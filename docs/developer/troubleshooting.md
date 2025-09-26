# Troubleshooting Guide

**Comprehensive troubleshooting guide for KuzuMemory issues and solutions**

---

## 🎯 **Quick Diagnostics**

### **Health Check Commands**
```bash
# Basic system check
kuzu-memory --version
kuzu-memory stats --detailed
kuzu-memory project --verbose

# Debug mode for detailed information
kuzu-memory --debug stats
kuzu-memory --debug enhance "test query"

# Performance check
time kuzu-memory enhance "performance test"
kuzu-memory recent --limit 1 --format json
```

### **Common Error Patterns**
| Error Pattern | Likely Cause | Quick Fix |
|---------------|--------------|-----------|
| `Command not found` | Installation issue | `pip install kuzu-memory` |
| `Database not initialized` | Missing init | `kuzu-memory init` |
| `Permission denied` | File permissions | `chmod -R 755 kuzu-memories/` |
| `Timeout expired` | Performance issue | Check system resources |
| `JSON decode error` | Corrupted output | Clear cache, restart |

---

## 🚨 **Installation Issues**

### **Problem: Command Not Found**
```bash
# Symptom
kuzu-memory --version
# bash: kuzu-memory: command not found

# Diagnosis
which python
pip list | grep kuzu-memory

# Solutions
# Option 1: Install/reinstall
pip install kuzu-memory

# Option 2: Check PATH
pip show kuzu-memory | grep Location
export PATH="$PATH:$HOME/.local/bin"

# Option 3: Use pipx (recommended)
pipx install kuzu-memory

# Option 4: Direct execution
python -m kuzu_memory.cli.commands --version
```

### **Problem: Import Errors**
```bash
# Symptom
ImportError: No module named 'kuzu'
ModuleNotFoundError: No module named 'kuzu_memory'

# Diagnosis
python -c "import kuzu; print(kuzu.__version__)"
python -c "import kuzu_memory; print(kuzu_memory.__version__)"

# Solutions
# Install missing dependencies
pip install kuzu>=0.4.0
pip install -U kuzu-memory

# Check Python version
python --version  # Should be 3.11+

# Virtual environment issues
deactivate && source venv/bin/activate
pip install -e .
```

### **Problem: Version Conflicts**
```bash
# Symptom
ERROR: kuzu-memory has requirement kuzu>=0.4.0, but you have kuzu 0.3.0

# Diagnosis
pip list | grep kuzu
pip check

# Solutions
# Upgrade conflicting packages
pip install --upgrade kuzu kuzu-memory

# Clean installation
pip uninstall kuzu-memory kuzu
pip install kuzu-memory

# Use constraints file
pip install -r requirements.txt --constraint constraints.txt
```

---

## 💾 **Database Issues**

### **Problem: Database Not Initialized**
```bash
# Symptom
ERROR: KuzuMemory not initialized. Run 'kuzu-memory init' first.

# Diagnosis
ls -la kuzu-memories/
kuzu-memory project

# Solutions
# Initialize in current directory
kuzu-memory init

# Force reinitialize
kuzu-memory init --force

# Custom path
kuzu-memory init --db-path ./custom-memories

# Check permissions
ls -la kuzu-memories/
chmod -R 755 kuzu-memories/
```

### **Problem: Database Corruption**
```bash
# Symptom
ERROR: database disk image is malformed
ERROR: no such table: memories

# Diagnosis
file kuzu-memories/kuzu.db
sqlite3 kuzu-memories/kuzu.db ".schema"

# Solutions
# Backup and reinitialize
cp -r kuzu-memories/ kuzu-memories-backup/
rm -rf kuzu-memories/
kuzu-memory init

# Recover from backup (if available)
kuzu-memory import kuzu-memories-backup/export.json

# Check disk space
df -h .
```

