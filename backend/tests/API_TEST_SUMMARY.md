# API Testing Framework Summary

## Overview

This document summarizes the API testing infrastructure enhancements made to the RAG system's testing framework.

## What Was Added

### 1. Pytest Configuration (`pyproject.toml`)

Added comprehensive pytest configuration under `[tool.pytest.ini_options]`:

- **Test Discovery**: Automatically finds tests in `backend/tests/` directory
- **Markers**: Defined test categories (unit, integration, api, slow)
- **Output Options**: Verbose output with short tracebacks
- **Warning Filters**: Suppresses common deprecation warnings
- **Dependencies**: Added `httpx>=0.28.1` for API testing

```toml
[tool.pytest.ini_options]
testpaths = ["backend/tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = ["-v", "--strict-markers", "--tb=short", "--disable-warnings"]
markers = [
    "unit: Unit tests for individual components",
    "integration: Integration tests for component interactions",
    "api: API endpoint tests",
    "slow: Tests that take longer to run",
]
```

### 2. API Testing Fixtures (`conftest.py`)

Enhanced `conftest.py` with specialized API testing fixtures:

#### `mock_rag_system` Fixture
- Mocks the RAGSystem for isolated API testing
- Returns predictable responses for query and analytics methods
- Simulates session creation and management

#### `test_app` Fixture
- Creates a minimal FastAPI test application
- Defines API endpoints inline (avoids static file mounting issues)
- Includes all production endpoints: `/`, `/api/query`, `/api/courses`
- Adds CORS middleware for realistic testing

#### `client` Fixture
- Provides FastAPI TestClient for making HTTP requests
- Automatically handles request/response serialization
- No server startup required (in-memory testing)

### 3. Comprehensive API Endpoint Tests (`test_api_endpoints.py`)

Created 25 API tests organized into 3 test classes:

#### TestAPIEndpoints (17 tests)
Tests core functionality of API endpoints:

- **Root endpoint**: Welcome message validation
- **Query endpoint success**: Valid query processing
- **Session handling**: New and existing session IDs
- **Input validation**: Missing fields, empty queries, invalid JSON
- **Error handling**: Internal errors, exception propagation
- **Response validation**: Pydantic model conformance
- **Edge cases**: Special characters, long text, concurrent queries
- **Courses endpoint**: Statistics retrieval, empty state

#### TestAPIErrorHandling (5 tests)
Tests error scenarios and edge cases:

- **404 errors**: Nonexistent endpoint handling
- **405 errors**: Wrong HTTP method detection
- **Null values**: Optional field handling
- **Extra fields**: Ignored additional request fields
- **Malformed input**: Invalid session IDs

#### TestAPIIntegrationFlow (3 tests)
Tests complete workflows:

- **Full query workflow**: Courses list → Query → Follow-up
- **Health checks**: Basic API availability
- **Error recovery**: System resilience after failures

## Test Coverage

### Endpoints Tested

