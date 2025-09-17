package server

import (
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/ts2/ts2-sim-server/simulation"
)

// Defaults/tuning for realtime KPIs
const (
	defaultOnTimeWindow    = 5 * time.Minute
	defaultDelayWindow     = 60 * time.Minute
	defaultThroughputWindow = 60 * time.Minute
	defaultMTTRWindow      = 60 * time.Minute
	defaultAcceptanceWindow = 120 * time.Minute
	defaultMinHeadway      = 120 * time.Second
)

type kpiSnapshot struct {
	ts                time.Time
	punctuality      float64
	averageDelay     float64
	p90Delay         float64
	throughput       int
	utilization      float64
	acceptanceRate   float64
	openConflicts    int
	mttrConflict     float64
	headwayAdherence float64
	headwayBreaches  int
	efficiency       float64
	performance      float64
}

type departureEvent struct{ ts time.Time; place string }
type delayPoint struct{ ts time.Time; minutes float64 }

type metricsState struct {
	mu sync.RWMutex

	// RTP counts across arrivals + departures (today/session so far)
	rtpOnTime int
	rtpTotal  int

	// Average delay (rolling), P90 window
	delays []delayPoint

	// throughput (rolling window of departures)
	departures []departureEvent

	// headway
	lastDepartureByPlace map[string]time.Time
	headwayBreaches      []time.Time

	// suggestions/conflicts
	openConflicts   int
	conflictFirstSeen map[string]time.Time // routeID -> first seen
	conflictsDetected []time.Time
	conflictsResolved []time.Time
	resolutionDurations []time.Duration

	// acceptance metrics
	accepted  []time.Time
	overrides []time.Time
	ignored   []time.Time

	// historical snapshots
	snapshots []kpiSnapshot
}

var metrics = &metricsState{ lastDepartureByPlace: make(map[string]time.Time), conflictFirstSeen: make(map[string]time.Time) }

func updateMetrics(e *simulation.Event) {
	metrics.mu.Lock()
	defer metrics.mu.Unlock()
	switch e.Name {
	case simulation.TrainStoppedAtStationEvent:
		// Arrival event, compute delay versus scheduled arrival
		t := e.Object.(*simulation.Train)
		line := t.Service()
		if line != nil && t.NextPlaceIndex < len(line.Lines) {
			sl := line.Lines[t.NextPlaceIndex]
			if !sl.ScheduledArrivalTime.IsZero() {
				delay := sim.Options.CurrentTime.Sub(sl.ScheduledArrivalTime)
				// RTP within ±5 min
				if delay < 0 {
					if -delay <= defaultOnTimeWindow { metrics.rtpOnTime++ }
				} else {
					if delay <= defaultOnTimeWindow { metrics.rtpOnTime++ }
				}
				metrics.rtpTotal++
				// Positive delay minutes only for Avg delay KPI
				if delay > 0 { metrics.delays = append(metrics.delays, delayPoint{ts: time.Now().UTC(), minutes: delay.Minutes()}) }
				trimDelaysLocked()
			}
		}
	case simulation.TrainDepartedFromStationEvent:
		// Departure event, compute delay versus scheduled departure at previous index
		t := e.Object.(*simulation.Train)
		line := t.Service()
		if line != nil {
			prevIdx := t.NextPlaceIndex - 1
			if prevIdx >= 0 && prevIdx < len(line.Lines) {
				sl := line.Lines[prevIdx]
				if !sl.ScheduledDepartureTime.IsZero() {
					delay := sim.Options.CurrentTime.Sub(sl.ScheduledDepartureTime)
					if delay < 0 {
						if -delay <= defaultOnTimeWindow { metrics.rtpOnTime++ }
					} else {
						if delay <= defaultOnTimeWindow { metrics.rtpOnTime++ }
					}
					metrics.rtpTotal++
					if delay > 0 { metrics.delays = append(metrics.delays, delayPoint{ts: time.Now().UTC(), minutes: delay.Minutes()}) }
					trimDelaysLocked()
				}
				// Throughput + headway by place
				place := sl.PlaceCode
				metrics.departures = append(metrics.departures, departureEvent{ts: time.Now().UTC(), place: place})
				trimDeparturesLocked()
				if last, ok := metrics.lastDepartureByPlace[place]; ok {
					gap := time.Since(last)
					if gap < defaultMinHeadway {
						metrics.headwayBreaches = append(metrics.headwayBreaches, time.Now().UTC())
						trimHeadwayBreachesLocked()
					}
				}
				metrics.lastDepartureByPlace[place] = time.Now().UTC()
			}
		}
	case simulation.SuggestionsUpdatedEvent:
		// Track open conflicts via route-deactivate suggestions and compute resolved/MTTR
		now := time.Now().UTC()
		// Suggestions object is sent by value
		sug := e.Object.(simulation.Suggestions)
		newSet := make(map[string]bool)
		for _, it := range sug.Items {
			if strings.HasPrefix(string(it.Kind), "ROUTE_DEACTIVATE") || strings.HasPrefix(it.ID, "ROUTE_DEACTIVATE:") {
				// Extract route id part if possible (format: ROUTE_DEACTIVATE:<routeId>)
				routeID := it.ID
				parts := strings.Split(it.ID, ":")
				if len(parts) >= 2 { routeID = parts[1] }
				newSet[routeID] = true
				if _, ok := metrics.conflictFirstSeen[routeID]; !ok {
					metrics.conflictFirstSeen[routeID] = now
					metrics.conflictsDetected = append(metrics.conflictsDetected, now)
				}
			}
		}
		// Detect cleared conflicts: present before, absent now
		for id, first := range metrics.conflictFirstSeen {
			if !newSet[id] {
				metrics.conflictsResolved = append(metrics.conflictsResolved, now)
				metrics.resolutionDurations = append(metrics.resolutionDurations, now.Sub(first))
				delete(metrics.conflictFirstSeen, id)
			}
		}
		metrics.openConflicts = len(newSet)
		trimConflictsLocked()
	}
}