### **Problem: Database Locked**
```bash
# Symptom
ERROR: database is locked
ERROR: Could not acquire database lock

# Diagnosis
lsof kuzu-memories/kuzu.db
ps aux | grep kuzu-memory

# Solutions
# Kill competing processes
pkill -f kuzu-memory

# Remove lock files
rm -f kuzu-memories/*.lock
rm -f kuzu-memories/*-wal kuzu-memories/*-shm

# Check file permissions
ls -la kuzu-memories/
chown -R $USER:$USER kuzu-memories/
```

---

## ⚡ **Performance Issues**

### **Problem: Slow Query Performance**
```bash
# Symptom
kuzu-memory enhance "test" taking >5 seconds
Query timeout errors

# Diagnosis
kuzu-memory stats --detailed
time kuzu-memory enhance "performance test"
top -p $(pgrep kuzu-memory)

# Solutions
# Enable CLI adapter for better performance
kuzu-memory optimize --enable-cli

# Clear cache
rm -rf ~/.cache/kuzu-memory/

# Reduce database size
kuzu-memory cleanup --older-than 30d

# Check system resources
free -h
iostat -x 1 5

# Optimize database
kuzu-memory optimize --compact-db
```

### **Problem: High Memory Usage**
```bash
# Symptom
Out of memory errors
System becoming unresponsive

# Diagnosis
ps aux | grep kuzu-memory | awk '{print $4, $6}'
kuzu-memory stats --format json | jq '.database_size_mb'

# Solutions
# Check database size
du -sh kuzu-memories/

# Clean old memories
kuzu-memory cleanup --force

# Reduce cache size
echo '{"performance": {"cache_size": 100}}' > kuzu-config.json
kuzu-memory --config kuzu-config.json stats

# Monitor memory usage
watch -n 1 'ps aux | grep kuzu-memory'
```

### **Problem: Timeout Errors**
```bash
# Symptom
ERROR: Operation timed out after 5000ms
subprocess.TimeoutExpired

# Diagnosis
kuzu-memory --debug enhance "test query"
strace -t kuzu-memory enhance "test" 2>&1 | grep -E "(read|write|open)"

# Solutions
# Increase timeout in client code
subprocess.run(['kuzu-memory', 'enhance', 'test'], timeout=10)

# Optimize query
kuzu-memory enhance "more specific query" --limit 3

# Check system load
uptime
iostat 1 5

# Use async operations
kuzu-memory learn "content" --quiet  # Fire and forget
```

---

## 🔧 **Configuration Issues**

### **Problem: Configuration Not Found**
```bash
# Symptom
WARNING: Configuration file not found, using defaults
ERROR: Invalid configuration

# Diagnosis
kuzu-memory --config /path/to/config.json stats
find . -name "kuzu-config.json" -o -name ".kuzu-memory.json"

# Solutions
# Create default configuration
kuzu-memory create-config

# Specify config path
kuzu-memory --config ./kuzu-config.json enhance "test"

# Check config format
cat kuzu-config.json | python -m json.tool

# Environment variable
export KUZU_MEMORY_CONFIG="/path/to/config.json"
kuzu-memory stats
```

### **Problem: Invalid Configuration Values**
```bash
# Symptom
ERROR: validation error for KuzuMemoryConfig
ValueError: cache_size must be positive

# Diagnosis
python -c "
import json
with open('kuzu-config.json') as f:
    config = json.load(f)
    print(json.dumps(config, indent=2))
"

# Solutions
# Validate configuration
python -c "
from kuzu_memory.core.config import KuzuMemoryConfig
config = KuzuMemoryConfig.from_file('kuzu-config.json')
print('Configuration valid')
"

# Fix common issues
cat > kuzu-config.json << EOF
{
  "performance": {
    "cache_size": 1000,
    "query_timeout_ms": 5000
  }
}
EOF
```

---

## 🔗 **Integration Issues**

