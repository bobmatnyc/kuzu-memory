#!/usr/bin/env python3
"""
Safely remove all kuzu-memory MCP server entries from global Claude configuration.
"""
import json
from pathlib import Path
import sys

def main():
    # Read the config
    config_path = Path.home() / ".claude.json"

    print(f"Reading configuration from: {config_path}")

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in config file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read config: {e}")
        sys.exit(1)

    print(f"Configuration loaded successfully")
    print(f"Top-level keys: {list(config.keys())}")

    # Find and count kuzu-memory entries
    removed_count = 0
    removal_log = []

    # Check top-level mcpServers if exists
    if 'mcpServers' in config and isinstance(config['mcpServers'], dict):
        if 'kuzu-memory' in config['mcpServers']:
            del config['mcpServers']['kuzu-memory']
            removed_count += 1
            removal_log.append("Removed kuzu-memory from top-level mcpServers")
            print(f"✓ Removed kuzu-memory from top-level mcpServers")

    # Check projects for mcpServers (this is where they actually are)
    if 'projects' in config and isinstance(config['projects'], dict):
        for project_path, project_data in list(config['projects'].items()):
            if isinstance(project_data, dict):
                if 'mcpServers' in project_data and isinstance(project_data['mcpServers'], dict):
                    if 'kuzu-memory' in project_data['mcpServers']:
                        del project_data['mcpServers']['kuzu-memory']
                        removed_count += 1
                        # Show just the last part of the path for readability
                        project_name = Path(project_path).name if project_path else "unknown"
                        removal_log.append(f"Removed kuzu-memory from project: {project_name}")
                        print(f"✓ Removed kuzu-memory from project: {project_name} ({project_path})")

    # Check all other nested structures for mcpServers
    for key in list(config.keys()):
        if key == 'projects':  # Already handled above
            continue
        if isinstance(config[key], dict):
            if 'mcpServers' in config[key] and isinstance(config[key]['mcpServers'], dict):
                if 'kuzu-memory' in config[key]['mcpServers']:
                    del config[key]['mcpServers']['kuzu-memory']
                    removed_count += 1
                    removal_log.append(f"Removed kuzu-memory from {key}.mcpServers")
                    print(f"✓ Removed kuzu-memory from {key}.mcpServers")

    print(f"\n{'='*60}")
    print(f"Total kuzu-memory entries removed: {removed_count}")
    print(f"{'='*60}")

    if removed_count == 0:
        print("⚠ No kuzu-memory entries found to remove")
        sys.exit(0)

    # Write back with pretty formatting
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2, sort_keys=False)
        print(f"\n✅ Updated configuration written to {config_path}")
    except Exception as e:
        print(f"\n❌ ERROR: Failed to write config: {e}")
        print(f"⚠ Original config is backed up, no changes were saved")
        sys.exit(1)

    # Summary
    print(f"\nRemoval Summary:")
    for log_entry in removal_log:
        print(f"  - {log_entry}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
