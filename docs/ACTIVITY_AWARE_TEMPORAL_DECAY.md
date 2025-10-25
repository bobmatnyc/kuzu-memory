# Activity-Aware Temporal Decay

## Overview

Activity-aware temporal decay makes recency calculations **relative to project activity** instead of absolute time. This solves the problem where memories appear "stale" when resuming projects after gaps, even though they were recent when the project was last active.

## Problem Statement

**Before (Absolute Time)**:
- Project last active: Jan 1, 2025
- Resume project: Feb 1, 2025 (1 month gap)
- Memory from Dec 25, 2024: 38 days old → appears "stale"

**Issue**: The memory is actually only 7 days before the last activity, but it's penalized for the 1-month gap when the project wasn't being worked on.

## Solution

**After (Activity-Aware)**:
- Same scenario as above
- Memory scored relative to last activity: 7 days old → appears "recent"
- Gap duration doesn't unfairly penalize old memories

## How It Works

### Key Concept
**"Recent" means "recent relative to when the project was last active"**

### Algorithm

```python
if project_last_activity and memory.created_at < project_last_activity:
    # Memory from before project gap
    age = project_last_activity - memory.created_at  # Relative time
else:
    # Recent memory (after resume) or no activity tracking
    age = current_time - memory.created_at  # Absolute time
```

### Decision Tree

- **Memory created BEFORE last activity**: Use relative time (activity-aware)
- **Memory created AFTER last activity**: Use absolute time (normal)
- **No last activity provided**: Use absolute time (backward compatible)

## Implementation

### Files Modified

1. **`src/kuzu_memory/recall/temporal_decay.py`**
   - Updated `calculate_temporal_score()` with `project_last_activity` parameter
   - Updated `get_decay_explanation()` to show activity-aware calculations
   - Updated `get_effective_weight()` to pass through activity parameter
   - Added `get_project_last_activity()` static helper method

### API Changes

#### `calculate_temporal_score()`

```python
def calculate_temporal_score(
    self,
    memory: Memory,
    current_time: datetime | None = None,
    project_last_activity: datetime | None = None,  # NEW PARAMETER
) -> float:
    """
    Calculate temporal decay score with activity-aware recency.

    Args:
        memory: Memory to score
        current_time: Current time (defaults to now)
        project_last_activity: Last project activity time for activity-aware decay

    Returns:
        Temporal decay score (0.0-1.0)
    """
```

**Backward Compatible**: Existing code without `project_last_activity` works unchanged.

#### `get_project_last_activity()` Helper

```python
@staticmethod
def get_project_last_activity(memories: list[Memory]) -> datetime | None:
    """
    Get the last activity time from a collection of memories.

    This finds the most recent created_at timestamp, representing when
    the project was last actively worked on.

    Returns:
        Most recent created_at datetime, or None if no valid memories
    """
```

**Usage**:
```python
# Get all memories for project
all_memories = memory_store.get_all_memories()

# Calculate last activity
last_activity = TemporalDecayEngine.get_project_last_activity(all_memories)

# Score memory with activity-aware mode
score = engine.calculate_temporal_score(
    memory,
    current_time=datetime.now(),
    project_last_activity=last_activity
)
```

#### `get_decay_explanation()` Enhanced

```python
def get_decay_explanation(
    self,
    memory: Memory,
    current_time: datetime | None = None,
    project_last_activity: datetime | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
    """Get detailed explanation including activity-aware context."""
```

**New Fields in Response**:
```python
{
    "activity_aware_mode": bool,  # Was activity-aware mode used?
    "age_days": float,  # Age used for scoring (relative or absolute)

    # Only present if activity_aware_mode is True:
    "activity_aware_context": {
        "project_last_activity": str,  # ISO timestamp
        "gap_duration_days": float,  # Time since last activity
        "absolute_age_days": float,  # Age if using absolute time
        "relative_age_days": float,  # Age relative to last activity
        "age_reduction_days": float,  # How much younger memory appears
        "explanation": str  # Human-readable explanation
    }
}
```

## Usage Examples

### Example 1: Resuming Old Project

```python
from datetime import datetime, timedelta
from kuzu_memory.recall.temporal_decay import TemporalDecayEngine
from kuzu_memory.core.models import Memory, MemoryType

# Initialize engine
engine = TemporalDecayEngine()

# Scenario: 3-month-old project
current_time = datetime(2025, 2, 1)
last_activity = datetime(2024, 11, 1)  # 3 months ago

# Memory from before the gap
memory = Memory(
    content="Bug fix in authentication service",
    memory_type=MemoryType.PROCEDURAL,
    created_at=datetime(2024, 10, 25)  # 7 days before last activity
)

# Without activity-aware (old behavior)
score_old = engine.calculate_temporal_score(memory, current_time)
# score_old ≈ 0.3 (appears very old - 99 days)

# With activity-aware (new behavior)
score_new = engine.calculate_temporal_score(
    memory, current_time, project_last_activity=last_activity
)
# score_new ≈ 0.9 (appears recent - only 7 days before last activity)

# Get explanation
explanation = engine.get_decay_explanation(
    memory, current_time, project_last_activity=last_activity
)

print(f"Activity-aware mode: {explanation['activity_aware_mode']}")  # True
print(f"Relative age: {explanation['age_days']} days")  # 7.0
print(f"Absolute age: {explanation['activity_aware_context']['absolute_age_days']} days")  # 99.0
```

