@echo off
echo Starting TS2 TrackTitans Simulation...
echo Available simulations: demo, drain, liverpool-st, gretz-armainvilliers
echo.
if "%1"=="" (
    echo Usage: start_simulation.bat [simulation_name]
    echo Example: start_simulation.bat liverpool-st
    python run_simulation.py
) else (
    python run_simulation.py %1
)
pause
