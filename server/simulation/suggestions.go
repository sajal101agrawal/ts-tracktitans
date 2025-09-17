// Copyright (C) 2008-2019 by Nicolas Piganeau and the TS2 TEAM
// (See AUTHORS file)
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program; if not, write to the
// Free Software Foundation, Inc.,
// 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

package simulation

import (
    "encoding/json"
    "fmt"
    "math"
    "sort"
    "strings"
    "time"
)

var suggestionEngine *SuggestionEngine

// SuggestionKind defines the category of a suggestion
type SuggestionKind string

const (
    SuggestionRouteActivate          SuggestionKind = "ROUTE_ACTIVATE"
    SuggestionRouteDeactivate        SuggestionKind = "ROUTE_DEACTIVATE"
    SuggestionTrainProceedWithCaution SuggestionKind = "TRAIN_PROCEED_WITH_CAUTION"
    SuggestionTrainReverse           SuggestionKind = "TRAIN_REVERSE"
    SuggestionTrainSetService        SuggestionKind = "TRAIN_SET_SERVICE"
    SuggestionSignalOverride         SuggestionKind = "SIGNAL_OVERRIDE"
)

// SuggestionAction describes an actionable command the client may accept
// The action maps to existing server hub object/action pairs.
type SuggestionAction struct {
    Object string                 `json:"object"`
    Action string                 `json:"action"`
    Params map[string]interface{} `json:"params"`
}

// Suggestion expresses a recommended action with a score and explanation
type Suggestion struct {
    ID        string             `json:"id"`
    Kind      SuggestionKind     `json:"kind"`
    Title     string             `json:"title"`
    Reason    string             `json:"reason"`
    Score     float64            `json:"score"`
    Actions   []SuggestionAction `json:"actions"`
}

// Suggestions is a wrapper to serialize a set of suggestions
type Suggestions struct {
    Items       []Suggestion `json:"items"`
    GeneratedAt Time         `json:"generatedAt"`

    simulation *Simulation
}

// ID implements SimObject for event serialization
func (s Suggestions) ID() string {
    // No object-level identity, broadcast as generic update
    return ""
}

// SuggestionEngine computes and manages suggestions periodically
type SuggestionEngine struct {
    sim            *Simulation
    lastComputedAt Time
    rejectedUntil  map[string]Time // suggestionID -> do not show until time
}

// NewSuggestionEngine creates a suggestion engine
func NewSuggestionEngine(sim *Simulation) *SuggestionEngine {
    return &SuggestionEngine{
        sim:           sim,
        rejectedUntil: make(map[string]Time),
    }
}

// RejectUntil marks a suggestion as rejected until the given time
func (e *SuggestionEngine) RejectUntil(id string, until Time) {
    e.rejectedUntil[id] = until
}

// RecomputeIfDue recomputes suggestions if interval elapsed. Returns true if changed.
func (e *SuggestionEngine) RecomputeIfDue() bool {
    if !e.sim.Options.SuggestionsEnabled {
        return false
    }
    interval := e.sim.Options.SuggestionsIntervalMinutes
    if interval <= 0 {
        interval = 3
    }
    now := e.sim.Options.CurrentTime
    if !e.lastComputedAt.IsZero() && now.Sub(e.lastComputedAt) < time.Duration(interval)*time.Minute {
        return false
    }
    e.lastComputedAt = now
    s := e.computeSuggestions()
    // Filter rejected
    filtered := make([]Suggestion, 0, len(s.Items))
    for _, it := range s.Items {
        if until, ok := e.rejectedUntil[it.ID]; ok {
            if now.Before(until) {
                continue
            }
        }
        filtered = append(filtered, it)
    }
    s.Items = filtered
    e.sim.Suggestions = s
    e.sim.sendEvent(&Event{Name: SuggestionsUpdatedEvent, Object: *s})
    return true
}

// Recompute recomputes suggestions immediately and emits an update event
func (e *SuggestionEngine) Recompute() {
    s := e.computeSuggestions()
    s.simulation = e.sim
    // Apply rejection filter just like RecomputeIfDue so suppressed hints disappear immediately
    now := e.sim.Options.CurrentTime
    filtered := make([]Suggestion, 0, len(s.Items))
    for _, it := range s.Items {
        if until, ok := e.rejectedUntil[it.ID]; ok {
            if now.Before(until) {
                continue
            }
        }
        filtered = append(filtered, it)
    }
    s.Items = filtered
    e.sim.Suggestions = s
    e.lastComputedAt = e.sim.Options.CurrentTime
    e.sim.sendEvent(&Event{Name: SuggestionsUpdatedEvent, Object: *s})
}

