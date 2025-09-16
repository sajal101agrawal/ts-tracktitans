# TS2 TrackTitans - Server API Requirements

## Overview
This document outlines the server-side API changes required to support the new production-ready features in the TS2 TrackTitans application.

## New API Endpoints Required

### 1. Enhanced Train Management

#### GET /api/trains/section/{sectionId}
Returns all trains currently in a specific section with detailed information.

**Response:**
```json
{
  "sectionId": "SEC_A",
  "currentTrains": [
    {
      "id": "T001",
      "serviceCode": "SVC001", 
      "status": "RUNNING",
      "speed": 75.5,
      "maxSpeed": 120,
      "position": {"x": 125.3, "y": 245.7},
      "route": ["Station_A", "Junction_B", "Station_C"],
      "delay": 2,
      "specs": {
        "type": "Express",
        "length": 250,
        "weight": 450,
        "passengers": 180,
        "maxPassengers": 200
      }
    }
  ],
  "incomingTrains": [...]
}
```

#### POST /api/trains/{trainId}/route
Accept/modify train routing decisions.

**Request:**
```json
{
  "action": "ACCEPT|REROUTE|HALT",
  "newRoute": ["Station_A", "Junction_C", "Station_D"],  // if REROUTE
  "reason": "Traffic optimization"
}
```

### 2. System Status Monitoring

#### GET /api/systems/signals
Returns current status of all traffic signals.

**Response:**
```json
{
  "signals": [
    {
      "id": "SIG_A1",
      "name": "Central Junction North",
      "position": {"x": 125, "y": 225},
      "status": "GREEN|YELLOW|RED",
      "type": "MAIN_SIGNAL|PLATFORM_SIGNAL",
      "section": "SEC_A",
      "lastChanged": "2025-09-16T14:15:30Z",
      "malfunctionStatus": "OPERATIONAL|WARNING|ERROR"
    }
  ]
}
```

#### PUT /api/systems/signals/{signalId}/status
Change signal status manually.

**Request:**
```json
{
  "newStatus": "GREEN|YELLOW|RED",
  "reason": "Manual override",
  "userId": "DISPATCHER_001"
}
```

#### POST /api/systems/maintenance
Mark track sections for maintenance.

**Request:**
```json
{
  "sectionId": "SEC_C",
  "maintenanceType": "SCHEDULED|EMERGENCY",
  "estimatedDuration": 120,  // minutes
  "reason": "Track inspection required"
}
```

### 3. KPI Analytics

#### GET /api/analytics/kpis
Returns current KPI values with time range filtering.

**Query Parameters:**
- `timeRange`: "1h|6h|1d|1w|1m"
- `trainType`: "all|express|regional|freight"

**Response:**
```json
{
  "timeRange": "1d",
  "timestamp": "2025-09-16T14:30:00Z",
  "kpis": {
    "punctuality": 87.5,
    "averageDelay": 3.2,
    "throughput": 245,
    "utilization": 78.5,
    "efficiency": 92.1,
    "performance": 89.3
  },
  "trends": {
    "punctuality": {"change": -2.1, "direction": "DOWN"},
    "throughput": {"change": 5.3, "direction": "UP"}
  }
}
```

#### GET /api/analytics/historical
Historical performance data for charting.

**Query Parameters:**
- `metric`: "punctuality|delay|throughput|utilization"
- `period`: "hourly|daily|weekly"
- `days`: number of days back

### 4. What-If Analysis

#### POST /api/simulation/whatif
Run what-if analysis scenarios.

**Request:**
```json
{
  "scenario": {
    "sectionId": "SEC_A",
    "additionalTrains": [
      {
        "type": "Express",
        "speed": 80,
        "destination": "Platform_1",
        "arrivalTime": "14:45:00"
      }
    ],
    "modifications": [
      {
        "type": "SIGNAL_CHANGE",
        "signalId": "SIG_A1",
        "newStatus": "GREEN"
      }
    ]
  }
}
```

**Response:**
```json
{
  "scenarioId": "scenario_12345",
  "predictions": {
    "throughput": 285.5,
    "averageDelay": 4.8,
    "utilization": 82.3,
    "bottlenecks": ["Junction_B"],
    "recommendations": [
      "Consider staggering train arrivals",
      "Monitor signal SIG_B1 timing"
    ]
  },
  "confidence": 0.87
}
```

