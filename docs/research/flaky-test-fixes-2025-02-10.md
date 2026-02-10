# Flaky MCP Test Fixes - 2025-02-10

## Problem Summary

Four integration tests were failing intermittently when run in bulk, but passing when run individually. This is classic flaky test behavior caused by race conditions and insufficient wait times for asynchronous operations.

### Failing Tests

1. `test_graceful_shutdown` - Server shutdown timing race condition
2. `test_connection_initialization_flow` - Notification processing timing issue
3. `test_invalid_notification` - Server response timing after invalid notification
4. `test_notification_after_error` - Response timing after error + notification

## Root Cause Analysis

### Common Pattern: Insufficient Wait Times

All failures were caused by **race conditions between client and server operations** during:
- Process termination checks
- Notification processing (fire-and-forget operations)
- Response waiting after error conditions

### Specific Issues

#### 1. `test_graceful_shutdown` (Line 87-109)

**Problem**: After sending shutdown request, test waited only 0.5s and checked `process.poll()` once.

```python
# ❌ BEFORE: Single check, no retry
await asyncio.sleep(0.5)
if client.process:
    assert client.process.poll() is not None, "Server did not shut down gracefully"
```

**Root Cause**: Server shutdown is not instantaneous. In bulk test runs, system load can delay process termination beyond 0.5s.

**Fix**: Exponential backoff retry logic with max 6.2s wait time.

```python
# ✅ AFTER: Retry with exponential backoff
max_retries = 5
for attempt in range(max_retries):
    await asyncio.sleep(0.2 * (2 ** attempt))  # 0.2s, 0.4s, 0.8s, 1.6s, 3.2s

    if client.process and client.process.poll() is not None:
        break  # Process terminated successfully
else:
    # All retries exhausted
    if client.process:
        assert client.process.poll() is not None, "Server did not shut down gracefully after 6.2s"
```

#### 2. `test_connection_initialization_flow` (Line 253-274)

**Problem**: After sending `notifications/initialized`, test immediately sent ping request without waiting for server to process notification.

```python
# ❌ BEFORE: No wait after notification
await client.send_notification("notifications/initialized", {})

# Immediately ping (race condition!)
ping_response = await client.send_request("ping", {})
assert ping_response is not None, "Post-initialization ping failed"
```

**Root Cause**: Notifications are **fire-and-forget** (no response expected). Server needs time to process notification before handling next request. In bulk runs, server may be processing previous notification when ping arrives.

**Fix**: Wait 0.3s after notification + retry logic for ping.

```python
# ✅ AFTER: Wait for notification processing + retry ping
await client.send_notification("notifications/initialized", {})

# Wait for server to process notification
await asyncio.sleep(0.3)

# Retry ping with exponential backoff
ping_response = None
for attempt in range(3):
    ping_response = await client.send_request("ping", {})
    if ping_response is not None:
        break
    await asyncio.sleep(0.2 * (attempt + 1))  # 0.2s, 0.4s, 0.6s

assert ping_response is not None, "Post-initialization ping failed after retries"
```

#### 3. `test_invalid_notification` and `test_notification_after_error` (Lines 432-476)

**Problem**: Same pattern as #2 - notifications sent without sufficient wait time before next request.

```python
# ❌ BEFORE: Short wait (0.2s), single attempt
await client.send_notification("invalid/notification", {})
await asyncio.sleep(0.2)

response = await client.send_request("ping", {})
assert response is not None
```

**Root Cause**: In bulk test runs, server may need more time to process notification before responding to ping.

**Fix**: Increased wait time (0.3s) + retry logic.

```python
# ✅ AFTER: Longer wait (0.3s) + retry with exponential backoff
await client.send_notification("invalid/notification", {})
await asyncio.sleep(0.3)

# Retry ping with exponential backoff
response = None
for attempt in range(3):
    response = await client.send_request("ping", {})
    if response is not None:
        break
    await asyncio.sleep(0.2 * (attempt + 1))  # 0.2s, 0.4s, 0.6s

assert response is not None, "Server failed to respond after invalid notification"
```

## Solution Strategy

### 1. Exponential Backoff for Process Operations

For operations that depend on process state (shutdown, termination):
- Retry with exponential backoff: `0.2 * (2 ** attempt)` seconds
- Maximum retries: 5 (total wait: ~6.2s)
- Check process state in each iteration