func (e *SuggestionEngine) computeSuggestions() *Suggestions {
    var res Suggestions
    res.simulation = e.sim
    res.GeneratedAt = e.sim.Options.CurrentTime
    // Collect candidate suggestions
    candidates := make([]Suggestion, 0)

    // KPI-proxy: current utilization percentage of track
    util := e.currentUtilizationPercent()

    // 1) Departures ready at platforms: propose route activation
    for _, t := range e.sim.Trains {
        if !t.IsActive() {
            continue
        }
        if t.Status != Stopped {
            continue
        }
        thi := t.TrainHead.TrackItem()
        if thi.Place() == nil || t.Service() == nil || t.NextPlaceIndex == NoMorePlace {
            continue
        }
        line := t.Service().Lines[t.NextPlaceIndex]
        if line.ScheduledDepartureTime.IsZero() {
            continue
        }
        // Can depart if past scheduled time and has waited minimum stop time
        if e.sim.Options.CurrentTime.Sub(line.ScheduledDepartureTime) < 0 {
            continue
        }
        if t.StoppedTime < t.minStopTime {
            continue
        }
        // Find next signal and candidate routes
        nextSignal := t.findNextSignal()
        if nextSignal == nil {
            continue
        }
        // Scan only routes starting at the next signal
        for _, r := range e.sim.routesByBeginSignal[nextSignal.ID()] {
            // Check activable
            activable := true
            for _, rm := range routesManagers {
                if err := rm.CanActivate(r); err != nil {
                    activable = false
                    break
                }
            }
            if !activable {
                continue
            }
            // Quick occupancy check on route path ahead (skip the begin signal and current head item)
            blocked := false
            for i, pos := range r.Positions {
                if i == 0 {
                    continue
                }
                ti := pos.TrackItem()
                if ti.Equals(thi) {
                    // ignore current occupancy by this train
                    continue
                }
                if ti.TrainPresent() {
                    blocked = true
                    break
                }
            }
            if blocked {
                continue
            }
            // Predictive safety: avoid potential crossing collisions on conflict items
            if pred, _ := e.predictsCrossingConflictOnRoute(t, r); pred {
                continue
            }
            // Predictive safety: avoid potential head-on collisions along the candidate route
            if pred, _ := e.predictsHeadOnConflictOnRoute(t, r); pred {
                continue
            }
            // Enforce planned track code for current departure place
            if line.TrackCode != "" && line.PlaceCode != "" {
                if !e.routeRespectsTrackCodeWithinPlace(r, line.PlaceCode, line.TrackCode) {
                    continue
                }
            }
            // Score: base on delay minutes and track alignment bonus
            delayMin := float64(e.sim.Options.CurrentTime.Sub(line.ScheduledDepartureTime) / time.Minute)
            score := 10.0*delayMin + 1.0
            reason := fmt.Sprintf("Scheduled departure was %s, minimum stop satisfied. No conflicts detected.", line.ScheduledDepartureTime.Time.Format("15:04:05"))
            // Bonus if first segment matches planned track code
            if thi.TrackCode() == line.TrackCode {
                score += 2.0
            }
            // KPI-proxy bonus: if utilization is low, encourage departures (boost when util < 50%)
            if util < 50.0 {
                score += (50.0 - util) / 10.0
            }
            sID := fmt.Sprintf("%s:%s:%s", SuggestionRouteActivate, t.ID(), r.ID())
            title := fmt.Sprintf("Set route %s to depart train %s", r.ID(), t.ServiceCode)
            act := SuggestionAction{Object: "route", Action: "activate", Params: map[string]interface{}{"id": r.ID(), "persistent": false}}
            candidates = append(candidates, Suggestion{ID: sID, Kind: SuggestionRouteActivate, Title: title, Reason: reason, Score: score, Actions: []SuggestionAction{act}})
        }
    }

    // 1b) Predictive route activation: for approaching trains that will need routes soon
    for _, t := range e.sim.Trains {
        if !t.IsActive() || t.Status != Running {
            continue
        }
        // Find next signal ahead
        nextSignal := t.findNextSignal()
        if nextSignal == nil {
            continue
        }
        // Calculate distance and time to signal
        distanceToSignal := e.distanceToSignal(t, nextSignal)
        maxDist := e.sim.Options.SuggestPredictiveMaxDistanceM
        if maxDist <= 0 { maxDist = 1000.0 }
        if distanceToSignal > maxDist { // Only consider trains within threshold
            continue
        }
        timeToSignal := e.estimateTimeToReach(t, distanceToSignal)
        maxETA := e.sim.Options.SuggestPredictiveMaxETASeconds
        if maxETA <= 0 { maxETA = 60 }
        if timeToSignal > time.Duration(maxETA)*time.Second { // Only consider if arriving within threshold
            continue
        }
        // Check if signal is or will be red
        if nextSignal.ActiveAspect().MeansProceed() {
            continue
        }
        // Find suitable route from this signal
        for _, r := range e.sim.routesByBeginSignal[nextSignal.ID()] {
            // Check if route can be activated
            activable := true
            for _, rm := range routesManagers {
                if err := rm.CanActivate(r); err != nil {
                    activable = false
                    break
                }
            }
            if !activable {
                continue
            }
            // Check path is clear
            pathClear := true
            for i, pos := range r.Positions {
                if i == 0 {
                    continue
                }
                if pos.TrackItem().TrainPresent() {
                    pathClear = false
                    break
                }
            }
            if !pathClear {
                continue
            }
            // Predictive safety: avoid potential crossing collisions on conflict items
            if pred, _ := e.predictsCrossingConflictOnRoute(t, r); pred {
                continue
            }
            // Predictive safety: avoid potential head-on collisions along the candidate route
            if pred, _ := e.predictsHeadOnConflictOnRoute(t, r); pred {
                continue
            }
            // Enforce planned track code for the upcoming must-stop place if this route touches it
            if nsl := e.nextMustStopLine(t); nsl != nil && nsl.PlaceCode != "" && nsl.TrackCode != "" {
                if e.routeTouchesPlace(r, nsl.PlaceCode) && !e.routeRespectsTrackCodeWithinPlace(r, nsl.PlaceCode, nsl.TrackCode) {
                    continue
                }
            }
            // Generate predictive suggestion with high priority
            score := 15.0 + (60.0-timeToSignal.Seconds())/10.0 // Higher score for trains closer to signal
            reason := fmt.Sprintf("Train %s approaching signal %s in ~%.0fs. Proactive route setting prevents stop.", 
                t.ServiceCode, nextSignal.ID(), timeToSignal.Seconds())
            sID := fmt.Sprintf("%s:%s:%s:predictive", SuggestionRouteActivate, t.ID(), r.ID())
            title := fmt.Sprintf("Proactively set route %s for approaching train %s", r.ID(), t.ServiceCode)
            act := SuggestionAction{Object: "route", Action: "activate", Params: map[string]interface{}{"id": r.ID(), "persistent": false}}
            candidates = append(candidates, Suggestion{ID: sID, Kind: SuggestionRouteActivate, Title: title, Reason: reason, Score: score, Actions: []SuggestionAction{act}})
            break // Only suggest one route per approaching train
        }
    }

    // 2) Waiting at stop signal: propose Proceed With Caution if clear to next signal
    for _, t := range e.sim.Trains {
        if !t.IsActive() || t.Speed != 0 {
            continue
        }
        // Next signal ahead
        nsp := t.NextSignalPosition()
        if nsp.Equals(Position{}) {
            continue
        }
        sig := nsp.TrackItem().(*SignalItem)
        if sig.ActiveAspect().MeansProceed() {
            continue
        }
        // Check ahead up to that next signal for trains
        clear := true
        for pos := t.TrainHead; !pos.Equals(nsp); pos = pos.Next(DirectionCurrent) {
            if pos.TrackItem().Equals(t.TrainHead.TrackItem()) {
                continue
            }
            if pos.TrackItem().TrainPresent() {
                clear = false
                break
            }
        }
        if !clear {
            continue
        }
        // Predictive safety: avoid potential crossing collisions along path to the next signal
        if pred, _ := e.predictsCrossingConflictAlongPath(t, nsp); pred {
            continue
        }
        // Predictive safety: avoid potential head-on collisions along path to the next signal
        if pred, _ := e.predictsHeadOnConflictAlongPath(t, nsp); pred {
            continue
        }
        sID := fmt.Sprintf("%s:%s", SuggestionTrainProceedWithCaution, t.ID())
        title := fmt.Sprintf("Proceed with caution for train %s to next signal", t.ServiceCode)
        reason := fmt.Sprintf("Signal %s at STOP but block to next signal appears clear.", sig.ID())
        act := SuggestionAction{Object: "train", Action: "proceed", Params: map[string]interface{}{"id": mustAtoi(t.ID())}}
        // Higher score for late trains
        bonus := 0.0
        if t.Service() != nil && t.NextPlaceIndex != NoMorePlace {
            line := t.Service().Lines[t.NextPlaceIndex]
            if !line.ScheduledDepartureTime.IsZero() {
                delayMin := float64(e.sim.Options.CurrentTime.Sub(line.ScheduledDepartureTime) / time.Minute)
                if delayMin > 0 {
                    bonus = delayMin
                }
            }
        }
        score := 5.0 + bonus
        // KPI-proxy: if utilization is high, prefer actions that get trains moving cautiously
        if util > 60.0 {
            score += (util - 60.0) / 12.0
        }
        candidates = append(candidates, Suggestion{ID: sID, Kind: SuggestionTrainProceedWithCaution, Title: title, Reason: reason, Score: score, Actions: []SuggestionAction{act}})
    }

    // 3) Route deactivation (targeted): only propose deactivating persistent routes that currently block ready departures
    // Map of blocking routeID -> list of affected train IDs
    blockedBy := make(map[string][]string)
    // Build list of trains ready to depart (same preconditions as activation)
    readyTrains := make([]*Train, 0)
    for _, t := range e.sim.Trains {
        if !t.IsActive() || t.Status != Stopped || t.Service() == nil || t.NextPlaceIndex == NoMorePlace {
            continue
        }
        line := t.Service().Lines[t.NextPlaceIndex]
        if line.ScheduledDepartureTime.IsZero() {
            continue
        }
        if e.sim.Options.CurrentTime.Sub(line.ScheduledDepartureTime) < 0 {
            continue
        }
        if t.StoppedTime < t.minStopTime {
            continue
        }
        readyTrains = append(readyTrains, t)
    }
    // For each ready train, find a candidate route that is blocked by a persistent active route
    for _, t := range readyTrains {
        nextSignal := t.findNextSignal()
        if nextSignal == nil { continue }
        thi := t.TrainHead.TrackItem()
        for _, r := range e.sim.routesByBeginSignal[nextSignal.ID()] {
            // Skip if occupied along route path ahead (true occupancy, not interlocking)
            pathBlockedByTrain := false
            for i, pos := range r.Positions {
                if i == 0 { continue }
                ti := pos.TrackItem()
                if ti.Equals(thi) { continue }
                if ti.TrainPresent() { pathBlockedByTrain = true; break }
            }
            if pathBlockedByTrain { continue }
            // Ask route managers for activation and parse conflicting route if any
            var conflictID string
            for _, rm := range routesManagers {
                if err := rm.CanActivate(r); err != nil {
                    if cid := parseConflictingRouteID(err.Error()); cid != "" {
                        conflictID = cid
                        break
                    }
                }
            }
            if conflictID == "" { continue }
            // Check conflicting route is persistent and unused
            rp, ok := e.sim.Routes[conflictID]
            if !ok { continue }
            if rp.State() != Persistent { continue }
            if routeHasAnyTrain(rp) { continue }
            // Record
            blockedBy[rp.ID()] = append(blockedBy[rp.ID()], t.ID())
            // Only record one blocking route per train to avoid noise
            break
        }
    }
    // Rank blocking routes by number of affected trains (desc) and emit top-K suggestions
    type blockEntry struct { id string; count int }
    bes := make([]blockEntry, 0, len(blockedBy))
    for id, list := range blockedBy { bes = append(bes, blockEntry{id: id, count: len(list)}) }
    sort.Slice(bes, func(i, j int) bool { return bes[i].count > bes[j].count })
    maxSuggest := 5
    for i, be := range bes {
        if i >= maxSuggest { break }
        r := e.sim.Routes[be.id]
        score := 8.0 + 3.0*float64(be.count)
        if util > 50.0 { score += (util - 50.0) / 8.0 }
        title := fmt.Sprintf("Deactivate persistent route %s to unblock %d departure(s)", r.ID(), be.count)
        reason := fmt.Sprintf("Route blocks %d ready departure(s) via interlocking.", be.count)
        sID := fmt.Sprintf("%s:%s", SuggestionRouteDeactivate, r.ID())
        act := SuggestionAction{Object: "route", Action: "deactivate", Params: map[string]interface{}{"id": r.ID()}}
        candidates = append(candidates, Suggestion{ID: sID, Kind: SuggestionRouteDeactivate, Title: title, Reason: reason, Score: score, Actions: []SuggestionAction{act}})
    }

    // 4) Safe manual signal override (prefer caution) when beneficial
    for _, t := range e.sim.Trains {
        if !t.IsActive() || t.Speed != 0 {
            continue
        }
        // Next signal ahead
        nsp := t.NextSignalPosition()
        if nsp.Equals(Position{}) {
            continue
        }
        sig := nsp.TrackItem().(*SignalItem)
        if sig.ActiveAspect().MeansProceed() {
            continue
        }
        // Check ahead up to that next signal for trains
        clear := true
        for pos := t.TrainHead; !pos.Equals(nsp); pos = pos.Next(DirectionCurrent) {
            if pos.TrackItem().Equals(t.TrainHead.TrackItem()) {
                continue
            }
            if pos.TrackItem().TrainPresent() {
                clear = false
                break
            }
        }
        if !clear {
            continue
        }
        // Choose a conservative proceed aspect (prefer the lowest-speed proceed aspect)
        targetAspect := e.findProceedAspectPreferCaution(sig)
        if targetAspect == nil {
            continue
        }
        sID := fmt.Sprintf("%s:%s:%s", SuggestionSignalOverride, sig.ID(), targetAspect.Name)
        title := fmt.Sprintf("Set signal %s to %s to allow cautious depart of train %s", sig.ID(), targetAspect.Name, t.ServiceCode)
        reason := fmt.Sprintf("Block to next signal appears clear; temporary manual override to %s would expedite departure.", targetAspect.Name)
        // Provide HTTP-friendly action mapping for clients
        color := strings.ToUpper(targetAspect.Name)
        if strings.Contains(color, "CLEAR") { color = "GREEN" }
        if strings.Contains(color, "CAUTION") { color = "YELLOW" }
        act := SuggestionAction{Object: "signal", Action: "status", Params: map[string]interface{}{"id": sig.ID(), "newStatus": color}}
        // KPI-proxy: prefer overrides more when utilization is high
        score := 7.0
        if util > 60.0 {
            score += (util - 60.0) / 8.0
        }
        candidates = append(candidates, Suggestion{ID: sID, Kind: SuggestionSignalOverride, Title: title, Reason: reason, Score: score, Actions: []SuggestionAction{act}})
    }

    // Order by score desc and cap list
    sort.Slice(candidates, func(i, j int) bool { return candidates[i].Score > candidates[j].Score })
    maxItems := e.sim.Options.SuggestMaxItems
    if maxItems <= 0 { maxItems = 50 }
    if len(candidates) > maxItems {
        candidates = candidates[:maxItems]
    }
    res.Items = candidates
    return &res
}

