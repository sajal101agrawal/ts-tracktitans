package server

import (
    "encoding/json"
    "net/http"
    "strconv"
    "strings"
    "time"

    "github.com/ts2/ts2-sim-server/simulation"
)

func trainStatusToString(s simulation.TrainStatus) string {
    switch s {
    case simulation.Running:
        return "RUNNING"
    case simulation.Stopped:
        return "STOPPED"
    case simulation.Waiting:
        return "WAITING"
    case simulation.Out:
        return "OUT"
    case simulation.EndOfService:
        return "END_OF_SERVICE"
    case simulation.Inactive:
        fallthrough
    default:
        return "INACTIVE"
    }
}

func positionXY(p simulation.Position) (float64, float64) {
    ti := p.TrackItem()
    switch v := ti.(type) {
    case *simulation.LineItem:
        // Interpolate between origin and end according to PositionOnTI
        start := v.Origin()
        end := v.End()
        // PositionOnTI is measured from previous item towards the other end
        // If coming from previous ID equals line.PreviousTiID, we use origin->end; otherwise end->origin
        t := p.PositionOnTI / v.RealLength()
        if p.PreviousItemID != v.PreviousTiID {
            // reverse direction
            start, end = end, start
        }
        x := start.X + (end.X-start.X)*t
        y := start.Y + (end.Y-start.Y)*t
        return x, y
    default:
        o := ti.Origin()
        return o.X, o.Y
    }
}

// GET /api/trains/section/{sectionId}
func serveTrainsBySection(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }
    sectionID := strings.TrimPrefix(r.URL.Path, "/api/trains/section/")
    // Section is represented by Place or TrackItem grouping. We'll match by PlaceCode or TrackItem name prefix.
    type trainOut struct {
        ID          string                 `json:"id"`
        ServiceCode string                 `json:"serviceCode"`
        Status      string                 `json:"status"`
        Speed       float64                `json:"speed"`
        MaxSpeed    float64                `json:"maxSpeed"`
        Position    map[string]float64     `json:"position"`
        Route       []string               `json:"route"`
        Delay       int                    `json:"delay"`
        Specs       map[string]interface{} `json:"specs"`
    }
    resp := map[string]interface{}{
        "sectionId": sectionID,
        "currentTrains": []trainOut{},
        "incomingTrains": []trainOut{},
    }
    // Simplified: consider trains whose head TrackItem belongs to the Place or TrackItem name contains sectionId
    for _, t := range sim.Trains {
        if !t.IsActive() {
            continue
        }
        ti := t.TrainHead.TrackItem()
        inSection := false
        if ti.Place() != nil && (ti.Place().PlaceCode == sectionID || ti.Place().Name() == sectionID) {
            inSection = true
        }
        if !inSection && (strings.Contains(ti.Name(), sectionID) || ti.ID() == sectionID) {
            inSection = true
        }
        if !inSection {
            continue
        }
        line := t.Service()
        delayMin := 0
        if line != nil && t.NextPlaceIndex != simulation.NoMorePlace {
            sl := line.Lines[t.NextPlaceIndex]
            if !sl.ScheduledDepartureTime.IsZero() {
                d := sim.Options.CurrentTime.Sub(sl.ScheduledDepartureTime)
                if d > 0 { delayMin = int(d / (60 * 1000000000)) }
            }
        }
        routeNames := []string{}
        if line != nil {
            for _, sl := range line.Lines {
                if sl.Place() != nil {
                    routeNames = append(routeNames, sl.Place().Name())
                } else {
                    routeNames = append(routeNames, sl.PlaceCode)
                }
            }
        }
        x, y := positionXY(t.TrainHead)
        out := trainOut{
            ID:          t.ID(),
            ServiceCode: t.ServiceCode,
            Status:      trainStatusToString(t.Status),
            Speed:       t.Speed * 3.6, // km/h for FE
            MaxSpeed:    t.MaxSpeedForTrainTrackItems(),
            Position:    map[string]float64{"x": x, "y": y},
            Route:       routeNames,
            Delay:       delayMin,
            Specs:       map[string]interface{}{"type": t.TrainType().Description, "length": t.TrainType().Length},
        }
        resp["currentTrains"] = append(resp["currentTrains"].([]trainOut), out)
    }
    w.Header().Set("Content-Type", "application/json; charset=utf-8")
    _ = json.NewEncoder(w).Encode(resp)
}