### **Problem: CLI Integration Failures**
```python
# Symptom
subprocess.CalledProcessError: Command '['kuzu-memory', 'enhance', 'test']' returned non-zero exit status 1

# Diagnosis
import subprocess

result = subprocess.run([
    'kuzu-memory', 'enhance', 'test'
], capture_output=True, text=True)

print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout}")
print(f"Stderr: {result.stderr}")

# Solutions
def safe_memory_enhance(prompt):
    """Safe memory enhancement with error handling."""
    try:
        result = subprocess.run([
            'kuzu-memory', 'enhance', prompt, '--format', 'plain'
        ], capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Error: {result.stderr}")
            return prompt  # Fallback to original

    except subprocess.TimeoutExpired:
        print("Memory enhancement timed out")
        return prompt
    except FileNotFoundError:
        print("kuzu-memory not found in PATH")
        return prompt
```

### **Problem: JSON Parsing Errors**
```python
# Symptom
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

# Diagnosis
result = subprocess.run([
    'kuzu-memory', 'enhance', 'test', '--format', 'json'
], capture_output=True, text=True)

print(f"Raw output: '{result.stdout}'")
print(f"Is valid JSON: {bool(result.stdout and result.stdout.strip())}")

# Solutions
def safe_json_parse(text):
    """Safe JSON parsing with error handling."""
    try:
        if not text or not text.strip():
            return {"error": "Empty response"}

        # Remove any leading/trailing whitespace or control characters
        clean_text = text.strip()

        # Try to parse JSON
        return json.loads(clean_text)

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Problematic text: '{text}'")

        # Return error structure
        return {
            "error": "JSON parse failed",
            "raw_output": text,
            "enhanced_prompt": text  # Fallback
        }

# Usage
result = subprocess.run(['kuzu-memory', 'enhance', 'test', '--format', 'json'],
                       capture_output=True, text=True)
data = safe_json_parse(result.stdout)
```

### **Problem: Async Operation Issues**
```python
# Symptom
Learning operations not completing
Memory not being stored

# Diagnosis
import asyncio
import subprocess

async def test_async_learning():
    # Test sync learning
    result = subprocess.run([
        'kuzu-memory', 'learn', 'test sync memory'
    ], capture_output=True)

    print(f"Sync learning: {result.returncode}")

    # Test async learning
    result = subprocess.run([
        'kuzu-memory', 'learn', 'test async memory', '--quiet'
    ], capture_output=True)

    print(f"Async learning: {result.returncode}")

    # Check if stored
    await asyncio.sleep(1)  # Wait for processing

    result = subprocess.run([
        'kuzu-memory', 'recall', 'test', '--format', 'json'
    ], capture_output=True, text=True)

    memories = json.loads(result.stdout)
    print(f"Memories found: {len(memories.get('memories', []))}")

# Solutions
class AsyncMemoryClient:
    def __init__(self):
        self.pending_operations = []

    async def learn_async(self, content, source="async"):
        """Reliable async learning with verification."""
        # Store with timestamp for verification
        timestamp = datetime.now().isoformat()
        tagged_content = f"{content} [stored:{timestamp}]"

        # Use subprocess with proper error handling
        process = await asyncio.create_subprocess_exec(
            'kuzu-memory', 'learn', tagged_content,
            '--source', source, '--quiet',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            print(f"Learning failed: {stderr.decode()}")
            return False

        # Optional: Verify storage after delay
        await asyncio.sleep(0.5)
        return await self.verify_storage(tagged_content)

    async def verify_storage(self, content):
        """Verify content was stored."""
        try:
            result = await asyncio.create_subprocess_exec(
                'kuzu-memory', 'recall', content[:20],  # Search partial
                '--format', 'json',
                stdout=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            data = json.loads(stdout.decode())
            return len(data.get('memories', [])) > 0
        except:
            return False
```

---

## 🐛 **Common Error Messages**

### **Error: "Module not found"**
```bash
# Full error
ModuleNotFoundError: No module named 'kuzu_memory'
ImportError: cannot import name 'KuzuMemory' from 'kuzu_memory'

# Root cause
- Incorrect installation
- Wrong Python environment
- Path issues

# Solution
# Check installation
pip list | grep kuzu-memory

# Reinstall
pip uninstall kuzu-memory
pip install kuzu-memory

# Check Python path
python -c "import sys; print(sys.path)"
```