### 5. AI Hints System

#### GET /api/ai/hints
Get AI-generated routing hints.

**Response:**
```json
{
  "hints": [
    {
      "id": "hint_1234",
      "type": "OPTIMIZATION|PREEMPTIVE|EFFICIENCY|MAINTENANCE",
      "priority": "HIGH|MEDIUM|LOW",
      "message": "Train T001 should be rerouted via Route_North to avoid 5-minute delay",
      "reasoning": "Current route shows congestion patterns...",
      "confidence": 85,
      "suggestedAction": {
        "type": "REROUTE",
        "trainId": "T001",
        "newRoute": ["Station_A", "Route_North", "Station_C"]
      }
    }
  ],
  "nextUpdate": "2025-09-16T14:33:00Z"
}
```

#### POST /api/ai/hints/{hintId}/respond
Respond to AI hints (accept/dismiss/override).

**Request:**
```json
{
  "response": "ACCEPT|DISMISS|OVERRIDE",
  "overrideAction": {  // if OVERRIDE
    "customRoute": ["Station_A", "Custom_Route", "Station_C"],
    "reason": "Local knowledge of track conditions"
  },
  "userId": "DISPATCHER_001"
}
```

### 6. Audit Logging

#### GET /api/audit/logs
Retrieve audit logs with filtering.

**Query Parameters:**
- `severity`: "INFO|WARNING|ERROR|NOTICE"
- `timeRange`: "1h|6h|1d|1w"
- `search`: "search term"
- `limit`: number of records
- `offset`: pagination offset

**Response:**
```json
{
  "logs": [
    {
      "id": "log_12345",
      "timestamp": "2025-09-16T14:27:15Z",
      "action": "TRAIN_DELAYED",
      "details": "Train T001 delayed by 2 minutes at Junction_B",
      "userId": "SYSTEM",
      "severity": "WARNING",
      "metadata": {
        "trainId": "T001",
        "section": "Junction_B",
        "delayMinutes": 2
      }
    }
  ],
  "totalCount": 1543,
  "hasMore": true
}
```

#### POST /api/audit/logs
Create new audit log entry.

**Request:**
```json
{
  "action": "MANUAL_OVERRIDE",
  "details": "Signal SIG_A1 manually changed to RED",
  "severity": "INFO",
  "metadata": {
    "signalId": "SIG_A1",
    "previousStatus": "GREEN",
    "newStatus": "RED"
  }
}
```

## WebSocket Events (Real-time Updates)

### Train Updates
```json
{
  "event": "TRAIN_STATUS_CHANGED",
  "data": {
    "trainId": "T001",
    "newStatus": "STOPPED",
    "position": {"x": 125.3, "y": 245.7},
    "delay": 3
  }
}
```

### Signal Updates
```json
{
  "event": "SIGNAL_STATUS_CHANGED", 
  "data": {
    "signalId": "SIG_A1",
    "newStatus": "RED",
    "timestamp": "2025-09-16T14:30:00Z"
  }
}
```

### KPI Updates
```json
{
  "event": "KPI_UPDATE",
  "data": {
    "kpi": "punctuality",
    "newValue": 86.2,
    "change": -1.3,
    "timestamp": "2025-09-16T14:30:00Z"
  }
}
```

### AI Hints Updates
```json
{
  "event": "NEW_AI_HINTS",
  "data": {
    "hints": [...],
    "generatedAt": "2025-09-16T14:30:00Z"
  }
}
```

## Database Schema Changes Required

### 1. New Tables

#### ai_hints
```sql
CREATE TABLE ai_hints (
  id VARCHAR(50) PRIMARY KEY,
  type VARCHAR(20) NOT NULL,
  priority VARCHAR(10) NOT NULL, 
  message TEXT NOT NULL,
  reasoning TEXT NOT NULL,
  confidence INTEGER NOT NULL,
  suggested_action JSON,
  status VARCHAR(20) DEFAULT 'PENDING',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  responded_at TIMESTAMP NULL,
  response_type VARCHAR(20) NULL,
  user_id VARCHAR(50) NULL
);
```

