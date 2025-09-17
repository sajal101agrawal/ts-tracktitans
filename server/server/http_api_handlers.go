package server

import (
    "encoding/json"
    "net/http"
    "strconv"
    "strings"
    "time"
    "github.com/ts2/ts2-sim-server/simulation"
)

// GET /api/analytics/kpis
func serveKPI(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet { http.Error(w, "Method not allowed", http.StatusMethodNotAllowed); return }
    rangeParam := r.URL.Query().Get("timeRange")
    var dur time.Duration
    switch rangeParam {
    case "1h": dur = time.Hour
    case "6h": dur = 6 * time.Hour
    case "1d": dur = 24 * time.Hour
    case "1w": dur = 7 * 24 * time.Hour
    case "1m": dur = 30 * 24 * time.Hour
    default: dur = 24 * time.Hour
    }
    agg, trend := aggregateKPIs(dur)
    resp := map[string]interface{}{
        "timeRange": rangeParam,
        "timestamp": time.Now().UTC().Format(time.RFC3339),
        "kpis": map[string]interface{}{
            "rtp": agg.punctuality,
            "punctuality": agg.punctuality,
            "averageDelay": agg.averageDelay,
            "p90Delay": agg.p90Delay,
            "throughput": agg.throughput,
            "utilization": agg.utilization,
            "acceptanceRate": agg.acceptanceRate,
            "openConflicts": agg.openConflicts,
            "mttrConflict": agg.mttrConflict,
            "headwayAdherence": agg.headwayAdherence,
            "headwayBreaches": agg.headwayBreaches,
            "efficiency": agg.efficiency,
            "performance": agg.performance,
        },
        "trends": map[string]interface{}{
            "rtp": map[string]interface{}{"change": trend.punctuality, "direction": trendDirection(trend.punctuality)},
            "averageDelay": map[string]interface{}{"change": trend.averageDelay, "direction": trendDirection(-trend.averageDelay)},
            "p90Delay": map[string]interface{}{"change": trend.p90Delay, "direction": trendDirection(-trend.p90Delay)},
            "throughput": map[string]interface{}{"change": trend.throughput, "direction": trendDirectionFloat(float64(trend.throughput))},
            "utilization": map[string]interface{}{"change": trend.utilization, "direction": trendDirection(trend.utilization)},
            "acceptanceRate": map[string]interface{}{"change": trend.acceptanceRate, "direction": trendDirection(trend.acceptanceRate)},
            "openConflicts": map[string]interface{}{"change": float64(trend.openConflicts), "direction": trendDirectionFloat(float64(-trend.openConflicts))},
            "headwayAdherence": map[string]interface{}{"change": trend.headwayAdherence, "direction": trendDirection(trend.headwayAdherence)},
        },
    }
    w.Header().Set("Content-Type", "application/json; charset=utf-8")
    _ = json.NewEncoder(w).Encode(resp)
}

func trendDirection(v float64) string { if v >= 0 { return "UP" }; return "DOWN" }
func trendDirectionFloat(v float64) string { if v >= 0 { return "UP" }; return "DOWN" }

// GET /api/analytics/historical
func serveKPIHistorical(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet { http.Error(w, "Method not allowed", http.StatusMethodNotAllowed); return }
    metric := r.URL.Query().Get("metric")
    period := r.URL.Query().Get("period")
    if period == "" { period = "hourly" }
    // naive: return last snapshots as series
    metrics.mu.RLock()
    snaps := append([]kpiSnapshot{}, metrics.snapshots...)
    metrics.mu.RUnlock()
    series := []map[string]interface{}{}
    for _, s := range snaps {
        v := 0.0
        switch metric {
        case "punctuality", "rtp": v = s.punctuality
        case "delay", "averageDelay": v = s.averageDelay
        case "p90", "p90Delay": v = s.p90Delay
        case "throughput": v = float64(s.throughput)
        case "utilization": v = s.utilization
        case "acceptanceRate": v = s.acceptanceRate
        case "openConflicts": v = float64(s.openConflicts)
        case "headwayAdherence": v = s.headwayAdherence
        case "headwayBreaches": v = float64(s.headwayBreaches)
        default: v = s.performance
        }
        series = append(series, map[string]interface{}{"t": s.ts.Format(time.RFC3339), "v": v})
    }
    resp := map[string]interface{}{"metric": metric, "period": period, "series": series}
    w.Header().Set("Content-Type", "application/json; charset=utf-8")
    _ = json.NewEncoder(w).Encode(resp)
}

