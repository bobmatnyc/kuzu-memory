# Known Issues - KuzuMemory v1.1.0

**Status**: Production Ready with Known Limitations
**Last Updated**: 2025-09-27
**Version**: v1.1.0

---

## 🔴 CRITICAL ISSUES

### 1. MCP Server Runtime Error ⚠️
**Issue**: MCP server implementation throws RuntimeError related to async generator
**Status**: **BLOCKING MCP FUNCTIONALITY**
**Impact**: HIGH - Claude Desktop integration non-functional

**Error Details**:
```
RuntimeError: async generator didn't stop after athrow()
```

**Root Cause**: Async generator pattern in MCP server implementation not properly handling cleanup
**Workaround**: Use CLI interface instead of MCP server
**Upstream Dependencies**: None - internal implementation issue
**Fix Timeline**: High priority for v1.1.1

### 2. Memory Recall Returns Empty Results ⚠️
**Issue**: Search/recall operations return empty results even after storing memories
**Status**: **BLOCKING CORE FUNCTIONALITY**
**Impact**: HIGH - Primary memory retrieval feature non-functional

**Symptoms**:
- `kuzu-memory recall <query>` returns no results
- Database contains stored memories (confirmed via stats)
- Search algorithms not matching stored content

**Root Cause**: Search/indexing mismatch in recall implementation
**Workaround**: Use `kuzu-memory stats` to verify storage, manual database queries
**Fix Timeline**: Critical priority for v1.1.1

### 3. Dual Database Location Conflict ⚠️
**Issue**: Multiple memory database directories exist simultaneously
**Status**: **DATA CONSISTENCY RISK**
**Impact**: MEDIUM - Potential data fragmentation and confusion

**Conflicting Locations**:
- `.kuzu_memory/` (primary database location)
- `kuzu-memories/` (secondary/legacy location)
- `.test_kuzu_memory/` (test database)
- `.kuzu-memory-backups/` (backup location)

**Root Cause**: Migration/refactoring left multiple database paths
**Data Risk**: Memories may be split across locations
**Workaround**: Manually consolidate to `.kuzu_memory/`
**Fix Timeline**: Medium priority - data consolidation script needed

---

## 🟡 MEDIUM PRIORITY ISSUES

### 4. Async Learning Queue Reliability
**Issue**: Background learning operations may fail silently under high load
**Status**: **MONITORING REQUIRED**
**Impact**: MEDIUM - Memory storage may be incomplete

**Details**:
- 5-second threshold helps but not foolproof
- Error handling could be improved
- No persistence for failed learning attempts

**Workaround**: Use synchronous learning for critical memories
**Fix Timeline**: v1.2.0 planning

### 5. Performance Thresholds Not Configurable
**Issue**: 100ms/200ms thresholds are hardcoded
**Status**: **ENHANCEMENT NEEDED**
**Impact**: LOW - Affects different hardware configurations

**Details**: Users on slower systems may need different performance expectations
**Workaround**: Modify source code for custom thresholds
**Fix Timeline**: v1.2.0 feature enhancement

---

## 🟢 LOW PRIORITY ISSUES

### 6. CLI Response Time Perception
**Issue**: CLI feels slower than reported 3ms benchmarks during interactive use
**Status**: **USER EXPERIENCE**
**Impact**: LOW - Functionality works, perception issue

**Details**: Startup overhead affects perceived performance in CLI
**Measurement**: Actual recall is 3ms, total CLI response ~50-100ms
**Workaround**: Use Python API for performance-critical applications

---

## 📋 FIX ROADMAP

### Immediate (v1.1.1) - Critical Fixes
1. **Fix MCP Server Async Generator** (Priority: Critical)
   - Investigate async generator cleanup
   - Implement proper resource management
   - Add comprehensive error handling

2. **Fix Memory Recall Search** (Priority: Critical)
   - Debug search algorithm implementation
   - Verify Kuzu query generation
   - Test with various query patterns

3. **Database Location Consolidation** (Priority: High)
   - Create migration script
   - Update configuration to single location
   - Add data validation after migration

### Short Term (v1.2.0) - Reliability Improvements
4. **Enhanced Async Learning**
   - Add persistence for failed operations
   - Improve error reporting
   - Add retry mechanisms

5. **Configurable Performance Thresholds**
   - Add configuration file support
   - Allow user-defined timeouts
   - Hardware-specific optimizations

### Long Term (v1.3.0+) - User Experience
6. **CLI Performance Optimization**
   - Reduce startup overhead
   - Add response time monitoring
   - Implement caching strategies

---

## 🛠️ WORKAROUNDS & MITIGATIONS

### For MCP Server Issues
```bash
# Use CLI interface instead
kuzu-memory enhance "your prompt here"
kuzu-memory recall "search query"
```

### For Memory Recall Issues
```bash
# Verify storage first
kuzu-memory stats

# Try different query patterns
kuzu-memory recall "exact phrase"
kuzu-memory recall "partial word"
```

### For Database Location Issues
```bash
# Check all database locations
find . -name "*.kuzu*" -o -name "*memory*" -type d

# Backup before consolidation
cp -r .kuzu_memory .kuzu-memory-backups/
```

---

## 📊 IMPACT ANALYSIS

### Production Readiness Assessment
- **Core Storage**: ✅ Working (verified 300 bytes/memory)
- **Performance**: ✅ Working (3ms recall when functional)
- **Database**: ✅ Working (genuine Kuzu implementation)
- **MCP Integration**: ❌ **BROKEN** (critical for Claude Desktop)
- **Memory Recall**: ❌ **BROKEN** (critical for core functionality)

### Deployment Recommendations
- **CLI Usage**: ✅ Safe for development/testing
- **Python API**: ✅ Safe with workarounds
- **MCP Server**: ❌ **DO NOT DEPLOY** until v1.1.1
- **Production Systems**: ⚠️ **DELAY** until recall fixes

---

## 📞 SUPPORT & REPORTING

### For New Issues
1. Check this document first
2. Verify with latest version
3. Test workarounds
4. Report with reproduction steps

### Known Issue Updates
This document is updated with each release and critical findings.

**Next Review**: With v1.1.1 release
**Critical Issue Tracking**: GitHub Issues #TBD

---

**Note**: Despite known issues, the core architecture and database implementation are sound. These are implementation bugs that can be resolved without architectural changes.