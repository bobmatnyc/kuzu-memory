#!/usr/bin/env python3
"""
KuzuMemory 3-Minute Installation Script

This script provides a complete installation and setup experience
that gets users productive with KuzuMemory in under 3 minutes.

Now with Claude Code MCP integration support!
"""

import subprocess
import sys
import time
import json
import os
import platform
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

def detect_claude_installation():
    """Detect Claude Code or Claude Desktop installation."""
    system = platform.system()
    claude_configs = []

    if system == "Darwin":  # macOS
        claude_configs = [
            Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        ]
    elif system == "Linux":
        claude_configs = [
            Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
        ]
    elif system == "Windows":
        app_data = os.environ.get("APPDATA", "")
        if app_data:
            claude_configs = [
                Path(app_data) / "Claude" / "claude_desktop_config.json"
            ]

    for config_path in claude_configs:
        if config_path.exists():
            return config_path

    return None

def setup_claude_code_integration():
    """Setup MCP integration for Claude Code."""
    print("🤖 Setting up Claude Code integration...")

    claude_config_path = detect_claude_installation()

    if not claude_config_path:
        print("⚠️  Claude Code/Desktop not detected, skipping MCP setup")
        return True

    print(f"✅ Found Claude configuration at: {claude_config_path}")

    # Create MCP server configuration
    config_dir = Path.home() / ".config" / "kuzu-memory"
    config_dir.mkdir(parents=True, exist_ok=True)

    mcp_config = {
        "mcpServers": {
            "kuzu-memory": {
                "command": str(Path.home() / ".local" / "bin" / "kuzu-memory-mcp"),
                "args": [],
                "env": {
                    "KUZU_MEMORY_HOME": str(Path.home() / ".local" / "kuzu-memory")
                }
            }
        }
    }

    mcp_config_path = config_dir / "mcp_server_config.json"
    with open(mcp_config_path, 'w') as f:
        json.dump(mcp_config, f, indent=2)

    print(f"✅ MCP configuration saved to: {mcp_config_path}")

    # Try to merge with existing Claude config
    try:
        # Backup existing config
        backup_path = claude_config_path.with_suffix(f'.backup-{int(time.time())}.json')
        if claude_config_path.exists():
            import shutil
            shutil.copy2(claude_config_path, backup_path)
            print(f"✅ Backed up existing config to: {backup_path}")

            # Load existing config
            with open(claude_config_path, 'r') as f:
                existing_config = json.load(f)

            # Merge configurations
            if 'mcpServers' not in existing_config:
                existing_config['mcpServers'] = {}

            existing_config['mcpServers']['kuzu-memory'] = mcp_config['mcpServers']['kuzu-memory']

            # Write merged config
            with open(claude_config_path, 'w') as f:
                json.dump(existing_config, f, indent=2)

            print("✅ Claude Code configuration updated with MCP server")
        else:
            # Create new config
            with open(claude_config_path, 'w') as f:
                json.dump(mcp_config, f, indent=2)
            print("✅ Created new Claude Code configuration")

        print("⚠️  Please restart Claude Code to load the new MCP server")
        return True

    except Exception as e:
        print(f"❌ Failed to update Claude configuration: {e}")
        print(f"   Please manually add the MCP configuration from: {mcp_config_path}")
        return False

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

        # Test MCP server
        try:
            from kuzu_memory.mcp import MCPServer
            print("✅ MCP server available for Claude Code")
        except ImportError:
            print("⚠️  MCP server not available (optional)")

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

    # Step 5: Setup Claude Code integration if available
    setup_claude_code_integration()

    # Step 6: Run demo
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