// POST /api/simulation/whatif
func serveWhatIf(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost { http.Error(w, "Method not allowed", http.StatusMethodNotAllowed); return }
    var body map[string]interface{}
    if err := json.NewDecoder(r.Body).Decode(&body); err != nil { http.Error(w, "Bad request", http.StatusBadRequest); return }
    // Stub predictive model: use current metrics to produce adjusted values
    agg, _ := aggregateKPIs(24 * time.Hour)
    predictions := map[string]interface{}{
        "throughput": float64(agg.throughput) * 1.05,
        "averageDelay": agg.averageDelay * 1.1,
        "utilization": agg.utilization * 1.02,
        "bottlenecks": []string{"Junction_B"},
        "recommendations": []string{"Consider staggering train arrivals", "Monitor signal SIG_B1 timing"},
    }
    resp := map[string]interface{}{
        "scenarioId": "scenario_" + time.Now().UTC().Format("20060102150405"),
        "predictions": predictions,
        "confidence": 0.75,
    }
    w.Header().Set("Content-Type", "application/json; charset=utf-8")
    _ = json.NewEncoder(w).Encode(resp)
}

// GET /api/ai/hints
func serveAIHints(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet { http.Error(w, "Method not allowed", http.StatusMethodNotAllowed); return }
    // Ensure simulation is ready
    if sim == nil { http.Error(w, "Simulation not initialized", http.StatusServiceUnavailable); return }
    // Optional: force recompute
    if r.URL.Query().Get("recompute") == "1" { simulation.RecomputeSuggestions() }
    // If no snapshot yet, compute once
    if sim.Suggestions == nil { simulation.RecomputeSuggestions() }
    // Map suggestions snapshot to hints format
    type hint struct {
        ID        string                 `json:"id"`
        Type      string                 `json:"type"`
        Priority  string                 `json:"priority"`
        Message   string                 `json:"message"`
        Reasoning string                 `json:"reasoning"`
        Confidence int                   `json:"confidence"`
        SuggestedAction map[string]interface{} `json:"suggestedAction"`
    }
    hints := []hint{}
    if sim.Suggestions != nil {
        for _, s := range sim.Suggestions.Items {
            prio := "MEDIUM"
            if s.Score >= 15 { prio = "HIGH" } else if s.Score < 5 { prio = "LOW" }
            msg := s.Title
            sa := map[string]interface{}{}
            if len(s.Actions) > 0 { sa = map[string]interface{}{ "type": strings.ToUpper(s.Actions[0].Action), "object": s.Actions[0].Object, "params": s.Actions[0].Params } }
            hints = append(hints, hint{
                ID: s.ID, Type: "OPTIMIZATION", Priority: prio, Message: msg, Reasoning: s.Reason, Confidence: int(80 + s.Score) % 100, SuggestedAction: sa,
            })
        }
    }
    resp := map[string]interface{}{ "hints": hints, "nextUpdate": time.Now().UTC().Add(3*time.Minute).Format(time.RFC3339) }
    w.Header().Set("Content-Type", "application/json; charset=utf-8")
    _ = json.NewEncoder(w).Encode(resp)
}

// POST /api/ai/hints/{hintId}/respond
func serveAIHintRespond(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost { http.Error(w, "Method not allowed", http.StatusMethodNotAllowed); return }
    hid := strings.TrimPrefix(r.URL.Path, "/api/ai/hints/")
    var body struct{
        Response string `json:"response"`
        OverrideAction map[string]interface{} `json:"overrideAction"`
        UserID string `json:"userId"`
        DismissMinutes int `json:"dismissMinutes"`
    }
    if err := json.NewDecoder(r.Body).Decode(&body); err != nil { http.Error(w, "Bad request", http.StatusBadRequest); return }
    switch strings.ToUpper(body.Response) {
    case "ACCEPT":
        _ = simulation.AcceptSuggestion(hid)
        simulation.RecomputeSuggestions()
        metrics.mu.Lock(); metrics.accepted = append(metrics.accepted, time.Now().UTC()); metrics.mu.Unlock()
    case "DISMISS":
        if body.DismissMinutes <= 0 { body.DismissMinutes = 10 }
        _ = simulation.RejectSuggestion(hid, body.DismissMinutes)
        simulation.RecomputeSuggestions()
        metrics.mu.Lock(); metrics.ignored = append(metrics.ignored, time.Now().UTC()); metrics.mu.Unlock()
    case "OVERRIDE":
        metrics.mu.Lock(); metrics.overrides = append(metrics.overrides, time.Now().UTC()); metrics.mu.Unlock()
        // no-op for action by default
    }
    w.Header().Set("Content-Type", "application/json; charset=utf-8")
    _, _ = w.Write([]byte("{\"status\":\"OK\"}"))
}


