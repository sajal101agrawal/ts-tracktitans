## TS2 TrackTitans - API Manual (Server)

### Auth headers (optional placeholders)
```
Authorization: Bearer <jwt_token>
X-API-Key: <api_key>
X-User-Role: <role>
```

### Base URL
- `http://<host>:22222`

---

### Suggestions
- GET `/api/suggestions` → current suggestions snapshot
- WS subscribe `server.addListener` to `suggestionsUpdated` for pushes
- WS RPC:
  - `{"object":"suggestions","action":"list"}`
  - `{"object":"suggestions","action":"accept","params":{"id":"..."}}`
  - `{"object":"suggestions","action":"reject","params":{"id":"...","minutes":10}}`

---

### Train Management

GET `/api/trains/section/{sectionId}`
- Returns trains whose head is within the section.
- Response fields: `currentTrains[].{id,serviceCode,status,speed,maxSpeed,position{x,y},route[],delay,specs{type,length}}`

POST `/api/trains/{trainId}/route`
- Body: `{ "action": "ACCEPT|REROUTE|HALT", "newRoute": [...], "reason": "..." }`
- Notes: `REROUTE` not implemented (core has pre-defined routes); `HALT` reduces speed using ProceedWithCaution.

---

### System Status

GET `/api/systems/signals`
- Returns signals with `{id,name,position{x,y},status(GREEN|RED),type,section,lastChanged,malfunctionStatus}`.

PUT `/api/systems/signals/{signalId}/status`
- Body: `{ "newStatus": "GREEN|YELLOW|RED", "reason": "...", "userId": "..." }`
- Sets manual override (mapped to library aspects). Use with caution.

### Simulation Control

#### HTTP REST API

POST `/api/simulation/restart?autoStart=0|1`
- Restarts the simulation to the initial state loaded at server startup.
- Query `autoStart=1` to automatically start the clock after restart (default `0` pauses).
- Response: `{ "status": "OK" }`

#### WebSocket API

All simulation control actions are also available via WebSocket for real-time applications:

**Start Simulation:**
```json
{"object":"simulation","action":"start"}
```
Response: `{"status":"OK","message":"Simulation started successfully"}`

**Pause Simulation:**
```json
{"object":"simulation","action":"pause"}
```  
Response: `{"status":"OK","message":"Simulation paused successfully"}`

**Restart Simulation:**
```json
{"object":"simulation","action":"restart","params":{"autoStart":false}}
```
Response: `{"status":"OK","message":"Simulation restarted successfully"}`

**Restart with Auto-Start:**
```json
{"object":"simulation","action":"restart","params":{"autoStart":true}}
```
Response: `{"status":"OK","message":"Simulation restarted and started successfully"}`

**Check Simulation State:**
```json
{"object":"simulation","action":"isStarted"}
```
Response: `true` or `false`

GET `/api/systems/overview`
- Consolidated snapshot for monitoring dashboards.
- Response shape:
```
{
  "timestamp": "2025-09-16T12:34:56Z",
  "system": {
    "title": "...",
    "description": "...",
    "version": "0.7",
    "currentTime": "15:04:05",
    "timeFactor": 1,
    "running": true
  },
  "totals": {
    "trackItems": { "LineItem": 123, "SignalItem": 45, "PointsItem": 12, ... },
    "routes": 87,
    "signals": 45,
    "points": 12,
    "trains": { "total": 20, "active": 15 }
  },
  "occupancy": { "segmentsTotal": 300, "segmentsOccupied": 42, "utilization": 14.0 },
  "signals": [
    { "id": "SIG_A1", "name": "...", "position": {"x":0,"y":0}, "status": "GREEN", "activeAspect": "GREEN", "type": "UK_BASIC", "section": "PL_A", "lastChanged": "...", "activeRoute": "R12", "previousActiveRoute": "R11", "nextActiveRoute": "R12" }
  ],
  "tracks": [
    { "id": "L123", "type": "LineItem", "name": "...", "place": "PL_A", "trackCode": "1", "origin": {"x":0,"y":0}, "end": {"x":10,"y":0}, "previous": "SIG_A1", "next": "SIG_A2", "conflictWith": "", "occupied": false, "activeRoute": "R12" },
    { "id": "P45", "type": "PointsItem", "name": "...", "reversed": false, "reverseTiId": "L999", "pairedTiId": "P46", "center": {"x":5,"y":5}, "reverse": {"x":10,"y":10}, ...}
  ],
  "routes": [ { "id": "R12", "beginSignal": "SIG_A1", "endSignal": "SIG_A2", "state": "ACTIVATED", "isActive": true } ],
  "trains": [ { "id": "3", "serviceCode": "S123", "status": "RUNNING", "active": true, "speedKmh": 45.0, "maxSpeed": 80.0, "position": {"x":100,"y":200} } ]
}
```