// POST /api/trains/{trainId}/route
func serveTrainRouteCommand(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }
    parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/api/trains/"), "/")
    if len(parts) < 2 || parts[1] != "route" {
        http.NotFound(w, r)
        return
    }
    tid, _ := strconv.Atoi(parts[0])
    if tid < 0 || tid >= len(sim.Trains) {
        http.Error(w, "TRAIN_NOT_FOUND", http.StatusNotFound)
        return
    }
    var body struct {
        Action   string   `json:"action"`
        NewRoute []string `json:"newRoute"`
        Reason   string   `json:"reason"`
    }
    if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
        http.Error(w, "Bad request", http.StatusBadRequest)
        return
    }
    t := sim.Trains[tid]
    switch strings.ToUpper(body.Action) {
    case "ACCEPT":
        // no-op here; client should use WS to activate a specific route. Return OK.
    case "REROUTE":
        // Not supported in core model (no free pathfinding). Return 501.
        http.Error(w, "Not Implemented", http.StatusNotImplemented)
        return
    case "HALT":
        _ = t.ProceedWithCaution() // best-effort to limit to warning speed
    default:
        http.Error(w, "Unknown action", http.StatusBadRequest)
        return
    }
    w.Header().Set("Content-Type", "application/json; charset=utf-8")
    _, _ = w.Write([]byte("{\"status\":\"OK\"}"))
}

// GET /api/systems/signals
func serveSignals(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }
    type out struct {
        Signals []map[string]interface{} `json:"signals"`
    }
    resp := out{Signals: []map[string]interface{}{}}
    for id, ti := range sim.TrackItems {
        s, ok := ti.(*simulation.SignalItem)
        if !ok {
            continue
        }
        status := "RED"
        if s.ActiveAspect().MeansProceed() {
            status = "GREEN"
        } else {
            status = "RED"
        }
        resp.Signals = append(resp.Signals, map[string]interface{}{
            "id": id,
            "name": s.Name(),
            "position": map[string]float64{"x": s.Origin().X, "y": s.Origin().Y},
            "status": status,
            "type": s.SignalType().Name,
            "section": s.PlaceCode,
            "lastChanged": s.LastChangedRFC3339(),
            "malfunctionStatus": "OPERATIONAL",
        })
    }
    w.Header().Set("Content-Type", "application/json; charset=utf-8")
    _ = json.NewEncoder(w).Encode(resp)
}

// PUT /api/systems/signals/{signalId}/status
func serveSignalOverride(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPut {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }
    sid := strings.TrimPrefix(r.URL.Path, "/api/systems/signals/")
    sid = strings.TrimSuffix(sid, "/status")
    sraw, ok := sim.TrackItems[sid]
    if !ok {
        http.Error(w, "SIGNAL_NOT_FOUND", http.StatusNotFound)
        return
    }
    s, ok := sraw.(*simulation.SignalItem)
    if !ok {
        http.Error(w, "SIGNAL_NOT_FOUND", http.StatusNotFound)
        return
    }
    var body struct{ NewStatus string `json:"newStatus"`; Reason string `json:"reason"`; UserID string `json:"userId"` }
    if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
        http.Error(w, "Bad request", http.StatusBadRequest)
        return
    }
    // Map to an aspect name in library by color. Fallback to default.
    target := strings.ToUpper(body.NewStatus)
    var asp *simulation.SignalAspect
    switch target {
    case "GREEN":
        asp = sim.SignalLib.Aspects["GREEN"]
    case "YELLOW":
        asp = sim.SignalLib.Aspects["YELLOW"]
    case "RED":
        asp = sim.SignalLib.Aspects["RED"]
    default:
        asp = s.SignalType().GetAspect(s)
    }
    s.SetManualAspect(asp)
    w.Header().Set("Content-Type", "application/json; charset=utf-8")
    _, _ = w.Write([]byte("{\"status\":\"OK\"}"))
}

