ts2 Sim Server
==============

[![GoDoc](https://godoc.org/github.com/ts2/ts2-sim-server?status.svg)](https://godoc.org/github.com/ts2/ts2-sim-server)
[![Join the chat at https://gitter.im/ts2/ts2-sim-server](https://badges.gitter.im/ts2/ts2-sim-server.svg)](https://gitter.im/ts2/ts2-sim-server?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Build Status](https://secure.travis-ci.org/ts2/ts2-sim-server.svg)](http://travis-ci.org/ts2/ts2-sim-server)
[![codecov](https://codecov.io/gh/ts2/ts2-sim-server/branch/master/graph/badge.svg)](https://codecov.io/gh/ts2/ts2-sim-server)

This is the home of the ts2 simulation server, the core of the ts2 simulator.

Unless you want to develop your own client and access the simulator through its API, 
you should go to https://github.com/ts2/ts2 to grab the all-in-one simulator which includes the simulation server.


Install
-------

### Binary

Download the binary for your platform from the [Release Page](https://github.com/ts2/ts2-sim-server/releases).
This is a single binary with no dependencies.

### Source
You need to install the Go distribution (https://golang.org/dl/) for your platform first.

Then use the go tool:

```bash
go get github.com/ts2/ts2-sim-server
```

Starting the server
-------------------
```bash
ts2-sim-server /path/to/simulation-file.json
```

The server is running and can be accessed at `ws://localhost:22222/ws`

> Note that the server only accepts JSON simulation files. 
> If you have a `.ts2` file, you must unzip it first, extract the `simulation.json` file inside and start the server on it.

Web UI
------
The server ships with a minimal Web UI to interact with the webservice.

Start the server and head to `http://localhost:22222`.


Suggestions API
---------------
The simulation can compute AI-generated operational suggestions every few minutes and push them to clients.

- Enable and configure in the simulation JSON `options`:

  - `suggestionsEnabled` (bool): turn suggestions on/off
  - `suggestionsIntervalMinutes` (int): recompute cadence in simulation minutes (default 3)

Delivery channels:

- WebSocket notifications: subscribe to `suggestionsUpdated` events to receive periodic snapshots:

  Request:

  ```json
  {"object":"server","action":"addListener","params":{"event":"suggestionsUpdated"}}
  ```

  Notification payload:

  ```json
  {
    "msgType": "notification",
    "data": {
      "name": "suggestionsUpdated",
      "object": {
        "items": [
          {
            "id": "ROUTE_ACTIVATE:3:11",
            "kind": "ROUTE_ACTIVATE",
            "title": "Set route 11 to depart train S001",
            "reason": "Scheduled departure was 06:05:00, minimum stop satisfied. No conflicts detected.",
            "score": 14.0,
            "actions": [{"object":"route","action":"activate","params":{"id":"11","persistent":false}}]
          }
        ],
        "generatedAt": "06:07:30"
      }
    }
  }
  ```

- WebSocket RPC:

  - List current suggestions
    ```json
    {"id":1, "object":"suggestions", "action":"list"}
    ```

  - Accept a suggestion (executes the embedded action)
    ```json
    {"id":2, "object":"suggestions", "action":"accept", "params": {"id": "ROUTE_ACTIVATE:3:11"}}
    ```

  - Reject a suggestion for N minutes (hides it temporarily)
    ```json
    {"id":3, "object":"suggestions", "action":"reject", "params": {"id": "ROUTE_ACTIVATE:3:11", "minutes": 10}}
    ```

  - Force recompute now
    ```json
    {"id":4, "object":"suggestions", "action":"recompute"}
    ```

- HTTP endpoint:

  - GET `/api/suggestions` returns the current snapshot.
  - GET `/api/suggestions?recompute=1` forces recompute then returns the snapshot.

Suggestion object schema:

```json
{
  "id": "<opaque-stable-id>",
  "kind": "ROUTE_ACTIVATE|ROUTE_DEACTIVATE|TRAIN_PROCEED_WITH_CAUTION|TRAIN_REVERSE|TRAIN_SET_SERVICE",
  "title": "Human readable action",
  "reason": "Short rationale",
  "score": 0.0,
  "actions": [{"object":"route|train", "action":"activate|deactivate|proceed|reverse|setService", "params": {}}]
}
```

See also: docs/system-suggestions.md for the detailed algorithm design.
