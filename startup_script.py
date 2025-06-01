#!/usr/bin/env python3
"""
Enhanced Payment Plan Analysis System - Startup Script
Phase 2: FastAPI Web Application

This script helps you get started quickly with the payment plan analysis system.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header():
    """Print welcome header"""
    print("=" * 60)
    print("🚀 Enhanced Payment Plan Analysis System")
    print("📊 Phase 2: FastAPI Web Application")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        print("   Please upgrade Python and try again.")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True

def check_virtual_environment():
    """Check if virtual environment exists and create if needed"""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print("📦 Creating virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("✅ Virtual environment created successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to create virtual environment")
            return False
    else:
        print("✅ Virtual environment already exists")
    
    return True

def get_activation_command():
    """Get the appropriate activation command for the platform"""
    if platform.system() == "Windows":
        return "venv\\Scripts\\activate"
    else:
        return "source venv/bin/activate"

def install_dependencies():
    """Install required dependencies"""
    print("📥 Installing dependencies...")
    
    # Determine pip executable
    if platform.system() == "Windows":
        pip_exe = "venv\\Scripts\\pip"
    else:
        pip_exe = "venv/bin/pip"
    
    try:
        subprocess.run([pip_exe, "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        print("   Try running manually:")
        print(f"   {get_activation_command()}")
        print("   pip install -r requirements.txt")
        return False
    except FileNotFoundError:
        print("❌ Virtual environment not properly set up")
        return False

def create_directories():
    """Create necessary directories"""
    dirs = ["uploads", "reports", "static", "templates", "logs"]
    
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"📁 Created directory: {dir_name}")
    
    print("✅ All directories ready")

def check_required_files():
    """Check if all required files exist"""
    required_files = [
        "fastapi_webapp.py",
        "enhanced_main.py",
        "enhanced_parsers.py",
        "enhanced_analyzers.py",
        "enhanced_calculators.py",
        "enhanced_reporters.py",
        "models.py",
        "requirements.txt"
    ]
    
    missing_files = []
    for file_name in required_files:
        if not Path(file_name).exists():
            missing_files.append(file_name)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_name in missing_files:
            print(f"   - {file_name}")
        return False
    
    print("✅ All required files present")
    return True

def start_application():
    """Start the FastAPI application"""
    print("\n🌐 Starting Payment Plan Analysis System...")
    print("📍 The application will be available at: http://localhost:8000")
    print("⏹️  Press Ctrl+C to stop the server")
    print()
    
    # Determine python executable
    if platform.system() == "Windows":
        python_exe = "venv\\Scripts\\python"
    else:
        python_exe = "venv/bin/python"
    
    try:
        # Try to start with uvicorn first (preferred)
        if platform.system() == "Windows":
            uvicorn_exe = "venv\\Scripts\\uvicorn"
        else:
            uvicorn_exe = "venv/bin/uvicorn"
        
        if Path(uvicorn_exe).exists() or Path(uvicorn_exe + ".exe").exists():
            cmd = [uvicorn_exe, "fastapi_webapp:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
        else:
            cmd = [python_exe, "fastapi_webapp.py"]
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except FileNotFoundError:
        print("❌ Failed to start server")
        print("   Try running manually:")
        print(f"   {get_activation_command()}")
        print("   python fastapi_webapp.py")

def show_usage_instructions():
    """Show usage instructions"""
    print("\n📖 Quick Start Guide:")
    print("1. Open your browser and go to: http://localhost:8000")
    print("2. Upload your payment plan CSV file")
    print("3. Review the analysis results")
    print("4. Download reports as needed")
    print()
    print("📁 File Requirements:")
    print("- CSV format with customer names, invoice data")
    print("- Required columns: Type, Date, Num, FOB, Open Balance, Amount")
    print("- Optional: Class column for filtering")
    print()

def main():
    """Main startup function"""
    print_header()
    
    # Check prerequisites
    if not check_python_version():
        sys.exit(1)
    
    if not check_required_files():
        print("\n❌ Setup incomplete. Please ensure all files are present.")
        sys.exit(1)
    
    # Setup environment
    if not check_virtual_environment():
        sys.exit(1)
    
    if not install_dependencies():
        sys.exit(1)
    
    create_directories()
    
    # Show instructions
    show_usage_instructions()
    
    # Start application
    try:
        start_application()
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Ensure all dependencies are installed")
        print("2. Check that port 8000 is not in use")
        print("3. Verify file permissions")
        print("4. Try running manually:")
        print(f"   {get_activation_command()}")
        print("   python fastapi_webapp.py")

if __name__ == "__main__":
    main()