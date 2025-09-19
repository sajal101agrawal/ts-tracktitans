# TrackTitans - Custom Layout Creation Guide

**Smart India Hackathon 2025 - AI-Enhanced Railway System**

## Overview

This guide provides comprehensive instructions for creating custom station layouts, tracks, and sections in the **TrackTitans** AI-powered train traffic control system editor. The editor is a sophisticated Qt-based application that allows you to design realistic railway layouts with proper signaling, AI-optimized routing, and intelligent train operations.

TrackTitans enhances traditional layout design with AI-powered optimization suggestions, predictive conflict detection, and intelligent routing capabilities that work seamlessly with your custom designs.

## Table of Contents

1. [Editor Overview](#editor-overview)
2. [Available Track Elements](#available-track-elements)
3. [Step-by-Step Layout Creation](#step-by-step-layout-creation)
4. [Advanced Layout Techniques](#advanced-layout-techniques)
5. [Best Practices](#best-practices)
6. [Common Layout Patterns](#common-layout-patterns)
7. [Example Layouts](#example-layouts)
8. [Troubleshooting](#troubleshooting)

## Editor Overview

The ts-tracktitans editor features six main tabs:

- **General**: Simulation metadata and options
- **Scenery**: Track layout design (primary workspace)
- **Routes**: Signal-to-signal route definitions
- **Rolling Stock**: Train type definitions
- **Services**: Timetables and train schedules
- **Trains**: Individual train management

### Key Interface Elements

- **Tools Panel**: Track element library (right side)
- **Properties Panel**: Selected item properties (right side)
- **Canvas**: Main design area with grid snapping
- **Toolbar**: Pan/Selection tools and zoom controls

## Available Track Elements

### Core Track Elements

#### LineItem
- **Purpose**: Basic straight track segments
- **Properties**:
  - `realLength`: Physical length in meters (affects train timing)
  - `placeCode`: Station/location identifier
  - `trackCode`: Track identifier within a location
  - `maxSpeed`: Speed limit for the segment

#### PointsItem (Switches/Turnouts)
- **Purpose**: Three-way junctions for creating branches
- **Components**:
  - Common End: Entry point
  - Normal End: Straight-through route
  - Reverse End: Diverging route
- **Properties**:
  - Position coordinates for each end
  - Linked track items for each direction
  - Current switch position (normal/reverse)

#### PlatformItem
- **Purpose**: Station platforms (visual and functional)
- **Appearance**: Green rectangles on the layout
- **Properties**:
  - Platform dimensions (start and end points)
  - Associated place and track codes
  - Visual representation for passengers

#### SignalItem
- **Purpose**: Train control and route definition
- **Types**:
  - `UK_3_ASPECTS`: Red/Yellow/Green signals
  - `BUFFER`: Buffer stop signals
  - Custom types via signal library
- **Properties**:
  - Signal position and orientation
  - Associated route conditions
  - Aspect display logic

#### EndItem
- **Purpose**: Track terminations (buffer stops)
- **Usage**: Marks the end of track sections
- **Common locations**: Terminal stations, sidings

#### PlaceItem
- **Purpose**: Named locations (stations, junctions, depots)
- **Function**: Groups tracks and platforms under common names
- **Properties**: Place code and descriptive name

### Utility Elements

#### InvisibleLinkItem
- **Purpose**: Hidden track connections
- **Usage**: Complex routing scenarios
- **Benefits**: Maintains logical connections without visual clutter

#### TextItem
- **Purpose**: Layout annotations and labels
- **Usage**: Station names, operational notes
- **Properties**: Text content and positioning

## Step-by-Step Layout Creation

### 1. Planning Phase

Before starting construction, consider:

```
Layout Requirements:
□ Station locations and types (through/terminal)
□ Track configuration (single/double/multiple)
□ Junction locations and connectivity
□ Signal placement strategy
□ Service patterns and train movements
□ Operational scenarios
```

### 2. Basic Construction Process

#### Setting Up the Workspace
1. Open the **Scenery tab**
2. Select appropriate tool (Pan/Selection)
3. Set zoom level for comfortable working
4. Enable grid snapping (5-pixel grid default)

#### Placing Track Elements
```markdown
Drag and Drop Process:
1. Select element from Tools Panel
2. Drag to desired canvas location
3. Element snaps to grid automatically
4. Use Properties Panel to adjust settings
5. Validate connections as you build
```

#### Connecting Elements
Track items connect through ID references:
- `nextTiId`: Following track item
- `previousTiId`: Preceding track item
- `reverseTiId`: Reverse branch (for points)

### 3. Station Creation

#### Basic Station Components
```json
Station Structure:
{
  "place": {
    "__type__": "Place",
    "placeCode": "STN",
    "name": "STATION NAME"
  },
  "platform": {
    "__type__": "PlatformItem",
    "placeCode": "STN",
    "trackCode": "1",
    "x": 100, "y": 100,
    "xf": 200, "yf": 120
  },
  "track": {
    "__type__": "LineItem",
    "placeCode": "STN",
    "trackCode": "1",
    "realLength": 150.0
  }
}
```

#### Multi-Platform Stations
```markdown
Configuration Steps:
1. Create Place item with station code
2. Add multiple PlatformItem objects
3. Use different trackCode for each platform
4. Connect with LineItem tracks
5. Add PointsItem for track selection
6. Install approach signals
```

### 4. Junction Design

#### Points Configuration
```json
{
  "__type__": "PointsItem",
  "name": "Junction_A",
  "x": 245, "y": 100,
  "xf": 5, "yf": 0,     // Common end (relative to center)
  "xn": -5, "yn": 0,    // Normal end
  "xr": -5, "yr": 5,    // Reverse end
  "nextTiId": "main_line",
  "reverseTiId": "branch_line"
}
```

#### Junction Types
- **Simple Junction**: One main line, one branch
- **Crossover**: Connecting parallel tracks
- **Flying Junction**: Grade-separated crossing
- **Complex Junction**: Multiple converging routes

### 5. Signal Implementation

#### Signal Placement Strategy
```markdown
Signal Location Principles:
- Entry/Exit points of stations
- Before and after junctions
- Block section boundaries
- Speed restriction points
- Approach to level crossings
```

#### Signal Configuration
```json
{
  "__type__": "SignalItem",
  "name": "Signal_A",
  "signalType": "UK_3_ASPECTS",
  "x": 500, "y": 100,
  "xn": 520, "yn": 105,
  "reverse": false,
  "maxSpeed": 25.0
}
```

### 6. Route Definition

Routes define valid signal-to-signal paths:

```json
{
  "__type__": "Route",
  "id": "1",
  "beginSignal": "SIG_A",
  "endSignal": "SIG_B",
  "directions": {
    "points_1": 0,    // 0=normal, 1=reverse
    "points_2": 1
  },
  "initialState": 0   // 0=inactive, 1=set, 2=cleared
}
```

## Advanced Layout Techniques

### 1. Complex Station Designs

#### Through Station
```
 ──────●═══════●──────  Platform 1
       │       │
 ──────●═══════●──────  Platform 2
     Signals
```

#### Terminal Station
```
 ──────●═══════■  Platform 1
       │       ■
 ──────●═══════■  Platform 2
     Signal  Buffers
```

#### Bay Platform Configuration
```
 ──────●═══════●──────  Main Line
       │       
       └───●═══■       Bay Platform
         Signal Buffer
```

### 2. Double Track Main Line

```
UP:   ●═══════●═══════●═══════●
                              
DN:   ●═══════●═══════●═══════●
    Station A      Junction    Station B
```

### 3. Branch Line Junction

```
Main Line: ●═══════◊═══════●
                   │
Branch:            └───●═══■
                    Signal Buffer
```

### 4. Realistic Track Geometry

#### Curve Simulation
While the editor uses straight segments, create curves using:
- Multiple short LineItem segments
- Slight angle changes between segments
- Appropriate speed restrictions on curves

#### Track Spacing
- Standard gauge consideration in positioning
- Platform clearance requirements
- Signal sight line requirements

## Best Practices

### Design Principles

1. **Prototype-Based Design**
   - Study real railway layouts
   - Understand operational requirements
   - Apply realistic constraints

2. **Incremental Development**
   - Start with basic track layout
   - Add signals and routes
   - Test with train movements
   - Refine based on operation

3. **Validation Workflow**
   ```markdown
   Regular Validation Steps:
   1. Use "Validate Scenery" button frequently
   2. Check all track connections
   3. Verify signal placement
   4. Test route definitions
   5. Run train services to test operation
   ```

### Performance Optimization

#### Track Segment Sizing
```markdown
Optimal Practices:
- Keep segments 50-500m in real length
- Avoid extremely short segments (<10m)
- Use appropriate detail level for scale
- Consider processing performance
```

#### Memory Management
- Limit total track items (< 1000 for good performance)
- Use invisible links sparingly
- Optimize graphic complexity

### Layout Organization

#### Naming Conventions
```markdown
Systematic Naming:
- Place Codes: 3-letter station codes (STN, JCT, DPT)
- Track Codes: Platform numbers (1, 2) or directions (UP, DN)
- Signal Names: Sequential (SIG_001) or location-based
- Route IDs: Sequential numbers or descriptive codes
```

#### File Management
```markdown
Project Organization:
- Save frequently during development
- Use descriptive filenames
- Maintain backup copies
- Document layout changes
- Version control for complex projects
```

## Common Layout Patterns

### 1. Simple Branch Line
```
Station A ──track── Junction ──track── Station B
                     │
                  Points
                     │
                Branch to Station C
```

### 2. Passing Loop
```
        ┌───Points───●═══════●───Points───┐
Main ───┤                               ├─── Main
        └───────────●═══════●───────────┘
                  Passing Loop
```

### 3. Triangle Junction
```
     Station A
         │
    ┌────●────┐
    │         │
Station B ●───● Station C
```

### 4. Double Junction
```
UP Main ●═══◊═══●═══◊═══●
            │       │
            └───●───┘
             Branch
            │       │
DN Main ●═══◊═══●═══◊═══●
```

## Example Layouts

### Example 1: Simple Two-Station Layout

```json
{
  "title": "Simple Branch Line",
  "description": "Basic two-station layout with single track",
  
  "places": {
    "STN_A": {"name": "Station Alpha", "code": "STA"},
    "STN_B": {"name": "Station Beta", "code": "STB"}
  },
  
  "track_sequence": [
    "Platform STA",
    "Exit Signal A",
    "Main Line Track",
    "Approach Signal B", 
    "Platform STB"
  ],
  
  "services": [
    "STA to STB shuttle service",
    "Return working STB to STA"
  ]
}
```

### Example 2: Junction Layout

```markdown
Construction Sequence:
1. Create main line stations
2. Add branch line terminus
3. Install junction points
4. Place approach signals
5. Define three routes:
   - Main to Main (through)
   - Main to Branch
   - Branch to Main
6. Set up shuttle services
```

## Troubleshooting

### Common Issues

#### Track Connection Problems
```markdown
Symptoms: Trains stop unexpectedly, route failures
Solutions:
- Check nextTiId/previousTiId consistency
- Verify all track items are connected
- Use "Validate Scenery" to identify breaks
- Ensure points have correct reverse connections
```

#### Signal Placement Issues
```markdown
Symptoms: Routes won't set, signal aspects incorrect
Solutions:
- Verify signal direction (reverse property)
- Check signal-to-track positioning
- Ensure signals are on correct track items
- Review route definitions for signal coverage
```

#### Performance Problems
```markdown
Symptoms: Slow response, graphics lag
Solutions:
- Reduce total number of track items
- Simplify complex junction areas
- Optimize train graphics settings
- Check for infinite loops in routing
```

### Validation Checklist

```markdown
Pre-Operation Checklist:
□ All tracks connected properly
□ Signals face correct direction
□ Routes defined for all movements
□ Place codes assigned correctly
□ Track codes are unique within places
□ Services reference valid places/tracks
□ Train types configured
□ No orphaned track items
□ Performance is acceptable
□ Layout tested with train movements
```

## Data Import/Export

### CSV Workflow

The editor supports bulk operations via CSV:

#### Track Items Export/Import
1. Use "Export" button in Scenery tab
2. Edit CSV in spreadsheet application
3. Import modified data
4. Validate scenery after import

#### Supported CSV Operations
- Bulk property changes
- Mass coordinate adjustments
- Track code standardization
- Speed limit updates

### Backup Strategy

```markdown
Recommended Backup Approach:
- Save .ts2 files regularly
- Export CSV periodically for external backup
- Document major layout changes
- Keep multiple versions during development
- Test backups by loading in clean editor
```

## Advanced Topics

### Custom Signal Types

Extend the signal library:
1. Define new signal aspects in signal library
2. Create signal states with conditions
3. Assign to SignalItem objects
4. Test with route operations

### Scripting Integration

For complex layouts, consider:
- CSV preprocessing scripts
- Automated track generation
- Bulk coordinate transformations
- Layout validation scripts

### Performance Monitoring

```python
# Monitor editor performance:
- Track item count
- Graphics update frequency
- Memory usage during operation
- Route calculation time
```

## Conclusion

Creating custom layouts in ts-tracktitans requires understanding both railway operations and the editor's capabilities. Start with simple designs, validate frequently, and build complexity gradually. The editor's powerful tools support everything from basic branch lines to complex metropolitan railway systems.

For additional support:
- Study the included example simulations
- Experiment with the editor's import/export features  
- Join the community for layout sharing and advice
- Refer to real railway prototype information

---

*This guide covers ts-tracktitans editor version 0.7. Features and interface may vary in different versions.*