// Helper to parse numeric train IDs (trains use string IDs of numeric index)
func mustAtoi(s string) int {
    var x int
    _, _ = fmt.Sscanf(s, "%d", &x)
    return x
}

// currentUtilizationPercent computes a proxy for network utilization as percentage of occupied key track items
func (e *SuggestionEngine) currentUtilizationPercent() float64 {
    occupied := 0
    total := 0
    for _, ti := range e.sim.TrackItems {
        switch ti.Type() {
        case TypeLine, TypeInvisibleLink, TypeSignal, TypePoints:
            total++
            if ti.TrainPresent() { occupied++ }
        }
    }
    if total == 0 { return 0 }
    return float64(occupied) * 100.0 / float64(total)
}

// findProceedAspectPreferCaution returns a proceed aspect for the given signal, preferring the lowest-speed proceed aspect.
func (e *SuggestionEngine) findProceedAspectPreferCaution(sig *SignalItem) *SignalAspect {
    var best *SignalAspect
    bestSpeed := math.MaxFloat64
    for _, st := range sig.SignalType().States {
        asp := st.Aspect
        if asp == nil { continue }
        if !asp.MeansProceed() { continue }
        speed := math.MaxFloat64
        if len(asp.Actions) > 0 {
            speed = asp.Actions[0].Speed
        }
        if speed < bestSpeed {
            best = asp
            bestSpeed = speed
        }
    }
    return best
}

