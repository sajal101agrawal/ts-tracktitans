# Railway Simulator Control Guide

## 🚦 Route Setting (Signal Control)

### Basic Route Setting
- **Left-click** on the origin signal (where you want the route to start)
- **Left-click** on the destination signal (where the route should end)
- If the route is valid:
  - Track between signals highlights in white
  - Points (switches) automatically align
  - Origin signal changes from red → yellow/green

### Route Types

#### Normal Route
- Just click origin → destination

#### Persistent Route
- Hold **Shift** + click destination signal
- Shows a small white square next to the signal
- Route stays active after trains pass through

#### Forced Route
- Hold **Ctrl + Alt** + click destination
- ⚠️ **Dangerous** - bypasses safety checks!

### Cancel Routes
- **Right-click** on the origin signal to cancel its route

## 🚂 Train Control & Management

### View Train Information
- Click on any train code (e.g., "5O02", "1B04") on the track
- Or click train in the Train List (bottom panel)
- Train details appear in "Train Information" panel (right side)

### Train Control Menu
**Right-click** on any train (on track or in lists) to open train menu:

#### Available Actions

**Assign New Service**
- Changes the train's route/destination
- Select from available services in popup

**Reset Service**
- Makes train restart its current service
- Useful if train gets confused or delayed

**Reverse Train**
- Changes train direction
- Useful for terminus operations

### Train States & Control
- **Green trains**: Running normally
- **Red trains**: Stopped at signals
- **Yellow/Amber**: Approaching stations/signals

## 🏢 Station & Platform Management

### Station Information
- Click on platforms to see station timetables
- Shows arrivals/departures for that platform
- Displays which trains are scheduled

### Platform Operations
- Trains automatically stop at scheduled platforms
- Departure happens at scheduled time OR after minimum stop time
- Late trains depart after arrival + minimum dwell time

## Quick Tips

### Safety First
- Always use normal routes unless absolutely necessary
- Forced routes can cause collisions if used incorrectly
- Monitor train movements after setting routes

### Efficiency
- Use persistent routes for frequently used paths
- Check train information panels to understand delays
- Reset services if trains seem stuck or confused

### Troubleshooting
- If a train won't move: Check if route is set correctly
- If signals stay red: Look for conflicting routes
- If trains are delayed: Check platform dwell times and route conflicts