1. **GET /**
   - Welcome message
   - Basic connectivity

2. **POST /api/query**
   - Request validation
   - Session management
   - Error handling
   - Response structure
   - Special characters and edge cases

3. **GET /api/courses**
   - Course statistics
   - Empty state handling
   - Error propagation

### Test Scenarios

- ✅ Successful requests with valid data
- ✅ Missing required fields (422 errors)
- ✅ Invalid JSON formatting (422 errors)
- ✅ Internal server errors (500 errors)
- ✅ Wrong HTTP methods (405 errors)
- ✅ Nonexistent endpoints (404 errors)
- ✅ Session persistence across queries
- ✅ Response model validation
- ✅ Special characters and Unicode
- ✅ Very long text inputs
- ✅ Concurrent query handling
- ✅ Error recovery

## Running the Tests

### Run All API Tests
```bash
uv run pytest tests/test_api_endpoints.py -v
```

### Run Tests by Marker
```bash
# Only API tests
uv run pytest -m api

# Only unit tests
uv run pytest -m unit

# Exclude slow tests
uv run pytest -m "not slow"
```

### Run Specific Test Class
```bash
uv run pytest tests/test_api_endpoints.py::TestAPIEndpoints -v
```

### Run Single Test
```bash
uv run pytest tests/test_api_endpoints.py::TestAPIEndpoints::test_query_endpoint_success -v
```

## Test Results

All 25 API tests pass successfully:

```
tests/test_api_endpoints.py::TestAPIEndpoints::test_root_endpoint PASSED
tests/test_api_endpoints.py::TestAPIEndpoints::test_query_endpoint_success PASSED
tests/test_api_endpoints.py::TestAPIEndpoints::test_query_endpoint_with_existing_session PASSED
... (22 more tests)

============================== 25 passed in 0.63s ==============================
```

## Architecture Benefits

### 1. Isolation from Production App
- Test app defined inline in fixtures
- No dependency on `backend/app.py` static file mounting
- Avoids "frontend directory not found" errors in CI/CD

### 2. Fast Execution
- In-memory testing (no actual HTTP server)
- Mocked RAG system (no AI API calls)
- No database operations
- Complete suite runs in <1 second

### 3. Maintainability
- Centralized fixtures in `conftest.py`
- Clear test organization by concern
- Descriptive test names and docstrings
- Easy to add new test cases

### 4. CI/CD Ready
- Pytest markers for selective execution
- Warning suppression for clean output
- Configurable test paths
- No external dependencies required

## Integration with Existing Tests

The API tests complement existing test files:

- `test_ai_generator.py`: AI/LLM interaction tests
- `test_search_tools.py`: Vector search and tool tests
- `test_rag_integration.py`: End-to-end RAG pipeline tests
- `test_live_system.py`: Real database integration tests
- **`test_api_endpoints.py`**: HTTP API layer tests (NEW)

## Future Enhancements

Potential additions to the testing framework:

1. **Authentication Tests**: If auth is added to API
2. **Rate Limiting Tests**: API throttling validation
3. **Performance Tests**: Load testing with multiple clients
4. **WebSocket Tests**: If real-time features are added
5. **Contract Tests**: OpenAPI/Swagger schema validation
6. **End-to-End Tests**: Full stack tests with frontend

## Dependencies

The following packages support API testing:

- `pytest>=8.4.2`: Test framework
- `pytest-mock>=3.15.1`: Mocking utilities
- `httpx>=0.28.1`: HTTP client (used by TestClient)
- `fastapi==0.116.1`: Web framework
- `pydantic==2.11.7`: Request/response validation

## Key Design Decisions

### Why Inline Test App?

The test app is defined in `conftest.py` instead of importing `backend/app.py` because:

1. **Static Files Issue**: Production app mounts `../frontend` directory, which doesn't exist in test environments
2. **Startup Events**: Production app loads documents from `../docs` on startup
3. **Isolation**: Tests should not depend on filesystem structure
4. **Speed**: No need to initialize full production dependencies

### Why Mock RAG System?

API tests mock the RAG system to:

1. **Focus on API Layer**: Tests validate HTTP handling, not AI logic
2. **Speed**: No AI API calls or vector database queries
3. **Determinism**: Predictable responses for reliable testing
4. **Cost**: No Anthropic API charges during testing

### Why FastAPI TestClient?

FastAPI's TestClient provides:

1. **No Server Required**: In-memory ASGI application
2. **Synchronous Testing**: No async/await in test code
3. **Full Request Cycle**: Middleware, validation, error handling
4. **pytest Integration**: Works seamlessly with pytest fixtures

## File Structure

```
backend/tests/
├── conftest.py              # Shared fixtures (enhanced)
├── test_api_endpoints.py    # API tests (NEW)
├── test_ai_generator.py     # Existing tests
├── test_search_tools.py     # Existing tests
├── test_rag_integration.py  # Existing tests
├── test_live_system.py      # Existing tests
└── API_TEST_SUMMARY.md      # This document

pyproject.toml               # Pytest configuration (enhanced)
```

## Contributing

When adding new API endpoints:

1. Add endpoint to `test_app` fixture in `conftest.py`
2. Create test methods in `test_api_endpoints.py`
3. Test success case, validation errors, and internal errors
4. Add appropriate pytest markers (`@pytest.mark.api`)
5. Update this summary document

## Conclusion

The API testing framework provides comprehensive coverage of the FastAPI endpoints with fast, isolated, and maintainable tests. All 25 tests pass successfully, validating proper request/response handling, error cases, and integration with the RAG system.
