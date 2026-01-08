"""
Quick Start Guide
Run this script to set up and start the API
"""
import subprocess
import sys
import os


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")


def check_env_file():
    """Check if .env file exists"""
    if not os.path.exists(".env"):
        print("❌ .env file not found!")
        print("📝 Creating .env from .env.example...")
        if os.path.exists(".env.example"):
            subprocess.run(["cp", ".env.example", ".env"])
            print("⚠️  Please edit .env with your credentials before continuing")
            sys.exit(1)
        else:
            print("❌ .env.example not found either!")
            sys.exit(1)
    print("✅ .env file found")


def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✅ Dependencies installed")


def create_logs_directory():
    """Create logs directory if it doesn't exist"""
    if not os.path.exists("logs"):
        os.makedirs("logs")
        print("✅ Logs directory created")
    else:
        print("✅ Logs directory exists")


def start_server():
    """Start the FastAPI server"""
    print("\n" + "=" * 60)
    print("🚀 Starting Weight Estimation API...")
    print("=" * 60)
    print("\n📍 API will be available at: http://localhost:8000")
    print("📚 API documentation: http://localhost:8000/docs")
    print("\n⌨️  Press CTRL+C to stop the server\n")
    
    subprocess.run([sys.executable, "main.py"])


if __name__ == "__main__":
    print("=" * 60)
    print("Weight Estimation API - Quick Start")
    print("=" * 60)
    print()
    
    check_python_version()
    check_env_file()
    create_logs_directory()
    
    # Ask user if they want to install dependencies
    response = input("\n📦 Install/update dependencies? (y/n): ").strip().lower()
    if response == 'y':
        install_dependencies()
    
    # Ask user if they want to start the server
    response = input("\n🚀 Start the server? (y/n): ").strip().lower()
    if response == 'y':
        start_server()
    else:
        print("\n✅ Setup complete! Run 'python main.py' to start the server.")
