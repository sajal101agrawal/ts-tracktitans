## TS2 System Suggestions Algorithm

This document explains the purpose, inputs, decision logic, scoring, safety guarantees, and extensibility of the System Suggestions feature.

### Goals

- Provide AI-generated, human-in-the-loop recommendations that help maximize score and smooth operations.
- Recompute periodically and when triggered, push to UI, and allow operators to accept/override.
- Remain safe and consistent with interlocking, signaling, and existing TS2 logic.

### Overview and Lifecycle

- Controlled via `options` in the simulation file:
  - `suggestionsEnabled` (bool)
  - `suggestionsIntervalMinutes` (int, default 3)
- Engine instance: created in `Simulation.Initialize()`.
- Periodic recomputation: each simulation tick (500 ms) checks if last compute is older than `interval` and recomputes if due.
- On-demand recomputation: via WebSocket (`suggestions/recompute`) or HTTP (`GET /api/suggestions?recompute=1`).
- Delivery: emits `suggestionsUpdated` WebSocket notifications with a snapshot of suggestions.
- Actions: operator accepts/rejects via WebSocket RPC.

### Data Inputs

The engine reads the authoritative simulation state – it does not maintain its own copy:

- Trains: status (`Running|Stopped|Waiting|...`), positions (`TrainHead`/`TrainTail`), speeds, associated `Service`, `TrainType`.
- Services: schedule lines, planned train type, planned track code, post-actions.
- Routes: begin/end signals, directions, current state; route viability checked through registered `RoutesManager`s.
- Track Items: connectivity graph, `Place` associations, occupancy (`TrainPresent()`), per-item `maxSpeed` and `realLength`.
- Signals: next/previous signal lookup, active aspect and associated actions (`MeansProceed()`), visibility range.
- Options: minimum stop time generator, default speeds, penalties, `timeFactor`.

### Safety and Invariants

- Never bypasses interlocking: route activation is gated by all registered `RoutesManager.CanActivate()` vetoes.
- Avoids conflicts: performs conservative occupancy checks on candidate route path and blocks before next signal.
- Predictive crossing safety: suppresses suggestions likely to cause a collision at crossings (`ConflictItem()`), by checking conflict occupancy and a short ETA/clearance window using current speeds and train/item lengths plus a buffer.
- Track code adherence: route suggestions for departures must respect the scheduled track code within the current place; predictive route activation also respects the scheduled track code of the upcoming must‑stop place when the candidate route touches that place.
- Does not change simulation state unless the operator accepts a suggestion.
- Suggestions carry human-readable reasoning; they are not hard orders.

### Suggestion Model

```json
{
  "id": "<opaque-stable-id>",
  "kind": "ROUTE_ACTIVATE|ROUTE_DEACTIVATE|TRAIN_PROCEED_WITH_CAUTION|TRAIN_REVERSE|TRAIN_SET_SERVICE|SIGNAL_OVERRIDE",
  "title": "Human readable action",
  "reason": "Short rationale",
  "score": 0.0,
  "actions": [{"object":"route|train|signal", "action":"activate|deactivate|proceed|reverse|setService|status", "params": {}}]
}
```

- IDs are stable strings used for accept/reject. Current formats:
  - `ROUTE_ACTIVATE:<trainId>:<routeId>`
  - `TRAIN_PROCEED_WITH_CAUTION:<trainId>`

### Implemented Suggestion Types (v3)

#### 1) Route Activation to Depart a Train

Purpose: Depart trains that are ready to leave their current place when safe.

