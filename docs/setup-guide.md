# 🚂 TrackTitans - Complete Setup Guide

**AI-Powered Train Traffic Control System**  
*Smart India Hackathon 2025 - Problem Statement ID: 25022*

A comprehensive railway simulation system with AI-enhanced train dispatching, predictive analytics, and intelligent decision-making developed by Team TrackTitans.

## 📋 Table of Contents

- [System Requirements](#system-requirements)
- [Prerequisites Installation](#prerequisites-installation)
  - [Windows Setup](#windows-setup)
  - [Mac Setup](#mac-setup)
- [Project Setup](#project-setup)
- [Running the Simulation](#running-the-simulation)
- [Available Simulations](#available-simulations)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## 🖥️ System Requirements

### Minimum Requirements
- **Operating System**: Windows 10+ or macOS 10.14+
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB free space
- **Network**: Internet connection for downloading dependencies

### Software Requirements
- **Go**: Version 1.13 or higher
- **Python**: Version 3.6 or higher (Python 3.8+ recommended)
- **Git**: For cloning the repository

## 🔧 Prerequisites Installation

### Windows Setup

#### Step 1: Install Python 3
1. Go to [python.org](https://www.python.org/downloads/windows/)
2. Download Python 3.8+ (64-bit recommended)
3. **Important**: During installation, check ✅ "Add Python to PATH"
4. Verify installation:
   ```cmd
   python --version
   pip --version
   ```

#### Step 2: Install Go
1. Go to [golang.org/dl](https://golang.org/dl/)
2. Download the Windows installer (`.msi` file)
3. Run the installer with default settings
4. Verify installation:
   ```cmd
   go version
   ```

#### Step 3: Install Git
1. Go to [git-scm.com](https://git-scm.com/download/win)
2. Download and install with default settings
3. Verify installation:
   ```cmd
   git --version
   ```

#### Step 4: Install Required Python Packages
Open Command Prompt or PowerShell and run:
```cmd
# Install PyQt5 (NOT PyQt6 - this is important!)
pip install PyQt5

# Install WebSocket support
pip install websocket-client

# Install JSON handling
pip install simplejson

# Install HTTP requests library
pip install requests
```

### Mac Setup

#### Step 1: Install Homebrew (if not already installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Step 2: Install Python 3
```bash
# Install Python 3 using Homebrew
brew install python

# Verify installation
python3 --version
pip3 --version
```

#### Step 3: Install Go
```bash
# Install Go using Homebrew
brew install go

# Verify installation
go version
```

#### Step 4: Install Git (usually pre-installed)
```bash
# Install if needed
brew install git

# Verify installation
git --version
```

#### Step 5: Install Required Python Packages
```bash
# Install PyQt5 (NOT PyQt6 - this is important!)
pip3 install PyQt5

# Install WebSocket support  
pip3 install websocket-client

# Install JSON handling
pip3 install simplejson

# Install HTTP requests library
pip3 install requests
```

## 📁 Project Setup

### Method 1: Automated Setup (Recommended) 🚀

**After installing Python 3 and Go**, you can use the automated setup script:

```bash
# Clone the project
git clone https://github.com/your-username/ts-tracktitans.git
cd ts-tracktitans

# Run the automated setup script
python setup_environment.py     # Windows
python3 setup_environment.py    # Mac
```

**The setup script will automatically:**
- ✅ Check your Python and Go installations
- ✅ Install all required Python packages (PyQt5, websocket-client, simplejson, requests)
- ✅ Set up Go server dependencies
- ✅ Build the server binary for optimal performance
- ✅ Create quick-start helper scripts
- ✅ Verify everything is working correctly

### Method 2: Manual Setup (Advanced Users)

If you prefer manual control or the automated setup fails:

#### Step 1: Clone the Repository
```bash
# Clone the project
git clone https://github.com/your-username/ts-tracktitans.git
cd ts-tracktitans
```

#### Step 2: Install Python Dependencies
```bash
# On Windows
pip install PyQt5 websocket-client simplejson requests

# On Mac  
pip3 install PyQt5 websocket-client simplejson requests
```

#### Step 3: Set Up Go Server Dependencies
```bash
# Navigate to server directory
cd server

# Download and install Go dependencies
go mod download
go mod tidy

# Build the server (optional but recommended)
go build -o ts2-sim-server .

# Go back to project root
cd ..
```

#### Step 4: Verify Installation
```bash
# On Windows
python -c "import PyQt5, websocket, simplejson, requests; print('✅ All Python dependencies installed')"

# On Mac  
python3 -c "import PyQt5, websocket, simplejson, requests; print('✅ All Python dependencies installed')"
```

## 🚀 Running the Simulation

### Quick Start (Recommended)

The easiest way to run the system is using the automated script:

```bash
# On Windows
python run_simulation.py liverpool-st

# On Mac
python3 run_simulation.py liverpool-st
```

This single command will:
1. ✅ Start the Go server in the background
2. ✅ Load the specified simulation
3. ✅ Launch the Python client and auto-connect to the server
4. ✅ Handle cleanup when you press Ctrl+C

### Manual Setup (Advanced Users)

If you prefer to start components manually:

#### Terminal 1: Start the Server
```bash
cd server

# Windows
go run . ../simulations/liverpool-st.json

# Mac  
go run . ../simulations/liverpool-st.json
```

#### Terminal 2: Start the Client
```bash
# Go back to project root
cd ..

# Windows
python start-ts2.py

# Mac
python3 start-ts2.py
```

Then manually connect to `localhost:22222` in the client interface.

## 🎮 Available Simulations

Run without arguments to see available simulations:
```bash
# Windows
python run_simulation.py

# Mac
python3 run_simulation.py
```

### Current Simulations:
- **`demo`** - Simple demonstration simulation
- **`drain`** - Drainage system simulation  
- **`liverpool-st`** - Liverpool Street station (complex, recommended)
- **`gretz-armainvilliers`** - French railway simulation

### Usage Examples:
```bash
# Start Liverpool Street (most comprehensive)
python run_simulation.py liverpool-st

# Start demo simulation (good for beginners)
python run_simulation.py demo

# Start drainage simulation
python run_simulation.py drain

# Start French railway simulation
python run_simulation.py gretz-armainvilliers
```

## 🎯 How to Play

### Basic Controls
1. **Route Setting**: Click on a signal, then click on the next signal to set a route
2. **Train Information**: Click on trains to see their details
3. **Station Information**: Click on platforms to see timetables
4. **Train Control**: Right-click on trains for advanced options

### Game Objective
- Dispatch trains efficiently across the network
- Keep trains on schedule 
- Avoid delays and conflicts
- Maintain safety by proper signal management

### Scoring
- Points are deducted for late arrivals
- Points are deducted for wrong platform stops
- Points are deducted for routing errors

## 🛠️ Troubleshooting

### Common Issues

#### "Port 22222 is already in use"
```bash
# The script should handle this automatically, but if it doesn't:

# Windows
netstat -ano | findstr :22222
taskkill /PID <PID_NUMBER> /F

# Mac/Linux  
lsof -ti:22222 | xargs kill -9
```

#### "go: command not found"
- Restart your terminal after installing Go
- Check that Go is in your PATH:
  ```bash
  echo $PATH  # Mac/Linux
  echo %PATH% # Windows
  ```

#### "python: command not found" (Mac)
- Use `python3` instead of `python` on Mac
- Add alias: `echo 'alias python=python3' >> ~/.zshrc`

#### "No module named 'PyQt5'"
```bash
# Make sure you're using the right Python version
# Windows
python -m pip install PyQt5

# Mac  
python3 -m pip install PyQt5
```

#### "ImportError: No module named 'simplejson'"
```bash
# Windows
pip install simplejson

# Mac
pip3 install simplejson
```

#### Server Won't Start
1. Check Go installation: `go version`
2. Navigate to server directory: `cd server`
3. Update dependencies: `go mod tidy`
4. Try building manually: `go build .`

#### Client Won't Connect
1. Make sure server is running first
2. Check server is listening on port 22222
3. Try manual connection using `start-ts2.py`

### Performance Issues

#### Slow Performance
- Close unnecessary applications
- Use a smaller simulation (demo instead of liverpool-st)
- Check available RAM and disk space

#### Graphics Issues
- Update graphics drivers
- Try running in compatibility mode (Windows)
- Check PyQt5 installation

## 🔧 Advanced Usage

### Editor Mode
To create or edit simulations:
```bash
# Windows
python start-ts2.py -e simulations/demo.json

# Mac
python3 start-ts2.py -e simulations/demo.json
```

### Debug Mode
For development and troubleshooting:
```bash
# Windows  
python start-ts2.py -d

# Mac
python3 start-ts2.py -d
```

### Custom Server Host
To connect to a remote server:
```bash
# Windows
python start-ts2.py -s path/to/custom/server

# Mac  
python3 start-ts2.py -s path/to/custom/server
```

## 📚 Additional Resources

### Documentation
- **Technical Manual**: `server/docs/ts2-technical-manual.pdf`
- **API Documentation**: `SERVER_API_REQUIREMENTS.md`
- **Custom Layout Guide**: `Custom_Layout_Creation_Guide.md`

### Project Links
- **Homepage**: [ts2.github.io](http://ts2.github.io/)
- **GitHub**: [github.com/ts2](http://github.com/ts2/)
- **Issues**: Report bugs and feature requests on GitHub

## 🤝 Getting Help

### Before Asking for Help
1. ✅ Check this README thoroughly
2. ✅ Try the troubleshooting steps
3. ✅ Verify all dependencies are installed correctly
4. ✅ Test with the demo simulation first

### Where to Get Help
- **GitHub Issues**: For bugs and feature requests
- **Technical Manual**: For gameplay and advanced features
- **IRC**: `irc.freenode.net#trainsigsim`

## 📝 Quick Reference Commands

### First-Time Setup (Automated)
```bash
# 1. Install Python 3, Go, and Git (see above)
# 2. Clone repository
git clone https://github.com/your-username/ts-tracktitans.git
cd ts-tracktitans

# 3. Run automated setup (installs everything automatically)
python setup_environment.py     # Windows
python3 setup_environment.py    # Mac

# 4. Run simulation
python run_simulation.py demo      # Windows
python3 run_simulation.py demo     # Mac
```

### First-Time Setup (Manual)
```bash
# 1. Install Python 3, Go, and Git (see above)
# 2. Clone repository
git clone https://github.com/your-username/ts-tracktitans.git
cd ts-tracktitans

# 3. Install Python dependencies
pip install PyQt5 websocket-client simplejson requests  # Windows
pip3 install PyQt5 websocket-client simplejson requests # Mac

# 4. Setup Go dependencies  
cd server && go mod tidy && cd ..

# 5. Run simulation
python run_simulation.py demo      # Windows
python3 run_simulation.py demo     # Mac
```

### Daily Usage
```bash
# Start any simulation
python run_simulation.py [simulation-name]   # Windows
python3 run_simulation.py [simulation-name]  # Mac

# Stop simulation
# Press Ctrl+C in the terminal
```

---

🎉 **You're all set!** Start with the `demo` simulation to get familiar with the controls, then try `liverpool-st` for a more complex experience.

**Happy dispatching! 🚂✨**
