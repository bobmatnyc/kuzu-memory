#!/usr/bin/env python3
"""
KuzuMemory 3-Minute Installation Script

This script provides a complete installation and setup experience
that gets users productive with KuzuMemory in under 3 minutes.
"""

import subprocess
import sys
import time
from pathlib import Path

def print_banner():
    """Print the installation banner."""
    banner = """
╭─────────────────────────────────────────────────────────────────╮
│  🧠 KuzuMemory - 3-Minute Installation                          │
│                                                                 │
│  Intelligent Memory System for AI Applications                  │
│  • No LLM calls required • Graph-based storage                  │
│  • AI-powered enhancements • Zero configuration needed          │
╰─────────────────────────────────────────────────────────────────╯
"""
    print(banner)

def run_command(cmd, description, show_output=False):
    """Run a command with progress indication."""
    print(f"⏳ {description}...")
    
    try:
        if show_output:
            result = subprocess.run(cmd, shell=True, check=True)
        else:
            result = subprocess.run(
                cmd, 
                shell=True, 
                check=True, 
                capture_output=True, 
                text=True
            )
        print(f"✅ {description} completed")
        return True, result.stdout if hasattr(result, 'stdout') else ""
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False, str(e)

def check_python_version():
    """Check if Python version is compatible."""
    print("🔍 Checking Python version...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} is not supported")
        print("   KuzuMemory requires Python 3.8 or higher")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def install_dependencies():
    """Install required dependencies."""
    dependencies = [
        "kuzu>=0.4.0",
        "pydantic>=2.0", 
        "click>=8.1.0",
        "pyyaml>=6.0",
        "python-dateutil>=2.8",
        "typing-extensions>=4.5",
        "rich>=13.0.0"
    ]
    
    print("📦 Installing dependencies...")
    
    for dep in dependencies:
        success, output = run_command(f"pip install {dep}", f"Installing {dep.split('>=')[0]}")
        if not success:
            return False
    
    return True

def install_kuzu_memory():
    """Install KuzuMemory in development mode."""
    print("🧠 Installing KuzuMemory...")
    
    # Check if we're in the KuzuMemory directory
    if Path("setup.py").exists() or Path("pyproject.toml").exists():
        success, _ = run_command("pip install -e .", "Installing KuzuMemory (development mode)")
    else:
        print("⚠️  Not in KuzuMemory directory, installing from PyPI...")
        success, _ = run_command("pip install kuzu-memory", "Installing KuzuMemory from PyPI")
    
    return success

def test_installation():
    """Test the installation."""
    print("🧪 Testing installation...")
    
    try:
        # Test basic import
        import kuzu_memory
        print("✅ KuzuMemory imports successfully")
        
        # Test CLI
        from kuzu_memory.cli.commands import cli
        print("✅ CLI available")
        
        # Test core functionality
        from kuzu_memory.core.memory import KuzuMemory
        from kuzu_memory.core.config import KuzuMemoryConfig
        print("✅ Core components available")
        
        # Test Auggie integration
        try:
            from kuzu_memory.integrations.auggie import AuggieIntegration
            print("✅ Auggie AI integration available")
        except ImportError:
            print("⚠️  Auggie integration not available (optional)")
        
        return True
        
    except ImportError as e:
        print(f"❌ Installation test failed: {e}")
        return False

def run_demo():
    """Run the interactive demo."""
    print("🎮 Running demo...")
    
    try:
        from kuzu_memory.cli.commands import cli
        cli(['demo'])
        return True
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False

def show_next_steps():
    """Show next steps to the user."""
    next_steps = """
🎉 Installation Complete!

🚀 QUICK START:
  kuzu-memory quickstart     # Interactive 3-minute setup
  kuzu-memory demo           # Try it instantly (just ran!)

📚 LEARN MORE:
  kuzu-memory examples       # See all examples
  kuzu-memory --help         # Full command reference

💡 FIRST STEPS:
  1. kuzu-memory remember "I'm [your name], a [your role]"
  2. kuzu-memory recall "What do you know about me?"
  3. kuzu-memory auggie enhance "How do I code?" --user-id you

🔧 CONFIGURATION:
  kuzu-memory setup          # Interactive configuration
  kuzu-memory tips           # Best practices

📊 MONITORING:
  kuzu-memory stats          # Memory statistics
  kuzu-memory auggie stats   # AI integration stats

🆘 HELP:
  Every command has detailed help: kuzu-memory COMMAND --help
  Rich examples available: kuzu-memory examples TOPIC

Ready to build intelligent AI applications! 🧠✨
"""
    
    print(next_steps)

def main():
    """Main installation process."""
    start_time = time.time()
    
    print_banner()
    print("Starting 3-minute installation process...\n")
    
    # Step 1: Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Step 2: Install dependencies
    if not install_dependencies():
        print("❌ Dependency installation failed")
        sys.exit(1)
    
    # Step 3: Install KuzuMemory
    if not install_kuzu_memory():
        print("❌ KuzuMemory installation failed")
        sys.exit(1)
    
    # Step 4: Test installation
    if not test_installation():
        print("❌ Installation test failed")
        sys.exit(1)
    
    # Step 5: Run demo
    print("\n" + "="*60)
    print("🎮 RUNNING DEMO")
    print("="*60)
    
    if not run_demo():
        print("⚠️  Demo failed, but installation is complete")
    
    # Calculate installation time
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    
    print("\n" + "="*60)
    print("🎉 INSTALLATION COMPLETE!")
    print("="*60)
    print(f"⏱️  Total time: {minutes}m {seconds}s")
    
    if elapsed_time <= 180:  # 3 minutes
        print("🎯 3-minute installation goal achieved!")
    else:
        print("⏰ Installation took longer than 3 minutes, but it's complete!")
    
    show_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Installation failed with unexpected error: {e}")
        sys.exit(1)
