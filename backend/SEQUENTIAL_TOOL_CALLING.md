# Sequential Tool Calling Implementation

## Summary

Successfully refactored `ai_generator.py` to support **up to 2 sequential tool calling rounds** using an iterative loop approach.

## Changes Made

### 1. Configuration (`config.py`)
Added:
```python
MAX_TOOL_ROUNDS: int = 2  # Maximum sequential tool calling rounds
```

### 2. AI Generator (`ai_generator.py`)

#### System Prompt Updates
- **Removed**: `"One tool call per query maximum"`
- **Added**:
  - `"Multiple tool calls allowed: You may call tools sequentially (up to 2 rounds)"`
  - `"Strategic tool use: Search content first, then get outline if needed"`
  - `"Follow-up searches: If initial results are insufficient, search again"`

#### Constructor
```python
def __init__(self, api_key: str, model: str, max_tool_rounds: int = 2):
    self.max_tool_rounds = max_tool_rounds
```

#### Core Logic Refactoring
**Before**: Single tool round with tools removed after execution
```python
generate_response():
    api_call(with_tools)
    if tool_use:
        _handle_tool_execution()
            execute_tools()
            api_call(WITHOUT tools)  # Tools removed!
```

**After**: Iterative loop allowing multiple rounds
```python
generate_response():
    for round_num in range(max_tool_rounds):
        api_call(WITH tools)  # Tools available in all rounds
        if not tool_use:
            return response  # Natural stop
        execute_tools()
        append_results_to_messages()

    # Max rounds reached
    api_call(WITHOUT tools)  # Force final answer
```

#### New Helper Methods
1. **`_execute_tools(content_blocks, tool_manager)`**
   - Executes all tool calls from a response
   - Handles errors gracefully (adds error to tool_result instead of crashing)
   - Returns list of tool result dictionaries

2. **`_extract_text_response(response)`**
   - Extracts text from API response content
   - Handles both real responses and mock objects
   - Provides fallback message if no text found

3. **`_make_final_call(messages, system_content)`**
   - Makes final API call without tools to force answer
   - Called when max_tool_rounds is reached
   - Ensures termination

### 3. RAG System (`rag_system.py`)
Updated AIGenerator initialization:
```python
self.ai_generator = AIGenerator(
    config.ANTHROPIC_API_KEY,
    config.ANTHROPIC_MODEL,
    config.MAX_TOOL_ROUNDS  # NEW
)
```

### 4. Tests (`test_ai_generator.py`)

#### Removed
- `test_handle_tool_execution()` - Method no longer exists

#### Updated
- `test_generate_response_with_tools_no_call` - Now requires tool_manager
- `test_handle_multiple_tool_calls` - Renamed and refactored for new flow
- `test_error_handling_in_tool_execution` - Removed (behavior changed to graceful)

#### Added (6 new tests)
1. **`test_sequential_two_tool_calls`** - Verifies 2 rounds work correctly
2. **`test_natural_stop_after_first_round`** - Early exit if Claude satisfied
3. **`test_max_rounds_forces_final_answer`** - Termination enforcement
4. **`test_tool_execution_error_graceful`** - Error handling
5. **`test_message_history_accumulation`** - Message structure validation
6. **`test_custom_max_rounds_configuration`** - Configurable rounds

## Test Results

```bash
$ uv run pytest tests/ -v
============================== 52 passed in 8.23s ==============================
```

**All tests passing** ✅
- 15 tests in `test_ai_generator.py` (6 new for sequential calling)
- 27 tests in `test_rag_integration.py` (unchanged)
- 10 tests in `test_search_tools.py` (unchanged)

## Behavior Examples

### Example 1: Single Round (Backward Compatible)
```
User: "What is MCP?"
Round 0: search_course_content(query="MCP") → results
         Claude: "MCP is Model Context Protocol..."
API Calls: 2 (same as before)
```

### Example 2: Two Sequential Rounds (New Capability)
```
User: "What is MCP and what lessons does it have?"
Round 0: search_course_content(query="MCP") → content results
Round 1: get_course_outline(course_name="MCP") → lesson list
         Claude: "MCP is a protocol with 5 lessons: Lesson 1..."
API Calls: 3
```

### Example 3: Max Rounds Reached
```
User: "Tell me everything about MCP"
Round 0: search_course_content(query="MCP overview") → results
Round 1: search_course_content(query="MCP features") → results
Round 2: MAX_ROUNDS reached → Force final answer WITHOUT tools
         Claude: "Based on the searches, MCP is..."
API Calls: 3 (2 with tools, 1 forced)
```

### Example 4: Natural Early Stop
```
User: "Who teaches MCP?"
Round 0: get_course_outline(course_name="MCP") → instructor info
         Claude: "The instructor is John Doe"
API Calls: 2 (stopped early, didn't use all rounds)
```

## Key Features

### 1. Termination Conditions (Priority Order)
1. **Natural stop**: `stop_reason != "tool_use"` (Claude decides)
2. **Max rounds**: `round_num >= max_tool_rounds` (forced)
3. **Tool error**: Added to tool_result, continues gracefully

### 2. Message History Preservation
Messages accumulate across rounds:
```
[user_query]
→ [assistant_tool_use_1]
→ [user_tool_results_1]
→ [assistant_tool_use_2]
→ [user_tool_results_2]
→ [assistant_final_answer]
```

Full context available to Claude in each round.

### 3. Tools Always Available
Tools parameter present in all rounds (0 to max_rounds-1).
Only removed in forced final call after max_rounds.

### 4. Graceful Error Handling
Tool execution errors don't crash:
```python
try:
    result = tool_manager.execute_tool(...)
except Exception as e:
    # Add error as tool_result
    tool_results.append({
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": f"Error: {str(e)}",
        "is_error": True
    })
```

Claude sees the error and can respond appropriately.

## Performance Impact

### Latency
- **Single round queries**: No change (~1-3 seconds)
- **Two round queries**: ~2-6 seconds (2 API calls + tool execution)
- Impact only when Claude needs multiple searches

### Cost
- More API calls when using multiple rounds
- Claude's updated prompt guides efficient tool use
- Most queries still use 1 round (backward compatible)

## Configuration

Customize max rounds:
```python
# In config.py
MAX_TOOL_ROUNDS: int = 2

# Or per-instance
generator = AIGenerator(api_key, model, max_tool_rounds=3)
```

## Migration Notes

### Breaking Changes
None! Existing code works unchanged.

### Recommended Updates
Update system prompts that reference "one tool call maximum" if used elsewhere.

### Monitoring
Watch for:
- Queries consistently using 2 rounds (may indicate prompt tuning needed)
- Increased latency on complex queries (expected, acceptable)
- Error rates in tool execution (should be low)

## Future Enhancements

Potential improvements:
1. **Dynamic max_rounds** per query type
2. **Tool result caching** for duplicate calls
3. **Round-specific prompts** (e.g., "This is your last chance to search")
4. **Token usage tracking** across rounds
5. **Streaming responses** (complex with multi-round)

## Conclusion

Sequential tool calling successfully implemented with:
- ✅ Clean iterative loop architecture
- ✅ Full backward compatibility
- ✅ Comprehensive test coverage (52 tests passing)
- ✅ Graceful error handling
- ✅ Configurable max rounds
- ✅ Natural termination conditions

The system now supports complex multi-step queries requiring multiple tool calls while maintaining simplicity for single-step queries.