FE Guide (overview):
```javascript
// Poll every 2-5s (or via WS in future if needed)
async function fetchOverview() {
  const res = await fetch('/api/systems/overview');
  if (!res.ok) throw new Error('Overview fetch failed');
  return res.json();
}

function drawDashboard(o) {
  // KPIs
  updateGauge('util', o.occupancy.utilization);
  setText('#activeTrains', o.totals.trains.active + ' / ' + o.totals.trains.total);
  // Map
  for (const t of o.tracks) drawTrack(t);
  for (const s of o.signals) drawSignal(s);
  for (const tr of o.trains) drawTrain(tr);
}

// Example polling loop
setInterval(async () => {
  try { drawDashboard(await fetchOverview()); } catch (e) { /* noop */ }
}, 3000);
```

---

### KPI Analytics

GET `/api/analytics/kpis?timeRange=1h|6h|1d|1w|1m`
- Returns an aggregated snapshot over `timeRange` with top-strip KPIs ready for FE.
- Response shape:
```json
{
  "timeRange": "1h",
  "timestamp": "2025-09-16T12:00:00Z",
  "kpis": {
    "rtp": 87.3,                  // Right-Time Performance (±5 min) %
    "punctuality": 87.3,          // alias of rtp
    "averageDelay": 5.4,          // minutes, last 60 min window
    "p90Delay": 12.0,             // minutes, last 60 min window
    "throughput": 22,             // trains departed in last 60 min
    "utilization": 48.1,          // % occupied key track items now
    "acceptanceRate": 72.0,       // % of hints accepted over last 120 min
    "openConflicts": 1,           // count from suggestion engine (route conflicts)
    "mttrConflict": 4.3,          // minutes, mean resolution time (rolling)
    "headwayAdherence": 96.0,     // % departures without headway breach (last 60 min)
    "headwayBreaches": 1,         // count in last 60 min
    "efficiency": 94.6,           // derived = 100 - averageDelay (naive)
    "performance": 58.2           // blended score for prototype
  },
  "trends": {
    "rtp": { "change": 1.2, "direction": "UP" },
    "averageDelay": { "change": -0.3, "direction": "UP" },
    "p90Delay": { "change": -1.0, "direction": "UP" },
    "throughput": { "change": 3, "direction": "UP" },
    "utilization": { "change": 2.1, "direction": "UP" },
    "acceptanceRate": { "change": 5.0, "direction": "UP" },
    "openConflicts": { "change": -1, "direction": "UP" },
    "headwayAdherence": { "change": 1.0, "direction": "UP" }
  }
}
```

GET `/api/analytics/historical?metric=punctuality|rtp|averageDelay|p90Delay|throughput|utilization|acceptanceRate|openConflicts|headwayAdherence|headwayBreaches&period=hourly|daily|weekly`
- Returns `{ metric, period, series:[{t,rfc3339,v:number}] }` using the server’s periodic snapshots.

Notes:
- RTP counts both arrivals and departures within ±5 minutes versus schedule.
- Average and P90 delay are computed over a rolling 60-minute window of positive delays.
- Throughput and headway adherence look at the last 60 minutes.
- Acceptance rate uses the last 120 minutes of hint responses.

---

### What-If (stub)

POST `/api/simulation/whatif`
- Body: see FE spec; server returns a scenarioId and heuristic predictions.
- Intended for prototyping; a full simulator fork would be needed for production-grade what-if.

---

### AI Hints

GET `/api/ai/hints`
- Maps the suggestions engine snapshot into `hints` with `priority`, `confidence`, and `suggestedAction`.

POST `/api/ai/hints/{hintId}/respond`
- Body: `{ "response": "ACCEPT|DISMISS|OVERRIDE", "overrideAction": {...}, "userId": "...", "dismissMinutes": 10 }`
- Semantics:
  - `ACCEPT`: executes the underlying action (e.g., route activation), then recomputes hints immediately so it disappears from the next poll.
  - `DISMISS`: hides the hint ID for `dismissMinutes` (default 10) and recomputes immediately.
  - `OVERRIDE`: reserved for FE-ack only (no-op server-side by default).

---

### Frontend Integration Guide

#### WebSocket Simulation Control (Recommended)

For interactive applications, use WebSocket simulation control for real-time responsiveness:

