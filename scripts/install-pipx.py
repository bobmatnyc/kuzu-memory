#!/usr/bin/env python3
"""
KuzuMemory pipx Installation Script

This script installs KuzuMemory via pipx for isolated CLI usage.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description, check=True, capture_output=True):
    """Run a command with status output."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            check=check, 
            capture_output=capture_output, 
            text=True
        )
        if result.returncode == 0:
            print(f"✅ {description} completed")
            return True, result.stdout if capture_output else ""
        else:
            error_msg = result.stderr if capture_output else "Command failed"
            print(f"❌ {description} failed: {error_msg}")
            return False, error_msg
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False, str(e)

def check_python_version():
    """Check if Python version is compatible."""
    print("🔍 Checking Python version...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print(f"❌ Python {version.major}.{version.minor} is not supported")
        print("   KuzuMemory requires Python 3.11 or higher")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def check_pipx():
    """Check if pipx is installed."""
    print("🔍 Checking for pipx...")
    
    success, output = run_command("pipx --version", "Checking pipx version", check=False)
    if success:
        print(f"✅ pipx is available: {output.strip()}")
        return True
    else:
        print("❌ pipx not found")
        return False

def install_pipx():
    """Install pipx if not available."""
    print("📦 Installing pipx...")
    
    # Try different installation methods
    install_methods = [
        ("pip install --user pipx", "Installing pipx via pip"),
        ("python -m pip install --user pipx", "Installing pipx via python -m pip"),
    ]
    
    for cmd, desc in install_methods:
        success, output = run_command(cmd, desc, check=False)
        if success:
            # Ensure pipx is in PATH
            success, _ = run_command("python -m pipx ensurepath", "Adding pipx to PATH", check=False)
            return True
    
    print("❌ Failed to install pipx")
    print("💡 Please install pipx manually:")
    print("   - macOS: brew install pipx")
    print("   - Linux: python -m pip install --user pipx")
    print("   - Windows: python -m pip install --user pipx")
    return False

def uninstall_existing():
    """Uninstall existing KuzuMemory installation."""
    print("🗑️  Checking for existing installation...")
    
    success, output = run_command("pipx list", "Checking pipx installations", check=False)
    if success and "kuzu-memory" in output:
        print("🔄 Uninstalling existing KuzuMemory...")
        success, _ = run_command("pipx uninstall kuzu-memory", "Uninstalling existing version", check=False)
        if success:
            print("✅ Existing installation removed")
        else:
            print("⚠️  Could not remove existing installation")
    else:
        print("✅ No existing installation found")

def install_kuzu_memory(source="pypi"):
    """Install KuzuMemory via pipx."""
    if source == "pypi":
        print("📦 Installing KuzuMemory from PyPI...")
        cmd = "pipx install kuzu-memory"
        desc = "Installing KuzuMemory from PyPI"
    elif source == "test-pypi":
        print("🧪 Installing KuzuMemory from Test PyPI...")
        cmd = "pipx install --index-url https://test.pypi.org/simple/ kuzu-memory"
        desc = "Installing KuzuMemory from Test PyPI"
    else:  # local
        print("🔧 Installing KuzuMemory from local source...")
        project_root = Path(__file__).parent.parent
        cmd = f"pipx install {project_root}"
        desc = "Installing KuzuMemory from local source"
    
    success, output = run_command(cmd, desc, check=False)
    return success, output

def test_installation():
    """Test the KuzuMemory installation."""
    print("🧪 Testing installation...")
    
    # Test basic command
    success, output = run_command("kuzu-memory --version", "Testing version command", check=False)
    if not success:
        return False
    
    print(f"✅ Version: {output.strip()}")
    
    # Test help command
    success, output = run_command("kuzu-memory --help", "Testing help command", check=False)
    if not success:
        return False
    
    print("✅ Help command working")
    
    # Test demo command
    print("🎮 Testing demo command...")
    success, output = run_command("kuzu-memory demo", "Running demo", check=False, capture_output=False)
    if success:
        print("✅ Demo command working")
    else:
        print("⚠️  Demo command had issues (may be normal)")
    
    return True

def show_usage_info():
    """Show usage information."""
    usage_info = """
🎉 KuzuMemory Installation Complete!

📋 Available Commands:
  kuzu-memory --help           # Show all commands
  kuzu-memory demo             # Try instant demo
  kuzu-memory quickstart       # 3-minute setup
  kuzu-memory examples         # See examples
  
🚀 Quick Start:
  kuzu-memory demo
  kuzu-memory remember "I love Python" --user-id you
  kuzu-memory recall "What do I like?" --user-id you

🔧 Configuration:
  kuzu-memory setup            # Interactive setup
  kuzu-memory optimize         # Performance tuning

📚 Help:
  kuzu-memory COMMAND --help   # Detailed help for any command
  kuzu-memory examples TOPIC   # Examples for specific topics

🆘 Troubleshooting:
  pipx list                    # Show installed packages
  pipx reinstall kuzu-memory   # Reinstall if issues
  pipx uninstall kuzu-memory   # Remove installation
"""
    print(usage_info)

def main():
    """Main installation workflow."""
    print("📦 KuzuMemory pipx Installation")
    print("=" * 50)
    
    # Parse command line arguments
    source = "pypi"  # default
    if "--test-pypi" in sys.argv:
        source = "test-pypi"
    elif "--local" in sys.argv:
        source = "local"
    
    force_reinstall = "--force" in sys.argv
    
    try:
        # Step 1: Check Python version
        if not check_python_version():
            sys.exit(1)
        
        # Step 2: Check/install pipx
        if not check_pipx():
            if not install_pipx():
                sys.exit(1)
            
            # Verify pipx is now available
            if not check_pipx():
                print("❌ pipx installation failed")
                sys.exit(1)
        
        # Step 3: Uninstall existing (if force or if exists)
        if force_reinstall:
            uninstall_existing()
        
        # Step 4: Install KuzuMemory
        success, output = install_kuzu_memory(source)
        if not success:
            print(f"❌ Installation failed: {output}")
            
            if "already installed" in output.lower():
                print("💡 KuzuMemory is already installed")
                print("   Use --force to reinstall")
                
                # Test existing installation
                if test_installation():
                    show_usage_info()
                    sys.exit(0)
            
            sys.exit(1)
        
        # Step 5: Test installation
        if not test_installation():
            print("❌ Installation test failed")
            print("💡 Try: pipx reinstall kuzu-memory")
            sys.exit(1)
        
        # Step 6: Show usage info
        show_usage_info()
        
        print("🎉 Installation successful!")
        
    except KeyboardInterrupt:
        print("\n❌ Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