### Example 2: Active Project (No Gap)

```python
# Scenario: Active project
current_time = datetime(2025, 2, 1)
last_activity = datetime(2025, 1, 31)  # Yesterday

# Recent memory
memory = Memory(
    content="Working on user dashboard",
    memory_type=MemoryType.WORKING,
    created_at=datetime(2025, 1, 31, 10, 0)  # Yesterday
)

# Activity-aware mode will use absolute time (memory after last_activity)
score = engine.calculate_temporal_score(
    memory, current_time, project_last_activity=last_activity
)

explanation = engine.get_decay_explanation(
    memory, current_time, project_last_activity=last_activity
)

print(f"Activity-aware mode: {explanation['activity_aware_mode']}")  # False
# Uses absolute time because memory is recent (after last_activity)
```

### Example 3: Automatic Last Activity Detection

```python
# Get all project memories
all_memories = memory_store.get_all_memories()

# Automatically detect last activity
last_activity = TemporalDecayEngine.get_project_last_activity(all_memories)

# Score memories with automatic activity detection
for memory in memories_to_score:
    score = engine.calculate_temporal_score(
        memory,
        current_time=datetime.now(),
        project_last_activity=last_activity
    )
```

## Benefits

### 1. **Fair Scoring After Project Gaps**
- Memories don't get unfairly penalized for project inactivity
- Old memories are scored relative to when the project was active
- Encourages continuity when resuming work

### 2. **Preserves Recent Memory Behavior**
- Memories created after project resume use normal absolute time
- No changes to active project behavior
- Recent memories still rank higher than old ones

### 3. **Backward Compatible**
- Existing code without `project_last_activity` works unchanged
- Optional parameter defaults to `None` (uses absolute time)
- No breaking changes to existing API

### 4. **Transparent and Explainable**
- `get_decay_explanation()` shows which mode was used
- Detailed context about age calculations
- Easy to debug and understand scoring

### 5. **Memory Type Aware**
- Still respects memory type decay rates
- SEMANTIC memories remain stable
- WORKING memories still decay fast
- Activity-aware mode complements existing decay functions

## Testing

Comprehensive test suite in `tests/unit/test_activity_aware_temporal_decay.py`:

### Test Coverage

1. **Normal mode without last activity** - Backward compatibility
2. **Activity-aware mode with project gap** - Core functionality
3. **Recent memory after gap uses absolute time** - Hybrid behavior
4. **Mixed scenario** - Both modes in same session
5. **Helper method tests** - `get_project_last_activity()`
6. **Memory type specific behavior** - WORKING, SEMANTIC, PROCEDURAL
7. **Explanation formatting** - Human-readable output
8. **Integration scenarios** - Real-world use cases

### Running Tests

```bash
# Run activity-aware tests only
pytest tests/unit/test_activity_aware_temporal_decay.py -v

# Run all temporal tests
pytest tests/unit/ -k "temporal" -v

# Check backward compatibility
pytest tests/unit/test_models.py -v
```

## Performance Considerations

- **No Performance Impact**: Activity-aware calculation is O(1) per memory
- **Helper Method**: `get_project_last_activity()` is O(n) but only called once
- **Memory Overhead**: Minimal (one additional datetime comparison)
- **Cache Friendly**: Results can still be cached as before

## Edge Cases Handled

1. **Empty memory list**: Returns `None` for last activity
2. **None timestamps**: Filtered out when finding last activity
3. **Memory exactly at last activity**: Uses absolute time (not before)
4. **No project gap**: Automatically uses absolute time
5. **Very large gaps**: Handles months/years correctly

## Integration with Ranking System

The ranking system (`ranking.py`) can be updated to use activity-aware decay:

```python
# In MemoryRanker._calculate_memory_score()

# Get project last activity (cache this!)
last_activity = TemporalDecayEngine.get_project_last_activity(all_memories)

# Calculate recency with activity-aware mode
scores["recency"] = self.temporal_decay_engine.calculate_temporal_score(
    memory,
    current_time=datetime.now(),
    project_last_activity=last_activity
)
```

## Future Enhancements

1. **Per-Project Last Activity**: Track last activity per project separately
2. **Session-Based Gaps**: Handle multiple gaps (sessions) more granularly
3. **Weighted Gap Penalty**: Optionally penalize very long gaps
4. **Activity Types**: Different last activity times for different memory types
5. **Smart Gap Detection**: Automatically detect gaps vs. continuous work

## Migration Guide

### For Existing Codebases

**No migration required!** The implementation is backward compatible.

**Optional Enhancement**:
```python
# Before (still works):
score = engine.calculate_temporal_score(memory)

# After (enhanced):
last_activity = TemporalDecayEngine.get_project_last_activity(all_memories)
score = engine.calculate_temporal_score(
    memory,
    project_last_activity=last_activity
)
```

### For Custom Implementations

If you've subclassed `TemporalDecayEngine`:

1. **No changes required** if you don't override `calculate_temporal_score()`
2. **If overridden**: Add optional `project_last_activity` parameter
3. **Call parent**: Use `super().calculate_temporal_score()` for activity-aware behavior

## Conclusion

Activity-aware temporal decay provides a more intelligent recency calculation that:
- Handles project gaps gracefully
- Preserves recent memory prioritization
- Remains fully backward compatible
- Enhances user experience when resuming old projects

The implementation is production-ready, well-tested, and easy to integrate.