```javascript
// Initialize WebSocket connection
const ws = new WebSocket('ws://localhost:22222/ws');
let requestId = 1;

// Helper function to send WebSocket requests
function sendRequest(object, action, params = {}) {
  return new Promise((resolve, reject) => {
    const id = requestId++;
    const request = { id, object, action, params };
    
    // Set up response handler
    const timeout = setTimeout(() => {
      reject(new Error('Request timeout'));
    }, 5000);
    
    const handleMessage = (event) => {
      const response = JSON.parse(event.data);
      if (response.id === id) {
        clearTimeout(timeout);
        ws.removeEventListener('message', handleMessage);
        
        if (response.status === 'OK') {
          resolve(response);
        } else {
          reject(new Error(response.message || 'Request failed'));
        }
      }
    };
    
    ws.addEventListener('message', handleMessage);
    ws.send(JSON.stringify(request));
  });
}

// Simulation control functions
async function startSimulation() {
  try {
    const response = await sendRequest('simulation', 'start');
    console.log('✅ Simulation started:', response.message);
  } catch (error) {
    console.error('❌ Failed to start simulation:', error.message);
  }
}

async function pauseSimulation() {
  try {
    const response = await sendRequest('simulation', 'pause');
    console.log('⏸️ Simulation paused:', response.message);
  } catch (error) {
    console.error('❌ Failed to pause simulation:', error.message);
  }
}

async function restartSimulation(autoStart = false) {
  try {
    const response = await sendRequest('simulation', 'restart', { autoStart });
    console.log('🔄 Simulation restarted:', response.message);
    return response;
  } catch (error) {
    console.error('❌ Failed to restart simulation:', error.message);
    throw error;
  }
}

async function checkSimulationState() {
  try {
    const response = await sendRequest('simulation', 'isStarted');
    const isRunning = JSON.parse(response.data);
    console.log('🔍 Simulation running:', isRunning);
    return isRunning;
  } catch (error) {
    console.error('❌ Failed to check simulation state:', error.message);
    throw error;
  }
}

// Example: Complete restart workflow
async function performCompleteRestart() {
  try {
    // Check current state
    const wasRunning = await checkSimulationState();
    console.log(`Current state: ${wasRunning ? 'RUNNING' : 'PAUSED'}`);
    
    // Restart with auto-start based on previous state
    await restartSimulation(wasRunning);
    
    // Verify new state
    const newState = await checkSimulationState();
    console.log(`New state: ${newState ? 'RUNNING' : 'PAUSED'}`);
    
    return newState;
  } catch (error) {
    console.error('Complete restart failed:', error);
    throw error;
  }
}

// UI Integration Example
class SimulationController {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.requestId = 1;
    this.isConnected = false;
    
    this.ws.onopen = () => {
      console.log('🔗 WebSocket connected');
      this.isConnected = true;
      this.updateUI();
    };
    
    this.ws.onclose = () => {
      console.log('🔌 WebSocket disconnected');
      this.isConnected = false;
      this.updateUI();
    };
  }
  
  async updateUI() {
    const startBtn = document.getElementById('start-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const restartBtn = document.getElementById('restart-btn');
    const statusEl = document.getElementById('sim-status');
    
    if (!this.isConnected) {
      startBtn.disabled = pauseBtn.disabled = restartBtn.disabled = true;
      statusEl.textContent = 'Disconnected';
      statusEl.className = 'status-error';
      return;
    }
    
    try {
      const isRunning = await this.checkState();
      statusEl.textContent = isRunning ? 'Running' : 'Paused';
      statusEl.className = isRunning ? 'status-running' : 'status-paused';
      
      startBtn.disabled = isRunning;
      pauseBtn.disabled = !isRunning;
      restartBtn.disabled = false;
    } catch (error) {
      console.error('Failed to update UI:', error);
      statusEl.textContent = 'Error';
      statusEl.className = 'status-error';
    }
  }
  
  async checkState() {
    const response = await this.sendRequest('simulation', 'isStarted');
    return JSON.parse(response.data);
  }
  
  async start() {
    await this.sendRequest('simulation', 'start');
    await this.updateUI();
  }
  
  async pause() {
    await this.sendRequest('simulation', 'pause');
    await this.updateUI();
  }
  
  async restart(autoStart = false) {
    await this.sendRequest('simulation', 'restart', { autoStart });
    await this.updateUI();
  }
  
  sendRequest(object, action, params = {}) {
    return sendRequest.call(this, object, action, params);
  }
}

// Initialize controller
const simController = new SimulationController('ws://localhost:22222/ws');

// Bind to UI buttons
document.getElementById('start-btn').onclick = () => simController.start();
document.getElementById('pause-btn').onclick = () => simController.pause();
document.getElementById('restart-btn').onclick = () => simController.restart();
document.getElementById('restart-start-btn').onclick = () => simController.restart(true);
```

