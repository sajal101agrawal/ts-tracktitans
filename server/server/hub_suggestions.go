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

package server

import (
    "encoding/json"
    "fmt"

    "github.com/ts2/ts2-sim-server/simulation"
)

type suggestionsObject struct{}

// dispatch processes requests on the suggestions object
func (s *suggestionsObject) dispatch(h *Hub, req Request, conn *connection) {
    ch := conn.pushChan
    switch req.Action {
    case "list":
        // Return current suggestions snapshot
        if sim.Suggestions == nil {
            // Force recompute if enabled
            simulation.RecomputeSuggestions()
        }
        data, err := json.Marshal(sim.Suggestions)
        if err != nil {
            ch <- NewErrorResponse(req.ID, fmt.Errorf("internal error: %s", err))
            return
        }
        ch <- NewResponse(req.ID, data)
    case "accept":
        var p struct{ ID string `json:"id"` }
        if err := json.Unmarshal(req.Params, &p); err != nil {
            ch <- NewErrorResponse(req.ID, fmt.Errorf("unparsable request: %s (%s)", err, req.Params))
            return
        }
        if err := simulation.AcceptSuggestion(p.ID); err != nil {
            ch <- NewErrorResponse(req.ID, err)
            return
        }
        // Recompute after applying
        simulation.RecomputeSuggestions()
        ch <- NewOkResponse(req.ID, "Suggestion accepted")
    case "reject":
        var p struct{
            ID string `json:"id"`
            Minutes int `json:"minutes"`
        }
        if err := json.Unmarshal(req.Params, &p); err != nil {
            ch <- NewErrorResponse(req.ID, fmt.Errorf("unparsable request: %s (%s)", err, req.Params))
            return
        }
        if err := simulation.RejectSuggestion(p.ID, p.Minutes); err != nil {
            ch <- NewErrorResponse(req.ID, err)
            return
        }
        ch <- NewOkResponse(req.ID, "Suggestion rejected")
    case "recompute":
        simulation.RecomputeSuggestions()
        ch <- NewOkResponse(req.ID, "Recomputed")
    default:
        ch <- NewErrorResponse(req.ID, fmt.Errorf("unknown action %s/%s", req.Object, req.Action))
        logger.Debug("Request for unknown action received", "submodule", "hub", "object", req.Object, "action", req.Action)
    }
}

var _ hubObject = new(suggestionsObject)

func init() {
    hub.objects["suggestions"] = new(suggestionsObject)
}