### **Error: "Database schema version mismatch"**
```bash
# Full error
ERROR: Database schema version 2, expected version 3
ERROR: Please run database migration

# Root cause
- Old database with new KuzuMemory version
- Migration not run

# Solution
# Backup database
cp -r kuzu-memories/ kuzu-memories-backup/

# Run migration
kuzu-memory migrate --from-version 2

# If migration fails, reinitialize
kuzu-memory init --force

# Import data from backup
kuzu-memory import kuzu-memories-backup/
```

### **Error: "Content too large"**
```bash
# Full error
ERROR: Content exceeds maximum length of 100000 characters
ValidationError: ensure this value has at most 100000 characters

# Root cause
- Input content too large
- Configuration limits

# Solution
# Chunk large content
def chunk_content(content, max_size=50000):
    """Split large content into chunks."""
    chunks = []
    words = content.split()
    current_chunk = []
    current_size = 0

    for word in words:
        word_size = len(word) + 1  # +1 for space
        if current_size + word_size > max_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_size = word_size
        else:
            current_chunk.append(word)
            current_size += word_size

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

# Store chunks separately
large_content = "..." # Your large content
for i, chunk in enumerate(chunk_content(large_content)):
    subprocess.run([
        'kuzu-memory', 'learn', chunk,
        '--source', f'large-doc-part-{i}'
    ])
```

---

## 🛠️ **Advanced Debugging**

### **Debug Mode Analysis**
```bash
# Enable comprehensive debugging
export KUZU_MEMORY_DEBUG=true
export KUZU_MEMORY_LOG_LEVEL=DEBUG

# Run with debug output
kuzu-memory --debug enhance "debug test" 2>&1 | tee debug.log

# Analyze debug output
grep "ERROR" debug.log
grep "WARNING" debug.log
grep "ms" debug.log | grep -E "[0-9]{3,}"  # Find slow operations
```

### **Performance Profiling**
```bash
# Profile CLI operations
time kuzu-memory enhance "performance test"
/usr/bin/time -v kuzu-memory enhance "memory test"

# Python profiling
python -m cProfile -s cumulative -o profile.stats $(which kuzu-memory) enhance "test"
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(20)
"

# Memory profiling
valgrind --tool=memcheck --leak-check=full kuzu-memory enhance "test"

# System call tracing
strace -c kuzu-memory enhance "test"
strace -t -e trace=file kuzu-memory enhance "test"
```

### **Database Analysis**
```bash
# Analyze database structure
sqlite3 kuzu-memories/kuzu.db << EOF
.schema
.tables
SELECT COUNT(*) FROM memories;
SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type;
PRAGMA integrity_check;
PRAGMA foreign_key_check;
EOF

# Check database size and fragmentation
sqlite3 kuzu-memories/kuzu.db << EOF
PRAGMA page_count;
PRAGMA page_size;
PRAGMA freelist_count;
VACUUM;
EOF

# Export for analysis
kuzu-memory recall --format json --limit 1000 > memories_export.json
python -c "
import json
with open('memories_export.json') as f:
    data = json.load(f)
    print(f'Total memories: {len(data.get(\"memories\", []))}')
    types = {}
    for memory in data.get('memories', []):
        t = memory.get('memory_type', 'unknown')
        types[t] = types.get(t, 0) + 1
    print('Memory types:', types)
"
```

### **Network and Integration Debugging**
```python
# Debug subprocess calls
import subprocess
import logging

# Enable subprocess debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_subprocess_call(cmd, **kwargs):
    """Debug subprocess calls with detailed logging."""
    logger.debug(f"Executing: {' '.join(cmd)}")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            **kwargs
        )

        execution_time = (time.time() - start_time) * 1000

        logger.debug(f"Exit code: {result.returncode}")
        logger.debug(f"Execution time: {execution_time:.1f}ms")
        logger.debug(f"Stdout length: {len(result.stdout)}")
        logger.debug(f"Stderr length: {len(result.stderr)}")

        if result.stderr:
            logger.warning(f"Stderr: {result.stderr}")

        return result

    except Exception as e:
        logger.error(f"Subprocess error: {e}")
        raise

# Usage
result = debug_subprocess_call([
    'kuzu-memory', 'enhance', 'debug test', '--format', 'json'
])
```