// parseConflictingRouteID tries to extract a route ID from a StandardManager CanActivate error string
// expected format contains: "conflicting route <ID> is active"
func parseConflictingRouteID(msg string) string {
    // Very small helper; avoid regex for performance
    parts := strings.Split(msg, " ")
    for i := 0; i+2 < len(parts); i++ {
        if strings.EqualFold(parts[i], "conflicting") && strings.EqualFold(parts[i+1], "route") {
            return strings.Trim(parts[i+2], ": ")
        }
    }
    return ""
}

// routeHasAnyTrain returns true if any position along the route is currently occupied by a train
func routeHasAnyTrain(r *Route) bool {
    for _, pos := range r.Positions {
        if pos.TrackItem().TrainPresent() {
            return true
        }
    }
    return false
}

// distanceToSignal calculates the distance from train to a signal ahead
func (e *SuggestionEngine) distanceToSignal(t *Train, sig *SignalItem) float64 {
    distance := 0.0
    pos := t.TrainHead
    for !pos.IsOut() {
        if pos.TrackItem().Equals(sig) {
            return distance
        }
        // Add remaining distance on current item
        if pos.TrackItem().RealLength() > 0 {
            distance += pos.TrackItem().RealLength() - pos.PositionOnTI
        }
        pos = pos.Next(DirectionCurrent)
    }
    return math.MaxFloat64 // Signal not found ahead
}

