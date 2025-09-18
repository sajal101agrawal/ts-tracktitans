#!/usr/bin/env python3
"""
TS2 TrackTitans Environment Setup Script

This script automatically sets up your development environment by:
1. Checking Python and Go installations
2. Installing required Python packages
3. Setting up Go server dependencies
4. Building the server for optimal performance

Usage: python setup_environment.py
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
import shutil

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'  # End formatting

def print_header(message):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN} {message} {Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")

def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message):
    """Print error message"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_warning(message):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_info(message):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_step(step_num, total_steps, message):
    """Print step progress"""
    print(f"{Colors.BOLD}{Colors.MAGENTA}[{step_num}/{total_steps}] {message}{Colors.END}")

def run_command(command, cwd=None, check=True, capture_output=False):
    """Run a command and handle errors gracefully"""
    try:
        if isinstance(command, str):
            command = command.split()
        
        print_info(f"Running: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            cwd=cwd,
            check=check,
            capture_output=capture_output,
            text=True
        )
        
        if capture_output:
            return result
        return True
        
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {' '.join(command)}")
        if capture_output and e.stdout:
            print(f"STDOUT: {e.stdout}")
        if capture_output and e.stderr:
            print(f"STDERR: {e.stderr}")
        return False
    except FileNotFoundError:
        print_error(f"Command not found: {command[0]}")
        return False

def check_python_version():
    """Check if Python version meets requirements"""
    print_step(1, 6, "Checking Python version...")
    
    if sys.version_info < (3, 6):
        print_error(f"Python 3.6+ required. Current version: {sys.version}")
        return False
    
    print_success(f"Python {sys.version.split()[0]} is installed and compatible")
    return True

def check_go_installation():
    """Check if Go is installed and get version"""
    print_step(2, 6, "Checking Go installation...")
    
    result = run_command("go version", capture_output=True, check=False)
    if not result or result.returncode != 0:
        print_error("Go is not installed or not in PATH")
        print_info("Please install Go from: https://golang.org/dl/")
        return False
    
    version_output = result.stdout.strip()
    print_success(f"{version_output}")
    
    # Check if Go version is recent enough (1.13+)
    try:
        version_parts = version_output.split()
        version_str = version_parts[2].replace('go', '').split('.')
        major, minor = int(version_str[0]), int(version_str[1])
        
        if major > 1 or (major == 1 and minor >= 13):
            print_success("Go version meets requirements (1.13+)")
            return True
        else:
            print_warning(f"Go version {version_str[0]}.{version_str[1]} detected. Version 1.13+ recommended.")
            return True  # Still proceed but with warning
    except:
        print_warning("Could not parse Go version, but Go is installed")
        return True

def get_pip_command():
    """Get the correct pip command for this system"""
    # Try different pip commands to find the right one
    pip_commands = ['pip3', 'pip']
    
    for pip_cmd in pip_commands:
        result = run_command(f"{pip_cmd} --version", capture_output=True, check=False)
        if result and result.returncode == 0:
            # Check if this pip is associated with the current Python
            if sys.executable in result.stdout or 'python3' in result.stdout.lower():
                return pip_cmd
    
    # Fallback to python -m pip
    return f"{sys.executable} -m pip"

def install_python_dependencies():
    """Install required Python packages"""
    print_step(3, 6, "Installing Python dependencies...")
    
    # Required packages for TS2
    required_packages = [
        'PyQt5>=5.12.0',  # GUI framework (NOT PyQt6!)
        'websocket-client>=1.0.0',  # WebSocket support
        'simplejson>=3.2.0',  # JSON handling
        'requests>=2.20.0',  # HTTP requests
    ]
    
    pip_cmd = get_pip_command()
    print_info(f"Using pip command: {pip_cmd}")
    
    # First upgrade pip itself
    print_info("Upgrading pip...")
    run_command(f"{pip_cmd} install --upgrade pip", check=False)
    
    # Install each package
    for package in required_packages:
        print_info(f"Installing {package}...")
        if not run_command(f"{pip_cmd} install {package}", check=False):
            print_error(f"Failed to install {package}")
            return False
    
    print_success("All Python dependencies installed successfully!")
    return True

def verify_python_imports():
    """Verify that all required Python modules can be imported"""
    print_step(4, 6, "Verifying Python imports...")
    
    test_imports = [
        ('PyQt5', 'PyQt5.QtWidgets'),
        ('websocket', 'websocket'),
        ('simplejson', 'simplejson'),
        ('requests', 'requests'),
    ]
    
    all_good = True
    for display_name, import_name in test_imports:
        try:
            __import__(import_name)
            print_success(f"{display_name} import successful")
        except ImportError as e:
            print_error(f"{display_name} import failed: {e}")
            all_good = False
    
    if all_good:
        print_success("All Python dependencies verified!")
    else:
        print_error("Some Python dependencies are missing or broken")
    
    return all_good

def setup_go_server():
    """Set up Go server dependencies and build"""
    print_step(5, 6, "Setting up Go server...")
    
    workspace_root = Path(__file__).parent
    server_dir = workspace_root / "server"
    
    if not server_dir.exists():
        print_error(f"Server directory not found: {server_dir}")
        return False
    
    if not (server_dir / "go.mod").exists():
        print_error(f"go.mod not found in {server_dir}")
        return False
    
    # Download dependencies
    print_info("Downloading Go dependencies...")
    if not run_command("go mod download", cwd=server_dir):
        print_error("Failed to download Go dependencies")
        return False
    
    # Tidy up dependencies
    print_info("Tidying Go modules...")
    if not run_command("go mod tidy", cwd=server_dir):
        print_error("Failed to tidy Go modules")
        return False
    
    # Build the server
    print_info("Building Go server...")
    if not run_command("go build -o ts2-sim-server main.go", cwd=server_dir):
        print_error("Failed to build Go server")
        return False
    
    print_success("Go server setup completed successfully!")
    return True

