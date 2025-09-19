# TS2 Simulation Runner

A convenient Python script to automatically start both the Go server and Python client for TS2 simulations.

## 🚀 Quick Start

### Basic Usage
```bash
python run_simulation.py [simulation_name]
```

### Examples
```bash
# Start Liverpool Street simulation
python run_simulation.py liverpool-st

# Start demo simulation  
python run_simulation.py demo

# Start drainage simulation
python run_simulation.py drain

# Start Gretz-Armainvilliers simulation
python run_simulation.py gretz-armainvilliers
```

### See Available Simulations
```bash
# List all available simulations
python run_simulation.py --help

# Or run without arguments
python run_simulation.py
```

## 📁 File Organization

All simulation files are now consolidated in the `/simulations` folder:
- `demo.json` - Demo simulation
- `drain.json` - Drainage simulation 
- `gretz-armainvilliers.json` - French railway simulation
- `liverpool-st.json` - Liverpool Street station simulation

## 🔧 How It Works

The script automatically:

1. **Validates** the simulation file exists
2. **Starts the Go server** in the background from the `/server` directory with the simulation
3. **Starts the Python client** and auto-connects to the running server
4. **Handles cleanup** when you press Ctrl+C or when the processes finish

## ⚡ Features

- **Automatic process management** - No need to manually start/stop server and client
- **Port cleanup** - Automatically detects and kills any existing processes on port 22222
- **Graceful shutdown** - Press Ctrl+C to cleanly stop both processes
- **Error handling** - Clear error messages if something goes wrong
- **Available simulation listing** - See what simulations are available
- **Path validation** - Ensures all required files and directories exist

## 🛑 Stopping the Simulation

Press `Ctrl+C` to stop both the server and client processes. The script will handle cleanup automatically.

## 🐛 Troubleshooting

### Server won't start
- Make sure you have Go installed and the server dependencies are available
- Check that `go mod tidy` runs successfully in the `/server` directory
- If you get "address already in use" error, the script should automatically handle it
- If automatic cleanup fails, manually run: `sudo lsof -ti:22222 | xargs kill -9`

### Client won't start  
- Make sure Python 3 is installed
- Check that the required Python dependencies are installed (see main README.md)

### Simulation file not found
- Make sure the simulation file exists in the `/simulations` directory
- Use `python run_simulation.py` to see available simulations

## 🔧 Technical Details

### Old vs New Commands

**Before (manual):**
```bash
# Start server (in server directory)
go run . /path/to/simulation.json | cat

# Start client (in root directory)  
python start-ts2.py "/simulations/simulation.json"
# Then manually select server connection in dialog
```

**Now (automatic):**
```bash
# One command does everything
python run_simulation.py simulation-name
# Server starts automatically + client auto-connects
```

### Process Management
- Server runs in background with output captured
- Client runs in foreground (you can interact with it)
- Both processes are automatically cleaned up on exit

## 📂 Directory Structure
```
ts-tracktitans/
├── run_simulation.py          # The runner script
├── start-ts2.py              # Original client starter
├── simulations/              # All simulation files (consolidated)
│   ├── demo.json
│   ├── drain.json  
│   ├── gretz-armainvilliers.json
│   └── liverpool-st.json
└── server/                   # Go server
    ├── main.go
    ├── go.mod
    └── ...
```