#### system_maintenance
```sql
CREATE TABLE system_maintenance (
  id VARCHAR(50) PRIMARY KEY,
  section_id VARCHAR(50) NOT NULL,
  maintenance_type VARCHAR(20) NOT NULL,
  status VARCHAR(20) DEFAULT 'SCHEDULED',
  estimated_duration INTEGER,
  actual_duration INTEGER NULL,
  reason TEXT,
  scheduled_start TIMESTAMP NOT NULL,
  actual_start TIMESTAMP NULL,
  actual_end TIMESTAMP NULL,
  created_by VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### kpi_snapshots
```sql
CREATE TABLE kpi_snapshots (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  timestamp TIMESTAMP NOT NULL,
  punctuality DECIMAL(5,2),
  average_delay DECIMAL(5,2),
  throughput DECIMAL(8,2),
  utilization DECIMAL(5,2),
  efficiency DECIMAL(5,2),
  performance DECIMAL(5,2),
  time_range VARCHAR(10) NOT NULL,
  train_type VARCHAR(20) DEFAULT 'all'
);
```

#### whatif_scenarios
```sql
CREATE TABLE whatif_scenarios (
  id VARCHAR(50) PRIMARY KEY,
  section_id VARCHAR(50) NOT NULL,
  scenario_data JSON NOT NULL,
  predicted_results JSON NOT NULL,
  confidence DECIMAL(3,2),
  created_by VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Enhanced Existing Tables

#### audit_logs (enhanced)
```sql
-- Add new columns to existing audit_logs table
ALTER TABLE audit_logs 
ADD COLUMN severity VARCHAR(20) DEFAULT 'INFO',
ADD COLUMN metadata JSON,
ADD COLUMN user_id VARCHAR(50),
ADD INDEX idx_severity (severity),
ADD INDEX idx_timestamp_desc (timestamp DESC);
```

#### signals (enhanced)
```sql
-- Add new columns to existing signals table  
ALTER TABLE signals
ADD COLUMN malfunction_status VARCHAR(20) DEFAULT 'OPERATIONAL',
ADD COLUMN last_maintenance TIMESTAMP NULL,
ADD COLUMN maintenance_due TIMESTAMP NULL;
```

## Authentication & Authorization

### Required Permissions
- `DISPATCHER`: Can accept/dismiss AI hints, change signals, manage trains
- `MAINTENANCE`: Can mark sections for maintenance, view system status
- `ANALYST`: Can view KPIs, run what-if scenarios, export reports
- `ADMIN`: Full access to all features and system configuration

### API Key Headers
```
Authorization: Bearer <jwt_token>
X-API-Key: <api_key>
X-User-Role: <role>
```

## Performance Requirements

### Response Times
- Real-time updates: < 100ms
- KPI queries: < 500ms
- What-if simulations: < 2s
- Historical data: < 1s
- Audit logs: < 300ms

### Throughput
- Support 100+ concurrent users
- Process 1000+ train updates per minute
- Handle 50+ AI hint generations per hour

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "TRAIN_NOT_FOUND",
    "message": "Train with ID T001 not found",
    "timestamp": "2025-09-16T14:30:00Z",
    "requestId": "req_12345"
  }
}
```

### Common Error Codes
- `TRAIN_NOT_FOUND`: Train ID doesn't exist
- `SECTION_UNAVAILABLE`: Section under maintenance
- `SIGNAL_MALFUNCTION`: Signal cannot be changed due to error
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions
- `SIMULATION_BUSY`: What-if simulation engine busy
- `INVALID_SCENARIO`: What-if scenario parameters invalid

## Implementation Priority

1. **Phase 1 (High Priority)**
   - Basic train management endpoints
   - System status monitoring
   - Enhanced audit logging

2. **Phase 2 (Medium Priority)**  
   - KPI analytics endpoints
   - AI hints system
   - WebSocket real-time updates

3. **Phase 3 (Low Priority)**
   - What-if analysis engine
   - Historical data analytics
   - Advanced reporting features

## Testing Requirements

### Unit Tests Required
- All endpoint functionality
- WebSocket event handling
- Database operations
- AI hint generation logic

### Integration Tests Required
- End-to-end train routing workflows
- Real-time update propagation
- Multi-user concurrent operations
- Performance under load

### Load Testing Targets
- 500 concurrent users
- 10,000 requests per minute
- 99th percentile response time < 1s