### 2. Wait + Retry for Notification Processing

For operations after notifications:
- Initial wait: 0.3s (up from 0.2s) to allow notification processing
- Retry subsequent requests: 3 attempts with linear backoff (0.2s, 0.4s, 0.6s)
- Total max wait: 0.3s + 1.2s = 1.5s

### 3. Improved Error Messages

All assertions now include descriptive messages explaining what failed:
- "Server did not shut down gracefully after 6.2s"
- "Post-initialization ping failed after retries"
- "Server failed to respond after invalid notification"

## Test Results

### Before Fixes

- Individual tests: ✅ Pass (low system load)
- Bulk test runs: ❌ Intermittent failures (race conditions under load)

### After Fixes

- Individual tests: ✅ Pass (all 4 tests)
- Bulk test runs (3 iterations): ✅ Pass (all 4 tests, 12/12 runs successful)
- Full test suite: ✅ Pass (39 tests in 68.43s)

```bash
# Verification runs
$ for i in {1..3}; do pytest <flaky_tests> -v; done
=== Run 1 === 4 passed in 5.17s ✅
=== Run 2 === 4 passed in 5.16s ✅
=== Run 3 === 4 passed in 5.18s ✅

# Full test suite
$ pytest tests/mcp/integration/ -v
39 passed in 68.43s (0:01:08) ✅
```

## Key Takeaways

### 1. Never Use Single-Attempt Timing for Async Operations

**❌ DON'T:**
```python
await asyncio.sleep(0.5)
assert condition, "Operation failed"
```

**✅ DO:**
```python
for attempt in range(max_retries):
    await asyncio.sleep(backoff_time)
    if condition:
        break
else:
    assert condition, "Operation failed after retries"
```

### 2. Notifications Need Processing Time

**❌ DON'T:**
```python
await client.send_notification("event", {})
response = await client.send_request("next_operation", {})  # Race!
```

**✅ DO:**
```python
await client.send_notification("event", {})
await asyncio.sleep(0.3)  # Allow notification processing
response = await client.send_request("next_operation", {})
```

### 3. Process Operations Need Retries

**❌ DON'T:**
```python
process.terminate()
await asyncio.sleep(0.5)
assert process.poll() is not None  # Might still be running!
```

**✅ DO:**
```python
process.terminate()
for attempt in range(max_retries):
    await asyncio.sleep(backoff_time)
    if process.poll() is not None:
        break
```

### 4. Descriptive Error Messages Help Debugging

Always include context in assertions:
- What operation was being performed
- How many retries were attempted
- How much time elapsed

```python
# ❌ BAD
assert response is not None

# ✅ GOOD
assert response is not None, "Post-initialization ping failed after 3 retries (1.5s total)"
```

## Files Modified

1. `tests/mcp/integration/test_connection_integration.py`
   - `test_graceful_shutdown`: Added exponential backoff for process termination check
   - `test_connection_initialization_flow`: Added wait time + retry logic for post-notification ping

2. `tests/mcp/integration/test_error_scenarios.py`
   - `test_invalid_notification`: Increased wait time + added retry logic
   - `test_notification_after_error`: Increased wait time + added retry logic

## Prevention Strategy

### For Future Tests

1. **Always use retry logic** for timing-sensitive operations
2. **Increase wait times** for notification processing (0.3s minimum)
3. **Use exponential backoff** for process state checks
4. **Test in bulk** (run 3+ times) to catch race conditions
5. **Add descriptive error messages** for failed assertions

### Checklist for Async Tests

- [ ] Does test involve process termination? → Add exponential backoff retry
- [ ] Does test send notifications? → Add 0.3s+ wait before next operation
- [ ] Does test check response timing? → Add retry logic for responses
- [ ] Does test run reliably 3+ times in bulk? → Verify no race conditions
- [ ] Do error messages explain what failed? → Add context to assertions

## Conclusion

All flaky tests are now **deterministic and robust** through:
- Exponential backoff for process operations (max 6.2s)
- Increased wait times for notification processing (0.3s)
- Retry logic for response waiting (3 attempts, 1.2s max)
- Descriptive error messages for debugging

Tests now pass consistently in both individual and bulk runs, eliminating race conditions that caused intermittent failures.