def create_quick_start_script():
    """Create a quick start script for easy launching"""
    print_step(6, 6, "Creating quick start helpers...")
    
    workspace_root = Path(__file__).parent
    
    # Determine the correct Python command
    python_cmd = "python" if platform.system() == "Windows" else "python3"
    
    # Create Windows batch file
    if platform.system() == "Windows":
        batch_content = f'''@echo off
echo Starting TS2 TrackTitans Simulation...
echo Available simulations: demo, drain, liverpool-st, gretz-armainvilliers
echo.
if "%1"=="" (
    echo Usage: start_simulation.bat [simulation_name]
    echo Example: start_simulation.bat liverpool-st
    {python_cmd} run_simulation.py
) else (
    {python_cmd} run_simulation.py %1
)
pause
'''
        with open(workspace_root / "start_simulation.bat", "w") as f:
            f.write(batch_content)
        print_success("Created start_simulation.bat for Windows")
    
    # Create shell script for Mac/Linux
    else:
        shell_content = f'''#!/bin/bash
echo "Starting TS2 TrackTitans Simulation..."
echo "Available simulations: demo, drain, liverpool-st, gretz-armainvilliers"
echo

if [ -z "$1" ]; then
    echo "Usage: ./start_simulation.sh [simulation_name]"
    echo "Example: ./start_simulation.sh liverpool-st"
    {python_cmd} run_simulation.py
else
    {python_cmd} run_simulation.py "$1"
fi
'''
        script_path = workspace_root / "start_simulation.sh"
        with open(script_path, "w") as f:
            f.write(shell_content)
        
        # Make it executable
        os.chmod(script_path, 0o755)
        print_success("Created start_simulation.sh for Mac/Linux")

def print_final_instructions():
    """Print final setup instructions"""
    system = platform.system()
    python_cmd = "python" if system == "Windows" else "python3"
    
    print_header("🎉 Setup Complete!")
    
    print(f"{Colors.BOLD}Your TS2 TrackTitans environment is now ready!{Colors.END}\n")
    
    print(f"{Colors.BOLD}Quick Start:{Colors.END}")
    if system == "Windows":
        print(f"  • Double-click {Colors.CYAN}start_simulation.bat{Colors.END}")
        print(f"  • Or run: {Colors.CYAN}{python_cmd} run_simulation.py liverpool-st{Colors.END}")
    else:
        print(f"  • Run: {Colors.CYAN}./start_simulation.sh liverpool-st{Colors.END}")
        print(f"  • Or run: {Colors.CYAN}{python_cmd} run_simulation.py liverpool-st{Colors.END}")
    
    print(f"\n{Colors.BOLD}Available Simulations:{Colors.END}")
    print(f"  • {Colors.GREEN}demo{Colors.END} - Simple demonstration")
    print(f"  • {Colors.GREEN}drain{Colors.END} - Drainage system")
    print(f"  • {Colors.GREEN}liverpool-st{Colors.END} - Liverpool Street (recommended)")
    print(f"  • {Colors.GREEN}gretz-armainvilliers{Colors.END} - French railway")
    
    print(f"\n{Colors.BOLD}What was installed:{Colors.END}")
    print(f"  ✅ PyQt5 - GUI framework")
    print(f"  ✅ websocket-client - WebSocket support")
    print(f"  ✅ simplejson - JSON handling")
    print(f"  ✅ requests - HTTP requests")
    print(f"  ✅ Go server dependencies")
    print(f"  ✅ Compiled server binary")
    
    print(f"\n{Colors.BOLD}Need help?{Colors.END}")
    print(f"  • Check {Colors.CYAN}SETUP_README.md{Colors.END} for detailed instructions")
    print(f"  • Run with no arguments to see available simulations")
    print(f"  • Press Ctrl+C to stop the simulation")
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}Happy dispatching! 🚂✨{Colors.END}")

def main():
    """Main setup function"""
    print_header("🚂 TS2 TrackTitans Environment Setup")
    print("This script will set up your complete development environment.\n")
    
    # Check if we're in the right directory
    if not Path("run_simulation.py").exists():
        print_error("Please run this script from the ts-tracktitans project root directory")
        return 1
    
    # Step-by-step setup
    steps = [
        ("Check Python version", check_python_version),
        ("Check Go installation", check_go_installation),
        ("Install Python dependencies", install_python_dependencies),
        ("Verify Python imports", verify_python_imports),
        ("Set up Go server", setup_go_server),
        ("Create quick start helpers", create_quick_start_script)
    ]
    
    failed_steps = []
    
    for step_name, step_function in steps:
        try:
            if not step_function():
                failed_steps.append(step_name)
        except Exception as e:
            print_error(f"Unexpected error in {step_name}: {e}")
            failed_steps.append(step_name)
    
    # Summary
    if failed_steps:
        print_header("⚠️  Setup Completed with Issues")
        print_error(f"The following steps failed: {', '.join(failed_steps)}")
        print_info("Please check the error messages above and resolve the issues.")
        print_info("You may need to:")
        print("  • Install missing software (Go, Python)")
        print("  • Fix PATH environment variables")
        print("  • Install packages manually")
        return 1
    else:
        print_final_instructions()
        return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_error("\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