#### HTML Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>TS2 Simulation Control</title>
    <style>
        .control-panel { padding: 20px; }
        .status-running { color: green; font-weight: bold; }
        .status-paused { color: orange; font-weight: bold; }
        .status-error { color: red; font-weight: bold; }
        button { margin: 5px; padding: 10px; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
    </style>
</head>
<body>
    <div class="control-panel">
        <h3>Simulation Control Panel</h3>
        <div>Status: <span id="sim-status">Connecting...</span></div>
        <div>
            <button id="start-btn">▶️ Start</button>
            <button id="pause-btn">⏸️ Pause</button>
            <button id="restart-btn">🔄 Restart</button>
            <button id="restart-start-btn">🔄▶️ Restart & Start</button>
        </div>
    </div>
    <script>/* Include the JavaScript code above */</script>
</body>
</html>
```

#### Best Practices

1. **Error Handling**: Always wrap WebSocket simulation commands in try-catch blocks
2. **State Synchronization**: Check simulation state after control actions to update UI
3. **Connection Management**: Handle WebSocket disconnections gracefully
4. **User Feedback**: Provide clear visual feedback during operations
5. **Timeouts**: Set reasonable timeouts for WebSocket requests (5-10 seconds)

---

### WebSocket Events

Use `/ws` and the bundled UI patterns as reference. Relevant events:
- `signalAspectChanged`, `trainChanged`, `trainStoppedAtStation`, `trainDepartedFromStation`, `optionsChanged`, `suggestionsUpdated`.

To subscribe:
```json
{"object":"server","action":"addListener","params":{"event":"suggestionsUpdated"}}
```

---

### Error Model
```
{
  "error": {"code": "...", "message": "...", "timestamp": "...", "requestId": "..."}
}
```

---

### Integration Tips
- Train IDs in HTTP are numeric index strings (from demo data). Use `/api/systems/signals` to discover signal IDs for overrides.
- Positions are scenery coordinates; scale/transform as needed by FE.
- Suggestions refresh every `options.suggestionsIntervalMinutes`; FE can also call `/api/suggestions?recompute=1` to force a refresh.

---

### Audit Logs

GET `/api/audit/logs?sinceId={lastId}&limit={n}`
- Returns recent audit items after `sinceId` (strictly greater), up to `limit` (default 200, max 1000).
- Response:
```
{
  "items": [
    {
      "id": "123",
      "timestamp": "2025-09-16T12:34:56Z",
      "event": "ROUTE_ACTIVATED|ROUTE_DEACTIVATED|SIGNAL_ASPECT_CHANGED|TRAIN_STOPPED_AT_STATION|TRAIN_DEPARTED_FROM_STATION|MESSAGE_RECEIVED|...",
      "category": "route|signal|train|system",
      "severity": "INFO",
      "object": { "id": "...", "type": "...", "serviceCode": "..." },
      "details": { "key": "value" }
    }
  ]
}
```

GET `/api/audit/stream`
- Server-Sent Events (SSE) stream. Emits events as:
```
event: audit
data: {"id":"...","timestamp":"...","event":"...", ...}
```
- Keep the connection open; a heartbeat comment is sent every ~25s.

FE Guide (example)
```javascript
// 1) Initial backfill via HTTP
let lastId = 0;
async function backfill() {
  const res = await fetch(`/api/audit/logs?sinceId=${lastId}&limit=500`);
  const json = await res.json();
  for (const it of json.items) {
    renderAudit(it);
    const n = Number(it.id);
    if (!Number.isNaN(n) && n > lastId) lastId = n;
  }
}

// 2) Live tail via SSE
const es = new EventSource('/api/audit/stream');
es.addEventListener('audit', (evt) => {
  const it = JSON.parse(evt.data);
  renderAudit(it);
  const n = Number(it.id);
  if (!Number.isNaN(n) && n > lastId) lastId = n;
});

// 3) Reconnect/backfill on resume (optional)
es.addEventListener('error', () => {
  // EventSource auto-reconnects. On resume, you can call backfill() to fill gaps.
});

function renderAudit(entry) {
  // Example: append to a table/list, filter by entry.category, etc.
}

// Kick off
backfill();
```

Notes
- The stream excludes high-frequency updates like `trainChanged` and `trackItemChanged` to avoid noise; use WebSocket for granular telemetry.
- `details` schema varies by event:
  - `SIGNAL_ASPECT_CHANGED`: `{ activeAspect, meansProceed, lastChanged }`
  - `TRAIN_STOPPED_AT_STATION`: `{ place:{code,name}, scheduledArrival, actualTime, delayMinutes }`
  - `TRAIN_DEPARTED_FROM_STATION`: `{ place:{code,name}, scheduledDeparture, actualTime, delayMinutes }`
  - `ROUTE_*`: `{ beginSignalId, endSignalId, persistent? }`
```