// estimateTimeToReach estimates time for train to reach a distance at current speed
func (e *SuggestionEngine) estimateTimeToReach(t *Train, distance float64) time.Duration {
    if t.Speed <= 0 {
        return time.Hour // Stopped train
    }
    // Consider deceleration if approaching signal
    avgSpeed := t.Speed
    if t.ApplicableAction().Speed < t.Speed {
        // Train is braking, use average of current and target speed
        avgSpeed = (t.Speed + t.ApplicableAction().Speed) / 2
    }
    if avgSpeed <= 0 {
        avgSpeed = 0.5 // Minimum speed to avoid division by zero
    }
    seconds := distance / avgSpeed
    return time.Duration(seconds * float64(time.Second))
}

// distanceToTrackItemStart calculates the distance from train to the start of a given track item ahead.
// Returns +Inf if the item is not found ahead in the current direction.
func (e *SuggestionEngine) distanceToTrackItemStart(t *Train, ti TrackItem) float64 {
    distance := 0.0
    pos := t.TrainHead
    for !pos.IsOut() {
        if pos.TrackItem().Equals(ti) {
            return distance
        }
        if pos.TrackItem().RealLength() > 0 {
            distance += pos.TrackItem().RealLength() - pos.PositionOnTI
        }
        pos = pos.Next(DirectionCurrent)
    }
    return math.MaxFloat64
}

