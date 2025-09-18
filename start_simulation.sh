#!/bin/bash
echo "Starting TS2 TrackTitans Simulation..."
echo "Available simulations: demo, drain, liverpool-st, gretz-armainvilliers"
echo

if [ -z "$1" ]; then
    echo "Usage: ./start_simulation.sh [simulation_name]"
    echo "Example: ./start_simulation.sh liverpool-st"
    python3 run_simulation.py
else
    python3 run_simulation.py "$1"
fi
