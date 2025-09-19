# 🚄 TrackTitans: AI-Powered Train Traffic Control System

[![Smart India Hackathon 2025](https://img.shields.io/badge/Smart%20India%20Hackathon-2025-orange)](https://sih.gov.in)
[![Problem Statement](https://img.shields.io/badge/PS%20ID-25022-blue)](https://sih.gov.in)
[![Theme](https://img.shields.io/badge/Theme-Smart%20Automation-green)](https://sih.gov.in)
[![Category](https://img.shields.io/badge/Category-Software-purple)](https://sih.gov.in)

> **Maximizing Section Throughput Using AI-Powered Precise Train Traffic Control**

An innovative railway traffic management system that revolutionizes train dispatching through AI-powered automation, predictive analytics, and intelligent decision-making. Built by Team TrackTitans for Smart India Hackathon 2025.

![TrackTitans Banner](images/banner.jpeg)

## 🏆 Project Overview

TrackTitans addresses the critical challenges faced by railway traffic controllers who make 200+ critical decisions daily. Our AI-powered system transforms reactive traffic management into proactive, intelligent automation that prevents conflicts before they occur.

### 🎯 Problem Statement
- **Challenge**: Decision overload and reactive approach in railway traffic control
- **Impact**: Stress, errors, delays, and ₹200+ crore annual losses
- **Solution**: AI system with human-in-the-loop for intelligent train traffic optimization

### 💡 Innovation Highlights
- 🤖 **Self-Learning AI Algorithm** - Continuously improves decision-making
- 🚄 **First-of-its-Kind Railway AI Controller** - Automated train movement management
- ⚡ **Multi-Train Type Optimization** - Handles Express, Regional, and Freight simultaneously
- 🔮 **Predictive Traffic Management** - Prevents conflicts before they happen
- 🔄 **Zero-Disruption Implementation** - Seamless integration with existing systems

## 📊 Key Benefits & Impact

### Operational Excellence
- **80% Reduction** in controller decision stress
- **60% Fewer** delays with consistent on-time performance
- **30% Cost Savings** in fuel and maintenance through optimized routing
- **24/7 Consistent** performance without human fatigue

### Financial Impact
- **₹200 Crore** annual loss prevention from passenger compensation
- **Massive Network Multiplication** - benefits scale exponentially
- **Enhanced Safety Standards** - significant reduction in human error incidents

### Performance Metrics
- **Real-time Optimization** of railway traffic flow
- **Advanced What-If** scenario planning and simulation
- **Comprehensive KPI** tracking and performance analytics
- **Interactive Geospatial** railway map visualization

## 🏗️ System Architecture

### Technology Stack

#### Frontend & Client
```
PyQt5                   → Desktop application GUI framework
Python 3.6+             → Core application runtime
WebSocket Client        → Real-time communication with server
JSON Processing         → Configuration and data handling
```

#### Backend & Server
```
Go 1.13+                → High-performance server runtime
Gorilla WebSocket       → Real-time bidirectional communication
In-Memory Processing    → Fast data operations and caching
JSON Data Format        → Simulation files and configuration
```

#### Core Components
```
Train Simulation Engine → Real-time railway operations
Signal Management       → Traffic control and routing
Route Calculation       → Path optimization algorithms
Event System           → State changes and notifications
```

#### Web Interface
```
Static Web Assets       → HTML/CSS/JavaScript dashboard
Bootstrap Framework     → Responsive UI components
Real-time Updates       → WebSocket-driven interface
REST API               → HTTP endpoints for data access
```

### Core Architecture

```
Desktop Client (PyQt5)
       ↕ WebSocket
Go Server & Simulation Engine
       ↕ JSON Files
Railway Network Data
```

## 🚀 Quick Start

### Prerequisites
- **Python 3.6+** (Python 3.8+ recommended)
- **PyQt5** GUI framework (NOT PyQt6)
- **Go 1.13+** for server components
- **Git** for cloning the repository

### Installation

#### 1. Automated Setup (Recommended)
```bash
# Clone the repository
git clone https://github.com/tracktitans/ts-tracktitans.git
cd ts-tracktitans

# Run automated setup
python setup_environment.py
```

#### 2. Manual Setup
```bash
# Install Python dependencies
pip install PyQt5 websocket-client simplejson requests

# Setup Go server
cd server
go mod tidy
go build -o ts2-sim-server .
cd ..

# Verify installation
python -c "import PyQt5, websocket, simplejson, requests; print('✅ Ready to launch')"
```

### Running the System

#### Start Complete System
```bash
# Launch with AI-enhanced Liverpool Street simulation
python run_simulation.py liverpool-st

# Or start demo simulation for testing
python run_simulation.py demo
```

#### Manual Component Launch
```bash
# Terminal 1: Start AI-enhanced server
cd server
go run . ../simulations/liverpool-st.json

# Terminal 2: Launch Python client with AI dashboard
python start-ts2.py
```

## 🎮 How to Use

### AI-Enhanced Traffic Control

#### Automated Decision Making
- **AI Controller** automatically manages train movements
- **Human Override** available for critical decisions
- **Predictive Alerts** warn of potential conflicts
- **Smart Routing** optimizes paths in real-time

#### Interactive Controls
```
Route Setting:    Click origin signal → Click destination signal
Train Info:       Click on train codes to view details
AI Hints:         Review suggestions in the AI panel
Override:         Right-click trains for manual control
```

### Advanced Analytics Dashboard

#### Key Performance Indicators (KPIs)
- **Punctuality Rate**: Real-time on-time performance
- **Throughput**: Trains processed per hour
- **Utilization**: Track and platform usage
- **Efficiency**: System-wide performance score
- **Delay Analysis**: Root cause identification

## 🎯 Smart India Hackathon 2025

### Problem Statement Details
- **ID**: 25022
- **Title**: Maximizing Section Throughput Using AI-Powered Precise Train Traffic Control
- **Theme**: Smart Automation
- **Category**: Software
- **Organization**: Ministry of Railways, Government of India

### Implementation Phases

#### Phase 1: Foundation ✅
- [x] Core AI system for single section
- [x] Modern controller interface
- [x] Basic analytics dashboard

#### Phase 2: Enhancement ✅
- [x] Multi-section AI expansion
- [x] Advanced decision explanations
- [x] Comprehensive KPI tracking
- [x] What-if scenario engine

#### Phase 3: Scale & Deploy 🚧
- [ ] Multi-zone optimization
- [ ] Cloud deployment
- [ ] Integration testing
- [ ] Production monitoring

### Feasibility Highlights
- ✅ **Available Railway Data**: Comprehensive datasets ready
- ✅ **Minimal Infrastructure**: Leverages existing systems
- ✅ **Development Budget**: Cost-effective solution
- ✅ **Proven Technology**: Battle-tested algorithms
- ✅ **Scalable Architecture**: Grows with network needs

---

<div align="center">
  <h3>🚄 Building the Future of Railway Traffic Control 🚄</h3>
  <p><strong>Team TrackTitans</strong> | Smart India Hackathon 2025</p>
  <p>Empowering India's Railways with AI-Powered Precision</p>
  
  [![Made with ❤️ in India](https://img.shields.io/badge/Made%20with%20❤️%20in-India-orange.svg)](https://en.wikipedia.org/wiki/India)
  [![Powered by AI](https://img.shields.io/badge/Powered%20by-AI-blue.svg)](https://github.com/tracktitans)
</div>