---

## 📊 **Monitoring and Health Checks**

### **Health Check Script**
```python
#!/usr/bin/env python3
"""KuzuMemory health check script."""

import subprocess
import json
import sys
import time
from pathlib import Path

def check_installation():
    """Check if KuzuMemory is properly installed."""
    try:
        result = subprocess.run(['kuzu-memory', '--version'],
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0, result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "kuzu-memory command not found or timed out"

def check_initialization(project_path="."):
    """Check if project is initialized."""
    memories_path = Path(project_path) / "kuzu-memories"
    if not memories_path.exists():
        return False, "kuzu-memories directory not found"

    try:
        result = subprocess.run(['kuzu-memory', 'project'],
                              cwd=project_path, capture_output=True, text=True, timeout=5)
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "project check timed out"

def check_performance():
    """Check system performance."""
    try:
        # Test enhance performance
        start_time = time.time()
        result = subprocess.run([
            'kuzu-memory', 'enhance', 'performance test', '--format', 'json'
        ], capture_output=True, text=True, timeout=10)

        enhance_time = (time.time() - start_time) * 1000

        if result.returncode != 0:
            return False, f"enhance command failed: {result.stderr}"

        # Test learn performance
        start_time = time.time()
        result = subprocess.run([
            'kuzu-memory', 'learn', 'health check test memory', '--quiet'
        ], capture_output=True, text=True, timeout=10)

        learn_time = (time.time() - start_time) * 1000

        if result.returncode != 0:
            return False, f"learn command failed: {result.stderr}"

        return True, f"enhance: {enhance_time:.1f}ms, learn: {learn_time:.1f}ms"

    except subprocess.TimeoutExpired:
        return False, "performance test timed out"

def check_database_integrity():
    """Check database integrity."""
    try:
        result = subprocess.run([
            'kuzu-memory', 'stats', '--format', 'json'
        ], capture_output=True, text=True, timeout=5)

        if result.returncode != 0:
            return False, f"stats command failed: {result.stderr}"

        stats = json.loads(result.stdout)
        memory_count = stats.get('memory_count', 0)

        return True, f"database healthy, {memory_count} memories"

    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        return False, f"database check failed: {e}"

def main():
    """Run all health checks."""
    checks = [
        ("Installation", check_installation),
        ("Initialization", check_initialization),
        ("Performance", check_performance),
        ("Database", check_database_integrity),
    ]

    print("KuzuMemory Health Check")
    print("=" * 30)

    all_passed = True

    for check_name, check_func in checks:
        try:
            passed, message = check_func()
            status = "PASS" if passed else "FAIL"
            print(f"{check_name:15} [{status}] {message}")

            if not passed:
                all_passed = False

        except Exception as e:
            print(f"{check_name:15} [ERROR] {e}")
            all_passed = False

    print("=" * 30)
    print(f"Overall Status: {'HEALTHY' if all_passed else 'ISSUES DETECTED'}")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
```

