// Copyright (C) 2008-2018 by Nicolas Piganeau and the TS2 TEAM
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

package server

import (
	"encoding/json"
	"fmt"
	
	"github.com/ts2/ts2-sim-server/simulation"
)

type simulationObject struct{}

// dispatch processes requests made on the Simulation object
func (s *simulationObject) dispatch(h *Hub, req Request, conn *connection) {
	ch := conn.pushChan
	logger.Debug("Request for simulation received", "submodule", "hub", "object", req.Object, "action", req.Action)
	switch req.Action {
	case "start":
		sim.Start()
		ch <- NewOkResponse(req.ID, "Simulation started successfully")
	case "pause":
		sim.Pause()
		ch <- NewOkResponse(req.ID, "Simulation paused successfully")
	case "restart":
		// Restart simulation to initial state (similar to HTTP API restart)
		if sim == nil {
			ch <- NewErrorResponse(req.ID, fmt.Errorf("simulation not initialized"))
			return
		}
		if initialSimSnapshot == nil {
			ch <- NewErrorResponse(req.ID, fmt.Errorf("initial snapshot unavailable"))
			return
		}
		
		// Pause current loop if running
		if sim.IsStarted() {
			sim.Pause()
		}
		
		// Rebuild a fresh Simulation from the initial snapshot
		var fresh simulation.Simulation
		if err := json.Unmarshal(initialSimSnapshot, &fresh); err != nil {
			ch <- NewErrorResponse(req.ID, fmt.Errorf("failed to rebuild simulation: %s", err))
			return
		}
		
		// Initialize and swap
		if err := fresh.Initialize(); err != nil {
			ch <- NewErrorResponse(req.ID, fmt.Errorf("failed to initialize simulation: %s", err))
			return
		}
		
		// Swap global pointer
		sim = &fresh
		
		// Rebind suggestion engine
		simulation.ResetSuggestionEngine(sim)
		if sim.Options.SuggestionsEnabled {
			simulation.RecomputeSuggestions()
		}
		
		// Check if auto-start is requested in params
		autoStart := false
		if req.Params != nil {
			var params map[string]interface{}
			if err := json.Unmarshal(req.Params, &params); err == nil {
				if value, exists := params["autoStart"]; exists {
					if boolVal, ok := value.(bool); ok {
						autoStart = boolVal
					} else if strVal, ok := value.(string); ok && strVal == "true" {
						autoStart = true
					}
				}
			}
		}
		
		// Optionally auto-start if requested
		if autoStart {
			sim.Start()
			ch <- NewOkResponse(req.ID, "Simulation restarted and started successfully")
		} else {
			ch <- NewOkResponse(req.ID, "Simulation restarted successfully")
		}
	case "isStarted":
		j, err := json.Marshal(sim.IsStarted())
		if err != nil {
			ch <- NewErrorResponse(req.ID, fmt.Errorf("internal error: %s", err))
			return
		}
		ch <- NewResponse(req.ID, RawJSON(j))
	case "dump":
		data, err := json.Marshal(sim)
		if err != nil {
			ch <- NewErrorResponse(req.ID, fmt.Errorf("internal error: %s", err))
			return
		}
		ch <- NewResponse(req.ID, data)
	default:
		ch <- NewErrorResponse(req.ID, fmt.Errorf("unknown action %s/%s", req.Object, req.Action))
		logger.Debug("Request for unknown action received", "submodule", "hub", "object", req.Object, "action", req.Action)
	}
}

var _ hubObject = new(simulationObject)

func init() {
	hub.objects["simulation"] = new(simulationObject)
}