Preconditions (all must hold):
- Train `t` is `IsActive()` and `t.Status == Stopped`.
- `t.TrainHead` is at a `Place` that matches the current `Service` line (`t.Service().Lines[t.NextPlaceIndex]`).
- Scheduled departure is defined and `now >= scheduledDepartureTime`.
- `t.StoppedTime >= t.minStopTime` (respects minimum dwell).
- The next signal ahead exists (`t.findNextSignal()` returns non-nil).
- A route `r` exists with `r.BeginSignalId == nextSignal.ID()` and all `RoutesManager.CanActivate(r)` accept.
- Conservative occupancy: no `TrainPresent()` on items along `r.Positions` ahead (ignoring the head's current item for this train).

Scoring:
- `delayMinutes = floor((now - scheduledDepartureTime)/1m)`; minimum 0 used in formula if negative.
- Base score: `score = 1 + 10*delayMinutes`.
- Track alignment bonus: `+2` if `t.TrainHead.TrackItem().TrackCode() == planned TrackCode` of current service line.
- KPI-proxy bonus: if utilization is low (`util < 50%`), add `(50 - util)/10` to encourage departures.

Reasoning:
- Includes scheduled time, that minimum stop requirements are met, and that no conflicts were detected on the chosen path.

Action:
- `{object:"route", action:"activate", params:{"id": r.ID(), "persistent": false}}`.

#### 1b) Predictive Route Activation (NEW)

Purpose: Proactively set routes for approaching trains to prevent unnecessary stops at red signals.

Preconditions:
- Train `t` is `IsActive()` and `t.Status == Running`.
- Next signal ahead exists and is currently showing a stop aspect.
- Train is within 1km of the signal (configurable threshold).
- Estimated time to reach signal is less than 60 seconds.
- A suitable route from that signal exists and can be activated.
- The route path is clear of other trains.

Scoring:
- Base score: `15` (higher than reactive suggestions to prioritize prevention).
- Proximity bonus: `(60 - timeToSignal)/10` (higher score for trains closer to signal).
- This ensures predictive suggestions appear before reactive ones.

Reasoning:
- States the train ID, signal ID, and estimated time to arrival.
- Explains that proactive route setting prevents an unnecessary stop.

Action:
- `{object:"route", action:"activate", params:{"id": r.ID(), "persistent": false}}`.
- ID includes `:predictive` suffix to distinguish from reactive suggestions.

#### 2) Proceed With Caution at Stop Signal

Purpose: When a train is waiting at a stop aspect but the block up to the next signal is clear, propose a cautious proceed.

Preconditions:
- Train `t` is `IsActive()` and `t.Speed == 0`.
- Next signal ahead exists and `!nextSignal.ActiveAspect().MeansProceed()` (i.e., it demands stop/caution).
- Conservative block check: Between `t.TrainHead` and the next signal position, no `TrainPresent()` on any intervening `TrackItem` (ignoring the head's own item).

Scoring:
- Base score: `5`.
- Delay bonus (if applicable): `+delayMinutes` if current service line’s scheduled time has passed.
- KPI-proxy bonus: if utilization is high (`util > 60%`), add `(util - 60)/12` to prefer actions that get trains moving.

Reasoning:
- Names the stop signal ID and states that the block appears clear up to that signal.

Action:
- `{object:"train", action:"proceed", params:{"id": <trainIndex>}}` which maps to `Train.ProceedWithCaution()`.

#### 3) Route Deactivation to Release Capacity

Purpose: Release persistent routes that are currently unused and block other potential movements.

Preconditions:
- Route `r` is `Persistent` (set to remain after a train passes).
- None of the `r.Positions` are currently occupied (`TrainPresent()` is false for all).

Heuristic blockage estimate:
- Count routes `other` whose positions overlap an item that currently has `ActiveRoute == r` or whose conflict item (`ConflictItem()`) has `ActiveRoute == r`.

Scoring:
- Base score: `6`.
- Add `2 * blockedRoutesCount`.
- KPI-proxy bonus: if utilization is high (`util > 50%`), add `(util - 50)/10`.

Action:
- `{object:"route", action:"deactivate", params:{"id": r.ID()}}`.

Reasoning:
- Explains that the route is persistent, unoccupied, and appears to block `N` other routes.

#### 4) Manual Signal Override (Conservative Proceed)

Purpose: Where a train is stopped at a red but the block up to the next signal is clear, suggest a temporary manual proceed aspect (favoring caution) to expedite flow.

Preconditions:
- Train `t` is `IsActive()` and `t.Speed == 0`.
- Next signal `sig` exists and does not `MeansProceed()`.
- Block to the next signal is clear of trains (conservative scan as in PWC case).

Aspect selection:
- Choose the lowest-speed proceed aspect available for `sig` (prefers caution aspects over clear).

Scoring:
- Base score: `7`.
- KPI-proxy bonus: if utilization is high (`util > 60%`), add `(util - 60)/8`.

Action and ID:
- ID format: `SIGNAL_OVERRIDE:<signalId>:<aspectName>`.
- Action for HTTP-friendly clients: `{object:"signal", action:"status", params:{"id": <signalId>, "newStatus": "GREEN|YELLOW"}}` (color mapped from aspect name).

Accept semantics:
- On accept, the engine executes a manual override by calling `SignalItem.SetManualAspect(targetAspect)`.
- Overrides persist until reverted (e.g., by setting default/automatic). Future engine versions may propose a revert when appropriate.

Safety:
- Only proposed when the next block is clear. Uses the built-in signal aspects and never bypasses interlocking for routes.

### Ranking, KPI Integration, Capping, and Output

- KPI proxy used at compute time:
  - Utilization is computed as the percentage of occupied `Line|InvisibleLink|Signal|Points` items.
  - Low utilization boosts departures; high utilization boosts getting trains moving and releasing capacity.
- All candidates are scored and sorted by `score` descending, then capped to the top 50.
- A snapshot is emitted in `suggestionsUpdated` events and can be fetched via APIs.

### Reject/Accept Semantics

- Accept:
  - Mapped by ID to the underlying safe action:
    - Route activation: `Route.Activate(false)`
    - Proceed with caution: `Train.ProceedWithCaution()`
  - Triggers immediate recomputation to reflect the new state.

- Reject:
  - Suppresses the suggestion by ID for N minutes (default 5 if not provided).
  - Rejected suggestions are filtered out until the suppression timeout.

### Pseudocode

```text
every tick:
  if now - lastComputedAt >= interval:
    recompute()

recompute():
  candidates = []
  for train t in Trains:
    if depart_ready(t) and safe_route_exists(t):
      add candidate ROUTE_ACTIVATE with score = 1 + 10*delay + track_bonus

  for train t in Trains:
    if at_stop_signal(t) and block_clear_to_next_signal(t):
      add candidate TRAIN_PROCEED_WITH_CAUTION with score = 5 + delay_bonus

  for route r in Routes:
    if r.state == PERSISTENT and route_unoccupied(r):
      blocked = count_routes_blocked_by(r)
      add candidate ROUTE_DEACTIVATE with score = 6 + 2*blocked

  for train t in Trains:
    if stopped_at_red_with_clear_block(t):
      targetAspect = lowest_speed_proceed_aspect(nextSignal(t))
      if targetAspect:
        add candidate SIGNAL_OVERRIDE with base score 7

  sort by score desc
  cap to 50
  filter out ID suppressed until ‘untilTime’
  emit suggestionsUpdated with snapshot
```

### Performance Considerations

- Complexity is primarily `O(#trains * #routes)` due to scanning candidate routes starting at each train’s next signal.
- Occupancy checks scan linear positions along a route path or between two signals; routes are statically defined.
- Recompute throttled by `suggestionsIntervalMinutes` to avoid wasteful work.

### Limitations and Future Work

- Occupancy checks are conservative and do not perform full block section logic. Predictive checks currently focus on level crossing conflicts via `ConflictItem()`; they do not yet model full timetable headways or full-reservation platform logic beyond track-code adherence.
- No timetable optimization or look-ahead re-routing; suggestions only use pre-defined routes.
- Platform availability is inferred via current track code only; no platform reservation horizon.
- Extensions planned:
  - Dynamic routing alternatives based on conflicts and priorities.
  - Prioritization based on service priority classes, connections, and headways.
  - Section-wise speed profile inclusion in scoring for better throughput.
  - Automatic suggestion to revert manual signal overrides after use when safe.

### Real-World Suitability

- Interlocking respect: All route activations are validated by the simulation’s registered `RoutesManager`s.
- SPAD avoidance: Proceed-with-caution is only suggested if no train is present up to the next signal; it uses the built-in `Train.ProceedWithCaution()` behavior limiting speed.
- Human-in-the-loop: Operators remain in control; suggestions include rationale and can be declined.

### Extending the Engine

- Add a new `SuggestionKind` (e.g., `TRAIN_REVERSE`).
- Generate candidates with clear preconditions, safety checks, and a scoring model.
- Create an action mapping to an existing hub method (or add one).
- Include reasoning text explaining the preconditions and benefits.

### Related Code

- Engine and types: `simulation/suggestions.go`
- Event emission and loop integration: `simulation/simulation.go`
- Delivery (WebSocket/HTTP): `server/hub_suggestions.go`, `server/http.go`


