Add smart `setup` command for one-step project configuration

The new `kuzu-memory setup` command combines initialization and AI tool installation into a single intelligent command that:

- **Auto-detects** existing installations and updates them as needed
- **Initializes** memory database if not present
- **Detects** which AI tools are installed in your project
- **Installs/updates** integrations automatically
- **Verifies** everything is working correctly

This is now the **RECOMMENDED** way to get started with KuzuMemory. The existing `init` and `install` commands remain available for users who need granular control.

**Example usage:**
```bash
# Smart setup - auto-detects and configures everything (recommended)
kuzu-memory setup

# Preview changes without applying
kuzu-memory setup --dry-run

# Setup for specific integration
kuzu-memory setup --integration claude-code
```

This change simplifies the user experience while maintaining the "ONE PATH" principle - there's now one simple command for getting started, with advanced options still available when needed.