// predictsCrossingConflictOnRoute checks if activating the route for train t could lead to
// a collision at a crossing (conflict items) with another approaching train.
func (e *SuggestionEngine) predictsCrossingConflictOnRoute(t *Train, r *Route) (bool, string) {
    for i, pos := range r.Positions {
        if i == 0 {
            continue
        }
        if pred, reason := e.predictsCrossingConflictForItem(t, pos.TrackItem()); pred {
            return true, reason
        }
    }
    return false, ""
}

// predictsCrossingConflictAlongPath checks items between the train head and the provided position (exclusive)
// for predicted crossing collisions.
func (e *SuggestionEngine) predictsCrossingConflictAlongPath(t *Train, to Position) (bool, string) {
    for pos := t.TrainHead; !pos.Equals(to); pos = pos.Next(DirectionCurrent) {
        if pos.TrackItem().Equals(t.TrainHead.TrackItem()) {
            continue
        }
        if pred, reason := e.predictsCrossingConflictForItem(t, pos.TrackItem()); pred {
            return true, reason
        }
    }
    return false, ""
}

// predictsCrossingConflictForItem checks one track item for potential crossing collision with another train
// via its ConflictItem link. It considers current occupancy and a short lookahead using simple ETA/clearance timing.
func (e *SuggestionEngine) predictsCrossingConflictForItem(t *Train, ti TrackItem) (bool, string) {
    conflict := ti.ConflictItem()
    if conflict == nil {
        return false, ""
    }
    // Immediate occupancy on the conflict item blocks
    if conflict.TrainPresent() {
        return true, fmt.Sprintf("conflict item %s is occupied", conflict.ID())
    }
    // Predictive: find nearest approaching train to the conflict item
    var other *Train
    nearest := math.MaxFloat64
    for _, ot := range e.sim.Trains {
        if ot == nil || ot == t || !ot.IsActive() {
            continue
        }
        d := e.distanceToTrackItemStart(ot, conflict)
        if d < nearest {
            nearest = d
            other = ot
        }
    }
    if other == nil || nearest == math.MaxFloat64 {
        return false, ""
    }
    // Estimate arrival windows for both trains at the crossing
    myDist := e.distanceToTrackItemStart(t, ti)
    if myDist == math.MaxFloat64 {
        return false, ""
    }
    myETA := e.estimateTimeToReach(t, myDist)
    otherETA := e.estimateTimeToReach(other, nearest)

    // Clearance durations: time to fully clear the crossing area conservatively
    mySpeed := t.ApplicableAction().Speed
    if mySpeed <= 0 {
        mySpeed = 0.5
    }
    otherSpeed := other.ApplicableAction().Speed
    if otherSpeed <= 0 {
        otherSpeed = 0.5
    }
    myClear := time.Duration(((t.TrainType().Length + ti.RealLength()) / mySpeed) * float64(time.Second))
    otherClear := time.Duration(((other.TrainType().Length + conflict.RealLength()) / otherSpeed) * float64(time.Second))
    // Safety buffer between intervals
    bufSec := e.sim.Options.SuggestSafetyBufferSeconds
    if bufSec <= 0 { bufSec = 5 }
    buffer := time.Duration(bufSec) * time.Second
    if intervalsOverlap(myETA, myETA+myClear+buffer, otherETA, otherETA+otherClear+buffer) {
        return true, fmt.Sprintf("predicted crossing conflict at item %s with train %s", ti.ID(), other.ServiceCode)
    }
    return false, ""
}