### **Automated Diagnostics**
```bash
#!/bin/bash
# kuzu-memory-diagnostics.sh

echo "KuzuMemory Diagnostics Report"
echo "============================="
echo "Date: $(date)"
echo "User: $(whoami)"
echo "Working Directory: $(pwd)"
echo

echo "System Information:"
echo "- OS: $(uname -s)"
echo "- Architecture: $(uname -m)"
echo "- Python: $(python --version 2>&1)"
echo "- Disk Space: $(df -h . | tail -1 | awk '{print $4}' ) available"
echo "- Memory: $(free -h | grep Mem | awk '{print $7}') available"
echo

echo "KuzuMemory Installation:"
echo "- Version: $(kuzu-memory --version 2>/dev/null || echo 'NOT INSTALLED')"
echo "- Location: $(which kuzu-memory 2>/dev/null || echo 'NOT FOUND')"
echo "- Python module: $(python -c 'import kuzu_memory; print(kuzu_memory.__version__)' 2>/dev/null || echo 'NOT FOUND')"
echo

echo "Project Status:"
if [ -d "kuzu-memories" ]; then
    echo "- Database exists: YES"
    echo "- Database size: $(du -sh kuzu-memories/ | cut -f1)"
    echo "- Files: $(find kuzu-memories/ -type f | wc -l)"
else
    echo "- Database exists: NO"
fi
echo

echo "Performance Test:"
if command -v kuzu-memory >/dev/null 2>&1; then
    if [ -d "kuzu-memories" ]; then
        echo "- Testing enhance command..."
        time timeout 10 kuzu-memory enhance "test query" >/dev/null 2>&1
        echo "- Testing learn command..."
        time timeout 10 kuzu-memory learn "diagnostic test" --quiet >/dev/null 2>&1
    else
        echo "- Project not initialized"
    fi
else
    echo "- KuzuMemory not available"
fi
echo

echo "Recent Errors (if any):"
if [ -f ~/.kuzu-memory/error.log ]; then
    tail -5 ~/.kuzu-memory/error.log
else
    echo "- No error log found"
fi
```

---

## 🔍 **Recovery Procedures**

### **Complete System Recovery**
```bash
#!/bin/bash
# kuzu-memory-recovery.sh

echo "KuzuMemory System Recovery"
echo "=========================="

# 1. Backup existing data
if [ -d "kuzu-memories" ]; then
    echo "Backing up existing database..."
    cp -r kuzu-memories/ kuzu-memories-backup-$(date +%Y%m%d-%H%M%S)/
    echo "Backup created: kuzu-memories-backup-$(date +%Y%m%d-%H%M%S)/"
fi

# 2. Clean installation
echo "Performing clean installation..."
pip uninstall -y kuzu-memory
pip cache purge
pip install kuzu-memory

# 3. Reinitialize
echo "Reinitializing project..."
rm -rf kuzu-memories/
kuzu-memory init

# 4. Verify installation
echo "Verifying installation..."
kuzu-memory --version
kuzu-memory project

# 5. Test basic functionality
echo "Testing basic functionality..."
kuzu-memory learn "Recovery test memory"
kuzu-memory enhance "test query"

echo "Recovery complete!"
```

### **Data Recovery from Backup**
```bash
#!/bin/bash
# restore-from-backup.sh

BACKUP_DIR="$1"

if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

echo "Restoring from backup: $BACKUP_DIR"

# Stop any running processes
pkill -f kuzu-memory

# Remove current database
rm -rf kuzu-memories/

# Restore from backup
cp -r "$BACKUP_DIR" kuzu-memories/

# Fix permissions
chmod -R 755 kuzu-memories/

# Test restoration
kuzu-memory project
kuzu-memory stats

echo "Restoration complete!"
```

---

## 📞 **Getting Help**

### **Information to Collect**
When reporting issues, please collect:

1. **System Information**
   ```bash
   uname -a
   python --version
   kuzu-memory --version
   pip list | grep kuzu
   ```

2. **Error Details**
   ```bash
   kuzu-memory --debug [failing-command] 2>&1 | tee error.log
   ```

3. **Environment**
   ```bash
   env | grep KUZU
   pwd
   ls -la kuzu-memories/
   ```

4. **Configuration**
   ```bash
   cat kuzu-config.json 2>/dev/null || echo "No config file"
   ```

### **Support Channels**
- **Documentation**: Start with [Getting Started Guide](getting-started.md)
- **GitHub Issues**: For bug reports with reproduction steps
- **Discussions**: For usage questions and community help
- **Debug Commands**: Use `--debug` flag for detailed output

### **Self-Help Resources**
- **[API Reference](api-reference.md)** - Complete command reference
- **[Integration Guide](integration-guide.md)** - Integration patterns
- **[Performance Guide](performance.md)** - Optimization strategies
- **[Testing Guide](testing-guide.md)** - Testing your setup

**Comprehensive troubleshooting guide for KuzuMemory!** 🔧🚨