func trimDeparturesLocked() {
	cutoff := time.Now().UTC().Add(-defaultThroughputWindow)
	i := 0
	for ; i < len(metrics.departures); i++ {
		if metrics.departures[i].ts.After(cutoff) { break }
	}
	if i > 0 && i < len(metrics.departures) {
		metrics.departures = append([]departureEvent{}, metrics.departures[i:]...)
	} else if i >= len(metrics.departures) {
		metrics.departures = nil
	}
}

func trimDelaysLocked() {
	cutoff := time.Now().UTC().Add(-defaultDelayWindow)
	i := 0
	for ; i < len(metrics.delays); i++ {
		if metrics.delays[i].ts.After(cutoff) { break }
	}
	if i > 0 && i < len(metrics.delays) {
		metrics.delays = append([]delayPoint{}, metrics.delays[i:]...)
	} else if i >= len(metrics.delays) {
		metrics.delays = nil
	}
}

func trimHeadwayBreachesLocked() {
	cutoff := time.Now().UTC().Add(-defaultThroughputWindow)
	i := 0
	for ; i < len(metrics.headwayBreaches); i++ {
		if metrics.headwayBreaches[i].After(cutoff) { break }
	}
	if i > 0 && i < len(metrics.headwayBreaches) {
		metrics.headwayBreaches = append([]time.Time{}, metrics.headwayBreaches[i:]...)
	} else if i >= len(metrics.headwayBreaches) {
		metrics.headwayBreaches = nil
	}
}

func trimConflictsLocked() {
	cutoffDet := time.Now().UTC().Add(-defaultThroughputWindow)
	cutoffRes := time.Now().UTC().Add(-defaultMTTRWindow)
	// detected
	i := 0
	for ; i < len(metrics.conflictsDetected); i++ { if metrics.conflictsDetected[i].After(cutoffDet) { break } }
	if i > 0 && i < len(metrics.conflictsDetected) { metrics.conflictsDetected = append([]time.Time{}, metrics.conflictsDetected[i:]...) } else if i >= len(metrics.conflictsDetected) { metrics.conflictsDetected = nil }
	// resolved
	j := 0
	for ; j < len(metrics.conflictsResolved); j++ { if metrics.conflictsResolved[j].After(cutoffRes) { break } }
	if j > 0 && j < len(metrics.conflictsResolved) { metrics.conflictsResolved = append([]time.Time{}, metrics.conflictsResolved[j:]...) } else if j >= len(metrics.conflictsResolved) { metrics.conflictsResolved = nil }
	// resolution durations: keep last N corresponding to window
	maxKeep := 500
	if len(metrics.resolutionDurations) > maxKeep { metrics.resolutionDurations = metrics.resolutionDurations[len(metrics.resolutionDurations)-maxKeep:] }
}