func intervalsOverlap(aStart time.Duration, aEnd time.Duration, bStart time.Duration, bEnd time.Duration) bool {
    return aStart <= bEnd && bStart <= aEnd
}

// routeTouchesPlace returns true if any position in the route belongs to the given place
func (e *SuggestionEngine) routeTouchesPlace(r *Route, placeCode string) bool {
    for _, pos := range r.Positions {
        if pl := pos.TrackItem().Place(); pl != nil && pl.PlaceCode == placeCode {
            return true
        }
    }
    return false
}

// routeRespectsTrackCodeWithinPlace returns true if all items of the route that belong to placeCode either
// have empty track code or match the required trackCode. This enforces platform/track adherence inside the place.
func (e *SuggestionEngine) routeRespectsTrackCodeWithinPlace(r *Route, placeCode string, trackCode string) bool {
    for _, pos := range r.Positions {
        ti := pos.TrackItem()
        pl := ti.Place()
        if pl == nil || pl.PlaceCode != placeCode {
            continue
        }
        tc := ti.TrackCode()
        if tc != "" && tc != trackCode {
            return false
        }
    }
    return true
}

// nextMustStopLine finds the next service line with MustStop=true from the train's perspective.
func (e *SuggestionEngine) nextMustStopLine(t *Train) *ServiceLine {
    if t.Service() == nil || t.NextPlaceIndex == NoMorePlace {
        return nil
    }
    // If currently stopped at a stop place, look ahead from the next index
    start := t.NextPlaceIndex
    if t.Status == Stopped {
        start = t.NextPlaceIndex + 1
    }
    for i := start; i < len(t.Service().Lines); i++ {
        sl := t.Service().Lines[i]
        if sl.MustStop {
            return sl
        }
    }
    return nil
}

// predictsHeadOnConflictOnRoute checks if activating the route for train t could lead to
// a head-on collision with another train approaching any item on the route.
func (e *SuggestionEngine) predictsHeadOnConflictOnRoute(t *Train, r *Route) (bool, string) {
    for i, pos := range r.Positions {
        if i == 0 {
            continue
        }
        if pred, reason := e.predictsHeadOnConflictForItem(t, pos.TrackItem()); pred {
            return true, reason
        }
    }
    return false, ""
}

// predictsHeadOnConflictAlongPath checks items between the train head and the provided position (exclusive)
// for predicted head-on collisions on the same track items.
func (e *SuggestionEngine) predictsHeadOnConflictAlongPath(t *Train, to Position) (bool, string) {
    for pos := t.TrainHead; !pos.Equals(to); pos = pos.Next(DirectionCurrent) {
        if pos.TrackItem().Equals(t.TrainHead.TrackItem()) {
            continue
        }
        if pred, reason := e.predictsHeadOnConflictForItem(t, pos.TrackItem()); pred {
            return true, reason
        }
    }
    return false, ""
}

// predictsHeadOnConflictForItem checks for potential head-on collision on a single track item
// by comparing ETAs of the current train and any other approaching train to that item.
func (e *SuggestionEngine) predictsHeadOnConflictForItem(t *Train, ti TrackItem) (bool, string) {
    // Immediate occupancy already handled elsewhere, this is predictive only
    myDist := e.distanceToTrackItemStart(t, ti)
    if myDist == math.MaxFloat64 {
        return false, ""
    }
    myETA := e.estimateTimeToReach(t, myDist)
    // Clearance time to traverse the item conservatively
    mySpeed := t.ApplicableAction().Speed
    if mySpeed <= 0 {
        mySpeed = 0.5
    }
    myClear := time.Duration(((t.TrainType().Length + ti.RealLength()) / mySpeed) * float64(time.Second))

    var other *Train
    var otherETA time.Duration
    var otherClear time.Duration
    nearest := math.MaxFloat64
    for _, ot := range e.sim.Trains {
        if ot == nil || ot == t || !ot.IsActive() {
            continue
        }
        d := e.distanceToTrackItemStart(ot, ti)
        if d == math.MaxFloat64 {
            continue
        }
        if d < nearest {
            nearest = d
            other = ot
        }
    }
    if other == nil {
        return false, ""
    }
    otherETA = e.estimateTimeToReach(other, nearest)
    otherSpeed := other.ApplicableAction().Speed
    if otherSpeed <= 0 {
        otherSpeed = 0.5
    }
    otherClear = time.Duration(((other.TrainType().Length + ti.RealLength()) / otherSpeed) * float64(time.Second))
    bufSec := e.sim.Options.SuggestSafetyBufferSeconds
    if bufSec <= 0 { bufSec = 5 }
    buffer := time.Duration(bufSec) * time.Second
    if intervalsOverlap(myETA, myETA+myClear+buffer, otherETA, otherETA+otherClear+buffer) {
        return true, fmt.Sprintf("predicted head-on conflict on item %s with train %s", ti.ID(), other.ServiceCode)
    }
    return false, ""
}

