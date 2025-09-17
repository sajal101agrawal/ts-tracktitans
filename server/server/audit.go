package server

import (
	"encoding/json"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/ts2/ts2-sim-server/simulation"
)

// AuditEntry represents a single audit log item sent to FE
type AuditEntry struct {
	ID        string                 `json:"id"`
	Timestamp string                 `json:"timestamp"`
	Event     string                 `json:"event"`
	Category  string                 `json:"category"`
	Severity  string                 `json:"severity"`
	Object    map[string]interface{} `json:"object"`
	Details   map[string]interface{} `json:"details"`
}

type auditState struct {
	mu          sync.RWMutex
	entries     []AuditEntry
	capacity    int
	nextID      int64
	subscribers map[chan AuditEntry]bool
}

var audits = &auditState{}

func init() {
	// default capacity for audit ring buffer
	audits.capacity = 1000
	audits.entries = make([]AuditEntry, 0, audits.capacity)
	audits.subscribers = make(map[chan AuditEntry]bool)
}

func (a *auditState) append(entry AuditEntry) {
	a.mu.Lock()
	defer a.mu.Unlock()
	// assign ID and timestamp if missing
	a.nextID++
	entry.ID = strconv.FormatInt(a.nextID, 10)
	if entry.Timestamp == "" {
		entry.Timestamp = time.Now().UTC().Format(time.RFC3339)
	}
	if len(a.entries) == a.capacity {
		// drop the oldest (ring buffer behavior)
		copy(a.entries[0:], a.entries[1:])
		a.entries[len(a.entries)-1] = entry
	} else {
		a.entries = append(a.entries, entry)
	}
	// broadcast non-blocking to subscribers
	for ch := range a.subscribers {
		select {
		case ch <- entry:
		default:
			// drop if subscriber is slow
		}
	}
}

func (a *auditState) subscribe() chan AuditEntry {
	ch := make(chan AuditEntry, 256)
	a.mu.Lock()
	a.subscribers[ch] = true
	a.mu.Unlock()
	return ch
}

func (a *auditState) unsubscribe(ch chan AuditEntry) {
	a.mu.Lock()
	delete(a.subscribers, ch)
	a.mu.Unlock()
	close(ch)
}

// getSince returns up to limit entries with ID strictly greater than sinceID
func (a *auditState) getSince(sinceID int64, limit int) []AuditEntry {
	a.mu.RLock()
	defer a.mu.RUnlock()
	out := make([]AuditEntry, 0, limit)
	for i := 0; i < len(a.entries); i++ {
		id, _ := strconv.ParseInt(a.entries[i].ID, 10, 64)
		if id > sinceID {
			out = append(out, a.entries[i])
			if len(out) >= limit {
				break
			}
		}
	}
	return out
}

// recordAuditFromEvent converts a simulation event to an AuditEntry and appends it
func recordAuditFromEvent(e *simulation.Event) {
	if e == nil {
		return
	}
	entry := AuditEntry{
		Severity: "INFO",
		Object:   map[string]interface{}{},
		Details:  map[string]interface{}{},
	}
	switch e.Name {
	case simulation.RouteActivatedEvent:
		entry.Event = "ROUTE_ACTIVATED"
		entry.Category = "route"
		if r, ok := e.Object.(*simulation.Route); ok {
			entry.Object["id"] = r.ID()
			entry.Details["beginSignalId"] = r.BeginSignalId
			entry.Details["endSignalId"] = r.EndSignalId
			entry.Details["persistent"] = r.Persistent
		}
	case simulation.RouteDeactivatedEvent:
		entry.Event = "ROUTE_DEACTIVATED"
		entry.Category = "route"
		if r, ok := e.Object.(*simulation.Route); ok {
			entry.Object["id"] = r.ID()
			entry.Details["beginSignalId"] = r.BeginSignalId
			entry.Details["endSignalId"] = r.EndSignalId
		}
	case simulation.SignalaspectChangedEvent:
		entry.Event = "SIGNAL_ASPECT_CHANGED"
		entry.Category = "signal"
		if s, ok := e.Object.(*simulation.SignalItem); ok {
			entry.Object["id"] = s.ID()
			entry.Object["type"] = s.SignalTypeCode
			entry.Details["activeAspect"] = s.ActiveAspect().Name
			entry.Details["meansProceed"] = s.ActiveAspect().MeansProceed()
			entry.Details["lastChanged"] = s.LastChangedRFC3339()
		}
	case simulation.TrainStoppedAtStationEvent:
		entry.Event = "TRAIN_STOPPED_AT_STATION"
		entry.Category = "train"
		if t, ok := e.Object.(*simulation.Train); ok {
			entry.Object["id"] = t.ID()
			entry.Object["serviceCode"] = t.ServiceCode
			if ti := t.TrainHead.TrackItem(); ti != nil && ti.Place() != nil {
				entry.Details["place"] = map[string]interface{}{
					"code": ti.Place().PlaceCode,
					"name": ti.Place().Name(),
				}
			}
			// scheduled vs current time if available
			if line := t.Service(); line != nil && t.NextPlaceIndex < len(line.Lines) {
				sl := line.Lines[t.NextPlaceIndex]
				if !sl.ScheduledArrivalTime.IsZero() {
					entry.Details["scheduledArrival"] = sl.ScheduledArrivalTime.Format(time.RFC3339)
					entry.Details["actualTime"] = sim.Options.CurrentTime.Format(time.RFC3339)
					d := sim.Options.CurrentTime.Sub(sl.ScheduledArrivalTime)
					entry.Details["delayMinutes"] = int(d / time.Minute)
				}
			}
		}
	case simulation.TrainDepartedFromStationEvent:
		entry.Event = "TRAIN_DEPARTED_FROM_STATION"
		entry.Category = "train"
		if t, ok := e.Object.(*simulation.Train); ok {
			entry.Object["id"] = t.ID()
			entry.Object["serviceCode"] = t.ServiceCode
			if ti := t.TrainHead.TrackItem(); ti != nil && ti.Place() != nil {
				entry.Details["place"] = map[string]interface{}{
					"code": ti.Place().PlaceCode,
					"name": ti.Place().Name(),
				}
			}
			if line := t.Service(); line != nil && t.NextPlaceIndex <= len(line.Lines) {
				idx := t.NextPlaceIndex
				if idx > 0 { idx = idx - 1 }
				sl := line.Lines[idx]
				if !sl.ScheduledDepartureTime.IsZero() {
					entry.Details["scheduledDeparture"] = sl.ScheduledDepartureTime.Format(time.RFC3339)
					entry.Details["actualTime"] = sim.Options.CurrentTime.Format(time.RFC3339)
					d := sim.Options.CurrentTime.Sub(sl.ScheduledDepartureTime)
					entry.Details["delayMinutes"] = int(d / time.Minute)
				}
			}
		}
	case simulation.MessageReceivedEvent:
		entry.Event = "MESSAGE_RECEIVED"
		entry.Category = "system"
		// The message logger uses string messages; attempt to marshal object to JSON if possible
		b, _ := json.Marshal(e.Object)
		entry.Details["message"] = strings.TrimSpace(string(b))
	default:
		// ignore very chatty events like TrackItemChanged/TrainChanged by default
		if e.Name == simulation.TrackItemChangedEvent || e.Name == simulation.TrainChangedEvent || e.Name == simulation.ClockEvent {
			return
		}
		entry.Event = strings.ToUpper(string(e.Name))
		entry.Category = "system"
	}
	audits.append(entry)
}


