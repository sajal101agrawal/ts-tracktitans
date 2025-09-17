#!/usr/bin/env python3
"""
TS2 Simulation Runner

This script automatically starts both the Go server and Python client with a specified simulation.
Usage: python run_simulation.py [simulation_name]

Available simulations: demo, drain, gretz-armainvilliers, liverpool-st
"""

import argparse
import os
import sys
import subprocess
import time
import signal
import atexit
from pathlib import Path

# Global variables for process management
server_process = None
client_process = None

def cleanup_processes():
    """Clean up running processes on exit"""
    global server_process, client_process
    
    print("\n🧹 Cleaning up processes...")
    
    if client_process and client_process.poll() is None:
        print("Terminating client process...")
        client_process.terminate()
        try:
            client_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            client_process.kill()
    
    if server_process and server_process.poll() is None:
        print("Terminating server process...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
    
    print("✅ Cleanup completed")

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print(f"\n⚠️  Received signal {signum}, shutting down...")
    cleanup_processes()
    sys.exit(0)

def kill_processes_on_port(port):
    """Kill any processes using the specified port"""
    try:
        # Use lsof to find processes using the port
        result = subprocess.run(
            ['lsof', '-t', f'-i:{port}'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"🔍 Found {len(pids)} process(es) using port {port}")
            
            for pid in pids:
                if pid.strip():
                    try:
                        print(f"🛑 Killing process {pid}")
                        subprocess.run(['kill', '-TERM', pid.strip()], check=True)
                        # Give it a moment to terminate gracefully
                        time.sleep(0.5)
                        
                        # Check if still running, force kill if needed
                        check_result = subprocess.run(['kill', '-0', pid.strip()], 
                                                    capture_output=True)
                        if check_result.returncode == 0:
                            print(f"⚡ Force killing process {pid}")
                            subprocess.run(['kill', '-KILL', pid.strip()], check=True)
                            
                    except subprocess.CalledProcessError:
                        # Process might already be dead
                        pass
                        
            print(f"✅ Cleared port {port}")
            time.sleep(1)  # Give the port time to be released
            
        else:
            print(f"✅ Port {port} is already free")
            
    except FileNotFoundError:
        # lsof not available, try alternative method
        print("⚠️  lsof not found, trying alternative method...")
        try:
            # Try using netstat + grep approach
            result = subprocess.run(
                ['netstat', '-lnp'], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if f':{port}' in line and 'LISTEN' in line:
                        print(f"⚠️  Found process using port {port}, but couldn't kill automatically")
                        print(f"Please manually run: sudo lsof -ti:{port} | xargs kill -9")
                        return False
        except:
            pass
            
    except Exception as e:
        print(f"⚠️  Error while clearing port {port}: {e}")
        return False
    
    return True

def get_available_simulations(simulations_dir):
    """Get list of available simulation files"""
    json_files = []
    if simulations_dir.exists():
        json_files = [f.stem for f in simulations_dir.glob("*.json") if f.name != ".gitkeep"]
    return sorted(json_files)

def main():
    # Set up the workspace paths
    workspace_root = Path(__file__).parent
    simulations_dir = workspace_root / "simulations"
    server_dir = workspace_root / "server"
    
    # Get available simulations
    available_sims = get_available_simulations(simulations_dir)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Start TS2 simulation server and client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available simulations:
{chr(10).join(f"  • {sim}" for sim in available_sims)}

Examples:
  python run_simulation.py liverpool-st
  python run_simulation.py demo
  python run_simulation.py drain
        """
    )
    parser.add_argument(
        "simulation", 
        help="Name of the simulation to run (without .json extension)",
        nargs="?" if available_sims else None,
        choices=available_sims if available_sims else None
    )
    
    args = parser.parse_args()
    
    # If no simulation provided, list available ones
    if not args.simulation:
        if not available_sims:
            print("❌ No simulation files found in the simulations directory.")
            return 1
        
        print("🎮 Available simulations:")
        for sim in available_sims:
            print(f"  • {sim}")
        print(f"\nUsage: python {sys.argv[0]} [simulation_name]")
        return 1
    
    simulation_name = args.simulation
    simulation_file = simulations_dir / f"{simulation_name}.json"
    
    # Check if simulation file exists
    if not simulation_file.exists():
        print(f"❌ Simulation file not found: {simulation_file}")
        print(f"Available simulations: {', '.join(available_sims)}")
        return 1
    
    # Check if server directory exists
    if not server_dir.exists():
        print(f"❌ Server directory not found: {server_dir}")
        return 1
    
    # Check if go.mod exists in server directory
    if not (server_dir / "go.mod").exists():
        print(f"❌ Go module not found in server directory: {server_dir}")
        print("Make sure the Go server is properly set up.")
        return 1
    
    # Register cleanup handlers
    atexit.register(cleanup_processes)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"🚀 Starting TS2 simulation: {simulation_name}")
    print(f"📁 Simulation file: {simulation_file}")
    print(f"🖥️  Server directory: {server_dir}")
    
    try:
        # Clear any existing processes on port 22222
        print("\n🧹 Checking for existing processes on port 22222...")
        if not kill_processes_on_port("22222"):
            print("❌ Could not clear port 22222. Please manually stop any running servers.")
            return 1
        
        # Start the Go server
        print("\n🔧 Starting Go server...")
        global server_process
        server_process = subprocess.Popen(
            ["go", "run", ".", str(simulation_file)],
            cwd=server_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Give the server a moment to start
        print("⏳ Waiting for server to initialize...")
        time.sleep(3)
        
        # Check if server started successfully
        if server_process.poll() is not None:
            print("❌ Server failed to start. Server output:")
            stdout, stderr = server_process.communicate()
            if stdout:
                print(stdout)
            if stderr:
                print(stderr)
            return 1
        
        print("✅ Server started successfully")
        
        # Start the Python client with auto-connect script
        print("\n🎮 Starting Python client (auto-connecting to server)...")
        global client_process
        client_process = subprocess.Popen(
            [sys.executable, "start-ts2-connect.py"],
            cwd=workspace_root
        )
        
        print("✅ Client started successfully")
        print("\n🎉 Both server and client are running!")
        print("🔗 The client should automatically connect to the server")
        print("💡 Press Ctrl+C to stop both processes")
        
        # Wait for the client to finish
        client_process.wait()
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        return 1
    finally:
        cleanup_processes()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