// Accept executes the suggestion identified by id if still valid
func (e *SuggestionEngine) Accept(id string) error {
    parts := strings.Split(id, ":")
    if len(parts) == 0 {
        return fmt.Errorf("invalid suggestion id")
    }
    kind := parts[0]
    switch SuggestionKind(kind) {
    case SuggestionRouteActivate:
        if len(parts) < 3 {
            return fmt.Errorf("invalid route activation id")
        }
        // parts[1] trainId (unused), parts[2] routeId
        rte, ok := e.sim.Routes[parts[2]]
        if !ok {
            return fmt.Errorf("unknown route: %s", parts[2])
        }
        return rte.Activate(false)
    case SuggestionRouteDeactivate:
        if len(parts) < 2 {
            return fmt.Errorf("invalid route deactivation id")
        }
        rte, ok := e.sim.Routes[parts[1]]
        if !ok {
            return fmt.Errorf("unknown route: %s", parts[1])
        }
        return rte.Deactivate()
    case SuggestionTrainProceedWithCaution:
        if len(parts) < 2 {
            return fmt.Errorf("invalid proceed id")
        }
        tid := mustAtoi(parts[1])
        if tid < 0 || tid >= len(e.sim.Trains) {
            return fmt.Errorf("unknown train: %d", tid)
        }
        return e.sim.Trains[tid].ProceedWithCaution()
    case SuggestionSignalOverride:
        if len(parts) < 3 {
            return fmt.Errorf("invalid signal override id")
        }
        sigRaw, ok := e.sim.TrackItems[parts[1]]
        if !ok {
            return fmt.Errorf("unknown signal: %s", parts[1])
        }
        sig, ok := sigRaw.(*SignalItem)
        if !ok {
            return fmt.Errorf("not a signal: %s", parts[1])
        }
        aspectName := parts[2]
        var asp *SignalAspect
        if strings.EqualFold(aspectName, "DEFAULT") {
            asp = nil
        } else if a, ok := e.sim.SignalLib.Aspects[aspectName]; ok {
            asp = a
        } else {
            // Fallback to the conservative proceed aspect if requested aspect unknown
            asp = e.findProceedAspectPreferCaution(sig)
        }
        sig.SetManualAspect(asp)
        return nil
    default:
        return fmt.Errorf("unsupported suggestion kind: %s", kind)
    }
}

// Reject marks the suggestion as rejected for given minutes
func (e *SuggestionEngine) Reject(id string, minutes int) {
    if minutes <= 0 {
        minutes = 5
    }
    until := e.sim.Options.CurrentTime.Add(time.Duration(minutes) * time.Minute)
    e.RejectUntil(id, until)
}

// Exported helpers for server layer
func GetSuggestionEngine() *SuggestionEngine {
    return suggestionEngine
}

func AcceptSuggestion(id string) error {
    if suggestionEngine == nil {
        return fmt.Errorf("suggestion engine not initialized")
    }
    return suggestionEngine.Accept(id)
}

func RejectSuggestion(id string, minutes int) error {
    if suggestionEngine == nil {
        return fmt.Errorf("suggestion engine not initialized")
    }
    suggestionEngine.Reject(id, minutes)
    return nil
}

func RecomputeSuggestions() {
    if suggestionEngine == nil {
        return
    }
    suggestionEngine.Recompute()
}

// ResetSuggestionEngine rebinds the suggestions engine to the provided simulation.
// It discards previous engine state (including rejections) and starts fresh.
func ResetSuggestionEngine(sim *Simulation) {
    suggestionEngine = NewSuggestionEngine(sim)
}

// MarshalJSON for Suggestions so it serializes cleanly in events
func (s Suggestions) MarshalJSON() ([]byte, error) {
    type aux struct {
        Items       []Suggestion `json:"items"`
        GeneratedAt Time         `json:"generatedAt"`
    }
    a := aux{Items: s.Items, GeneratedAt: s.GeneratedAt}
    return json.Marshal(a)
}