// POST /api/simulation/restart
// Restarts the simulation back to its initial state loaded at process start.
// This reinitializes all data and time to the original snapshot.
func serveSimulationRestart(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost { http.Error(w, "Method not allowed", http.StatusMethodNotAllowed); return }
    if sim == nil { http.Error(w, "Simulation not initialized", http.StatusServiceUnavailable); return }
    if initialSimSnapshot == nil { http.Error(w, "Initial snapshot unavailable", http.StatusInternalServerError); return }

    // Pause current loop if running
    if sim.IsStarted() { sim.Pause() }

    // Rebuild a fresh Simulation from the initial snapshot
    var fresh simulation.Simulation
    if err := json.Unmarshal(initialSimSnapshot, &fresh); err != nil {
        http.Error(w, "Failed to rebuild simulation", http.StatusInternalServerError)
        return
    }
    // Initialize and swap
    if err := fresh.Initialize(); err != nil {
        http.Error(w, "Failed to initialize simulation", http.StatusInternalServerError)
        return
    }

    // Swap global pointer
    sim = &fresh

    // Rebind suggestion engine
    simulation.ResetSuggestionEngine(sim)
    if sim.Options.SuggestionsEnabled { simulation.RecomputeSuggestions() }

    // Optionally restart clock if client requests autoStart=1
    if r.URL.Query().Get("autoStart") == "1" {
        sim.Start()
    }

    w.Header().Set("Content-Type", "application/json; charset=utf-8")
    _, _ = w.Write([]byte("{\"status\":\"OK\"}"))
}


// GET /api/audit/logs?sinceId=123&limit=200
func serveAuditLogs(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet { http.Error(w, "Method not allowed", http.StatusMethodNotAllowed); return }
    q := r.URL.Query()
    sinceParam := q.Get("sinceId")
    limitParam := q.Get("limit")
    var sinceID int64
    var err error
    if sinceParam != "" { sinceID, err = strconv.ParseInt(sinceParam, 10, 64); if err != nil { http.Error(w, "Bad sinceId", http.StatusBadRequest); return } }
    limit := 200
    if limitParam != "" { if l, err2 := strconv.Atoi(limitParam); err2 == nil && l > 0 && l <= 1000 { limit = l } }
    logs := audits.getSince(sinceID, limit)
    w.Header().Set("Content-Type", "application/json; charset=utf-8")
    _ = json.NewEncoder(w).Encode(map[string]interface{}{"items": logs})
}

// GET /api/audit/stream (Server-Sent Events)
func serveAuditStream(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet { http.Error(w, "Method not allowed", http.StatusMethodNotAllowed); return }
    w.Header().Set("Content-Type", "text/event-stream")
    w.Header().Set("Cache-Control", "no-cache")
    w.Header().Set("Connection", "keep-alive")
    flusher, ok := w.(http.Flusher)
    if !ok { http.Error(w, "Streaming unsupported", http.StatusInternalServerError); return }
    ch := audits.subscribe()
    defer audits.unsubscribe(ch)
    // Send a comment to establish stream
    _, _ = w.Write([]byte(":ok\n\n"))
    flusher.Flush()
    // heartbeat ticker
    ticker := time.NewTicker(25 * time.Second)
    defer ticker.Stop()
    enc := json.NewEncoder(w)
    for {
        select {
        case e, ok := <-ch:
            if !ok { return }
            _, _ = w.Write([]byte("event: audit\n"))
            // write data: <json> followed by two newlines
            _, _ = w.Write([]byte("data: "))
            // We need to encode into a buffer-like; json.Encoder writes without newline so ok
            _ = enc.Encode(e)
            _, _ = w.Write([]byte("\n"))
            flusher.Flush()
        case <-r.Context().Done():
            return
        case <-ticker.C:
            _, _ = w.Write([]byte(":hb\n\n"))
            flusher.Flush()
        }
    }
}


