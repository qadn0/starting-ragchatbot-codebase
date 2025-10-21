# RAG System Testing Framework

Comprehensive test suite for the Retrieval-Augmented Generation (RAG) system.

## Quick Start

```bash
# Run all tests
uv run pytest tests/ -v

# Run only API tests
uv run pytest tests/test_api_endpoints.py -v

# Run tests by marker
uv run pytest -m api          # API endpoint tests
uv run pytest -m unit         # Unit tests
uv run pytest -m integration  # Integration tests
uv run pytest -m "not slow"   # Exclude slow tests
```

## Test Files

### Core Component Tests

- **`test_ai_generator.py`**: AI/LLM interaction and tool calling
- **`test_search_tools.py`**: Vector search and tool execution
- **`test_rag_integration.py`**: End-to-end RAG pipeline
- **`test_live_system.py`**: Real database integration

### API Tests (NEW)

- **`test_api_endpoints.py`**: FastAPI REST API endpoints
  - 25 comprehensive tests
  - Tests all endpoints: `/`, `/api/query`, `/api/courses`
  - Success cases, error handling, edge cases
  - All tests passing ✅

### Configuration

- **`conftest.py`**: Shared pytest fixtures
- **`../pyproject.toml`**: Pytest configuration and markers

## Test Statistics

- **Total Tests**: 64
- **API Tests**: 25 (all passing)
- **Test Files**: 5
- **Fixtures**: 15+

## Test Markers

Use markers to run specific test categories:

```bash
# API endpoint tests
pytest -m api

# Unit tests (individual components)
pytest -m unit

# Integration tests (component interactions)
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

## API Test Coverage

### Endpoints Tested

1. **`GET /`** - Root endpoint, welcome message
2. **`POST /api/query`** - Query processing with RAG
3. **`GET /api/courses`** - Course statistics

### Test Categories

**TestAPIEndpoints** (17 tests)
- Successful requests
- Session management
- Input validation
- Response validation
- Edge cases (special chars, long text)

**TestAPIErrorHandling** (5 tests)
- HTTP error codes (404, 405, 422, 500)
- Invalid input handling
- Error recovery

**TestAPIIntegrationFlow** (3 tests)
- Complete workflows
- Health checks
- Multi-step interactions

## Running Tests

### Basic Commands

```bash
# All tests
uv run pytest tests/

# Verbose output
uv run pytest tests/ -v

# Stop on first failure
uv run pytest tests/ -x

# Show print statements
uv run pytest tests/ -s

# Run specific file
uv run pytest tests/test_api_endpoints.py

# Run specific test
uv run pytest tests/test_api_endpoints.py::TestAPIEndpoints::test_query_endpoint_success
```

### Coverage Options

```bash
# With coverage report
uv run pytest tests/ --cov=backend --cov-report=term-missing

# HTML coverage report
uv run pytest tests/ --cov=backend --cov-report=html
```

### Useful Flags

- `-v, --verbose`: Detailed test output
- `-x, --exitfirst`: Stop on first failure
- `-s`: Show print statements
- `-k EXPRESSION`: Run tests matching expression
- `--tb=short`: Shorter traceback format
- `--collect-only`: List tests without running

## Writing New Tests

### Test Structure

```python
import pytest

@pytest.mark.api  # Add appropriate marker
class TestNewFeature:
    """Test suite for new feature"""

    def test_success_case(self, client):
        """Test successful operation"""
        response = client.get("/new-endpoint")
        assert response.status_code == 200
        assert "expected" in response.json()

    def test_error_case(self, client):
        """Test error handling"""
        response = client.get("/invalid")
        assert response.status_code == 404
```

### Using Fixtures

Common fixtures available in `conftest.py`:

```python
# Component fixtures
def test_with_vector_store(mock_vector_store):
    """Use mocked vector store"""
    pass

def test_with_rag_system(mock_rag_system):
    """Use mocked RAG system"""
    pass

# API fixtures
def test_api_endpoint(client):
    """Use FastAPI test client"""
    response = client.get("/")
    assert response.status_code == 200

def test_with_test_app(test_app):
    """Access test app directly"""
    pass
```

### Best Practices

1. **Use descriptive names**: `test_query_endpoint_with_invalid_session`
2. **Add docstrings**: Explain what the test validates
3. **Use markers**: `@pytest.mark.api` for categorization
4. **Mock external calls**: AI APIs, databases
5. **Test one thing**: Each test should have a single assertion focus
6. **Clean up**: Use fixtures with teardown for resources

## Fixtures Reference

### Component Fixtures

- `sample_course`: Test course with lessons
- `sample_chunks`: Test course chunks
- `sample_search_results`: Mock search results
- `mock_vector_store`: Mocked VectorStore
- `mock_anthropic_client`: Mocked AI client
- `temp_chroma_db`: Temporary database directory
- `test_config`: Test configuration

### API Fixtures

- `mock_rag_system`: Mocked RAGSystem for API tests
- `test_app`: FastAPI test application
- `client`: FastAPI TestClient for HTTP requests

## Continuous Integration

The test suite is CI/CD ready:

- Fast execution (<10 seconds for full suite)
- No external dependencies (mocked)
- Clear pass/fail output
- Configurable via pytest.ini options
- Warning suppression for clean output

## Troubleshooting

### Import Errors

If you see import errors, ensure you're in the backend directory:

```bash
cd backend
uv run pytest tests/
```

### Missing Dependencies

Install test dependencies:

```bash
uv sync  # Installs all dependencies including dev group
```

### ChromaDB Warnings

ChromaDB warnings are filtered in `pyproject.toml`. To see them:

```bash
uv run pytest tests/ --disable-warnings
```

### Slow Tests

Skip slow tests during development:

```bash
uv run pytest -m "not slow"
```

## Documentation

- **API_TEST_SUMMARY.md**: Detailed API testing documentation
- **FIX_SUMMARY.md**: Historical fixes and improvements
- **TEST_REPORT.md**: Test execution reports
- **DIAGNOSIS.md**: Issue diagnosis and solutions

## Contributing

1. Write tests for new features
2. Add appropriate markers (`@pytest.mark.api`, etc.)
3. Update fixtures in `conftest.py` if needed
4. Run full test suite before committing
5. Update documentation for significant changes

## Test Results

Latest test run (API tests only):

```
tests/test_api_endpoints.py::TestAPIEndpoints::test_root_endpoint PASSED
tests/test_api_endpoints.py::TestAPIEndpoints::test_query_endpoint_success PASSED
... (23 more tests)

============================== 25 passed in 0.63s ==============================
```

All API tests passing! ✅

## Contact

For issues with the testing framework, check:
1. This README
2. API_TEST_SUMMARY.md for API test details
3. conftest.py for fixture definitions
4. pyproject.toml for pytest configuration