// GET /api/systems/overview
func serveSystemOverview(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }
    if sim == nil {
        http.Error(w, "Simulation not initialized", http.StatusServiceUnavailable)
        return
    }

    totalsByType := map[string]int{}
    segmentsTotal := 0
    segmentsOccupied := 0

    signals := []map[string]interface{}{}
    tracks := []map[string]interface{}{}

    for id, ti := range sim.TrackItems {
        ttype := string(ti.Type())
        totalsByType[ttype]++

        switch ti.Type() {
        case simulation.TypeLine, simulation.TypeInvisibleLink, simulation.TypeSignal, simulation.TypePoints:
            segmentsTotal++
            if ti.TrainPresent() { segmentsOccupied++ }
        }

        base := map[string]interface{}{
            "id": id,
            "type": ttype,
            "name": ti.Name(),
            "place": func() string { if ti.Place() != nil { return ti.Place().PlaceCode }; return "" }(),
            "trackCode": ti.TrackCode(),
            "origin": map[string]float64{"x": ti.Origin().X, "y": ti.Origin().Y},
            "end": map[string]float64{"x": ti.End().X, "y": ti.End().Y},
            "previous": func() string { if ti.PreviousItem() != nil { return ti.PreviousItem().ID() }; return "" }(),
            "next": func() string { if ti.NextItem() != nil { return ti.NextItem().ID() }; return "" }(),
            "conflictWith": func() string { if ti.ConflictItem() != nil { return ti.ConflictItem().ID() }; return "" }(),
            "occupied": ti.TrainPresent(),
            "activeRoute": func() string { if ti.ActiveRoute() != nil { return ti.ActiveRoute().ID() }; return "" }(),
        }

        switch v := ti.(type) {
        case *simulation.SignalItem:
            status := "RED"
            if v.ActiveAspect().MeansProceed() { status = "GREEN" }
            var parID, narID string
            if v.PreviousItem() != nil && v.PreviousItem().ActiveRoute() != nil {
                parID = v.PreviousItem().ActiveRoute().ID()
            }
            if v.NextItem() != nil && v.NextItem().ActiveRoute() != nil {
                narID = v.NextItem().ActiveRoute().ID()
            }
            signals = append(signals, map[string]interface{}{
                "id": id,
                "name": v.Name(),
                "position": map[string]float64{"x": v.Origin().X, "y": v.Origin().Y},
                "status": status,
                "activeAspect": v.ActiveAspect().Name,
                "type": v.SignalType().Name,
                "section": v.PlaceCode,
                "lastChanged": v.LastChangedRFC3339(),
                "activeRoute": base["activeRoute"],
                "previousActiveRoute": parID,
                "nextActiveRoute": narID,
            })
        case *simulation.PointsItem:
            pm := map[string]interface{}{}
            for k, val := range base { pm[k] = val }
            pm["reversed"] = v.Reversed()
            pm["reverseTiId"] = v.ReverseTiId
            pm["pairedTiId"] = v.PairedTiId
            pm["center"] = map[string]float64{"x": v.Center().X, "y": v.Center().Y}
            pm["reverse"] = map[string]float64{"x": v.Reverse().X, "y": v.Reverse().Y}
            tracks = append(tracks, pm)
        case *simulation.LineItem, *simulation.InvisibleLinkItem:
            tracks = append(tracks, base)
        default:
            // skip others from tracks list
        }
    }

    routes := []map[string]interface{}{}
    for id, r := range sim.Routes {
        state := r.State()
        stateStr := "DEACTIVATED"
        switch state {
        case simulation.Activated:
            stateStr = "ACTIVATED"
        case simulation.Persistent:
            stateStr = "PERSISTENT"
        case simulation.Destroying:
            stateStr = "DESTROYING"
        }
        routes = append(routes, map[string]interface{}{
            "id": id,
            "beginSignal": r.BeginSignalId,
            "endSignal": r.EndSignalId,
            "state": stateStr,
            "isActive": r.IsActive(),
        })
    }

    trains := []map[string]interface{}{}
    activeCount := 0
    for _, t := range sim.Trains {
        x, y := positionXY(t.TrainHead)
        isActive := t.IsActive()
        if isActive { activeCount++ }
        trains = append(trains, map[string]interface{}{
            "id": t.ID(),
            "serviceCode": t.ServiceCode,
            "status": trainStatusToString(t.Status),
            "active": isActive,
            "speedKmh": t.Speed * 3.6,
            "maxSpeed": t.MaxSpeedForTrainTrackItems(),
            "position": map[string]float64{"x": x, "y": y},
        })
    }

    util := 0.0
    if segmentsTotal > 0 {
        util = float64(segmentsOccupied) * 100.0 / float64(segmentsTotal)
    }

    resp := map[string]interface{}{
        "timestamp": time.Now().UTC().Format(time.RFC3339),
        "system": map[string]interface{}{
            "title": sim.Options.Title,
            "description": sim.Options.Description,
            "version": sim.Options.Version,
            "currentTime": sim.Options.CurrentTime.Time.Format("15:04:05"),
            "timeFactor": sim.Options.TimeFactor,
            "running": sim.IsStarted(),
        },
        "totals": map[string]interface{}{
            "trackItems": totalsByType,
            "routes": len(sim.Routes),
            "signals": len(signals),
            "points": totalsByType[string(simulation.TypePoints)],
            "trains": map[string]int{"total": len(sim.Trains), "active": activeCount},
        },
        "occupancy": map[string]interface{}{
            "segmentsTotal": segmentsTotal,
            "segmentsOccupied": segmentsOccupied,
            "utilization": util,
        },
        "signals": signals,
        "tracks": tracks,
        "routes": routes,
        "trains": trains,
    }

    w.Header().Set("Content-Type", "application/json; charset=utf-8")
    _ = json.NewEncoder(w).Encode(resp)
}

func installHTTPAPI() {
    http.HandleFunc("/api/trains/section/", serveTrainsBySection)
    http.HandleFunc("/api/trains/", serveTrainRouteCommand)
    http.HandleFunc("/api/systems/signals", serveSignals)
    http.HandleFunc("/api/systems/signals/", serveSignalOverride)
    http.HandleFunc("/api/systems/overview", serveSystemOverview)
    http.HandleFunc("/api/analytics/kpis", serveKPI)
    http.HandleFunc("/api/analytics/historical", serveKPIHistorical)
    http.HandleFunc("/api/simulation/whatif", serveWhatIf)
    http.HandleFunc("/api/simulation/restart", serveSimulationRestart)
    http.HandleFunc("/api/ai/hints", serveAIHints)
    http.HandleFunc("/api/ai/hints/", serveAIHintRespond)
    http.HandleFunc("/api/audit/logs", serveAuditLogs)
    http.HandleFunc("/api/audit/stream", serveAuditStream)
}