func takeSnapshot() {
	metrics.mu.Lock()
	defer metrics.mu.Unlock()
	// compute utilization instantaneously
	occupied := 0
	total := 0
	for _, ti := range sim.TrackItems {
		switch ti.Type() {
		case simulation.TypeLine, simulation.TypeInvisibleLink, simulation.TypeSignal, simulation.TypePoints:
			total++
			if ti.TrainPresent() { occupied++ }
		}
	}
	util := 0.0
	if total > 0 {
		util = float64(occupied) * 100.0 / float64(total)
	}
	// compute throughput in last hour
	cutoff := time.Now().UTC().Add(-defaultThroughputWindow)
	tp := 0
	for _, d := range metrics.departures {
		if d.ts.After(cutoff) { tp++ }
	}
	// RTP (session so far)
	punctuality := 0.0
	if metrics.rtpTotal > 0 {
		punctuality = float64(metrics.rtpOnTime) * 100.0 / float64(metrics.rtpTotal)
	}
	// Avg delay and P90 over last 60 minutes
	avgDelay := 0.0
	p90 := 0.0
	if len(metrics.delays) > 0 {
		sum := 0.0
		vals := make([]float64, 0, len(metrics.delays))
		for _, d := range metrics.delays { sum += d.minutes; vals = append(vals, d.minutes) }
		avgDelay = sum / float64(len(metrics.delays))
		sort.Float64s(vals)
		idx := int(0.9*float64(len(vals)-1) + 0.5)
		if idx < 0 { idx = 0 }
		if idx >= len(vals) { idx = len(vals)-1 }
		p90 = vals[idx]
	}
	// Acceptance rate (last 2 hours)
	acc, tot := countInWindow(metrics.accepted, defaultAcceptanceWindow), countInWindow(append(append([]time.Time{}, metrics.accepted...), append(append([]time.Time{}, metrics.overrides...), metrics.ignored...)...), defaultAcceptanceWindow)
	accRate := 0.0
	if tot > 0 { accRate = float64(acc) * 100.0 / float64(tot) }
	// Open conflicts and MTTR (avg of durations recorded in window)
	mttr := 0.0
	if len(metrics.resolutionDurations) > 0 {
		sum := 0.0
		cnt := 0
		for _, d := range metrics.resolutionDurations { sum += d.Minutes(); cnt++ }
		if cnt > 0 { mttr = sum / float64(cnt) }
	}
	// Headway adherence (no breaches)
	hwBreachesCount := countTimeInWindow(metrics.headwayBreaches, defaultThroughputWindow)
	depCount := 0
	for _, d := range metrics.departures { if d.ts.After(cutoff) { depCount++ } }
	headwayAdherence := 100.0
	if depCount > 0 { headwayAdherence = 100.0 * float64(depCount-hwBreachesCount) / float64(depCount) }
	// simple derived metrics
	efficiency := 100.0 - avgDelay
	if efficiency < 0 { efficiency = 0 }
	performance := (0.5*punctuality + 0.3*float64(tp) + 0.2*util) / 2.0
	snap := kpiSnapshot{
		ts:               time.Now().UTC(),
		punctuality:     punctuality,
		averageDelay:    avgDelay,
		p90Delay:        p90,
		throughput:      tp,
		utilization:     util,
		acceptanceRate:  accRate,
		openConflicts:   metrics.openConflicts,
		mttrConflict:    mttr,
		headwayAdherence: headwayAdherence,
		headwayBreaches: hwBreachesCount,
		efficiency:      efficiency,
		performance:     performance,
	}
	metrics.snapshots = append(metrics.snapshots, snap)
	if len(metrics.snapshots) > 1440 {
		metrics.snapshots = metrics.snapshots[len(metrics.snapshots)-1440:]
	}
}

func countInWindow(ts []time.Time, window time.Duration) int {
	cutoff := time.Now().UTC().Add(-window)
	c := 0
	for _, t := range ts {
		if t.After(cutoff) { c++ }
	}
	return c
}

func countTimeInWindow(ts []time.Time, window time.Duration) int { return countInWindow(ts, window) }

func startMetricsTicker() {
	go func() {
		ticker := time.NewTicker(60 * time.Second)
		for range ticker.C {
			takeSnapshot()
		}
	}()
}

func aggregateKPIs(rangeDur time.Duration) (kpiSnapshot, kpiSnapshot) {
	metrics.mu.RLock()
	defer metrics.mu.RUnlock()
	if len(metrics.snapshots) == 0 {
		return kpiSnapshot{ts: time.Now().UTC()}, kpiSnapshot{}
	}
	cutoff := time.Now().UTC().Add(-rangeDur)
	aggCount := 0
	var agg kpiSnapshot
	for _, s := range metrics.snapshots {
		if s.ts.Before(cutoff) { continue }
		agg.punctuality += s.punctuality
		agg.averageDelay += s.averageDelay
		agg.p90Delay += s.p90Delay
		agg.throughput += s.throughput
		agg.utilization += s.utilization
		agg.acceptanceRate += s.acceptanceRate
		agg.openConflicts += s.openConflicts
		agg.mttrConflict += s.mttrConflict
		agg.headwayAdherence += s.headwayAdherence
		agg.headwayBreaches += s.headwayBreaches
		agg.efficiency += s.efficiency
		agg.performance += s.performance
		aggCount++
	}
	if aggCount > 0 {
		agg.punctuality /= float64(aggCount)
		agg.averageDelay /= float64(aggCount)
		agg.p90Delay /= float64(aggCount)
		agg.utilization /= float64(aggCount)
		agg.acceptanceRate /= float64(aggCount)
		agg.mttrConflict /= float64(aggCount)
		agg.headwayAdherence /= float64(aggCount)
		agg.efficiency /= float64(aggCount)
		agg.performance /= float64(aggCount)
	}
	// trends: compare average of last 10% window vs previous 10%
	if len(metrics.snapshots) < 10 {
		return agg, kpiSnapshot{}
	}
	n := len(metrics.snapshots)
	w := n/10
	if w < 1 { w = 1 }
	cur := averageSlice(metrics.snapshots[n-w:])
	prev := averageSlice(metrics.snapshots[max(0,n-2*w):n-w])
	trend := kpiSnapshot{
		punctuality:  cur.punctuality - prev.punctuality,
		averageDelay: cur.averageDelay - prev.averageDelay,
		p90Delay:     cur.p90Delay - prev.p90Delay,
		throughput:   cur.throughput - prev.throughput,
		utilization:  cur.utilization - prev.utilization,
		acceptanceRate: cur.acceptanceRate - prev.acceptanceRate,
		openConflicts:  cur.openConflicts - prev.openConflicts,
		mttrConflict:   cur.mttrConflict - prev.mttrConflict,
		headwayAdherence: cur.headwayAdherence - prev.headwayAdherence,
		headwayBreaches:  cur.headwayBreaches - prev.headwayBreaches,
		efficiency:   cur.efficiency - prev.efficiency,
		performance:  cur.performance - prev.performance,
	}
	return agg, trend
}

func averageSlice(ss []kpiSnapshot) kpiSnapshot {
	var a kpiSnapshot
	if len(ss) == 0 { return a }
	for _, s := range ss {
		a.punctuality += s.punctuality
		a.averageDelay += s.averageDelay
		a.p90Delay += s.p90Delay
		a.throughput += s.throughput
		a.utilization += s.utilization
		a.acceptanceRate += s.acceptanceRate
		a.openConflicts += s.openConflicts
		a.mttrConflict += s.mttrConflict
		a.headwayAdherence += s.headwayAdherence
		a.headwayBreaches += s.headwayBreaches
		a.efficiency += s.efficiency
		a.performance += s.performance
	}
	a.punctuality /= float64(len(ss))
	a.averageDelay /= float64(len(ss))
	a.p90Delay /= float64(len(ss))
	a.utilization /= float64(len(ss))
	a.acceptanceRate /= float64(len(ss))
	a.mttrConflict /= float64(len(ss))
	a.headwayAdherence /= float64(len(ss))
	a.efficiency /= float64(len(ss))
	a.performance /= float64(len(ss))
	return a
}

func max(a, b int) int { if a>b {return a}; return b }

