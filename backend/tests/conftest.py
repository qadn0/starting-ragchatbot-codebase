"""Pytest configuration and fixtures for RAG system tests"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock

import pytest
from ai_generator import AIGenerator
from config import Config
from models import Course, CourseChunk, Lesson
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults, VectorStore


@pytest.fixture
def sample_course():
    """Sample course with lessons for testing"""
    return Course(
        title="Introduction to MCP",
        course_link="https://example.com/mcp",
        instructor="John Doe",
        lessons=[
            Lesson(
                lesson_number=1,
                title="Getting Started",
                lesson_link="https://example.com/mcp/lesson1",
            ),
            Lesson(
                lesson_number=2,
                title="Advanced Topics",
                lesson_link="https://example.com/mcp/lesson2",
            ),
        ],
    )


@pytest.fixture
def sample_chunks():
    """Sample course chunks for testing"""
    return [
        CourseChunk(
            content="Lesson 1 content: This is an introduction to MCP. It covers basic concepts.",
            course_title="Introduction to MCP",
            lesson_number=1,
            chunk_index=0,
        ),
        CourseChunk(
            content="MCP stands for Model Context Protocol. It helps with integration.",
            course_title="Introduction to MCP",
            lesson_number=1,
            chunk_index=1,
        ),
        CourseChunk(
            content="Lesson 2 content: Advanced MCP features include streaming and caching.",
            course_title="Introduction to MCP",
            lesson_number=2,
            chunk_index=2,
        ),
    ]


@pytest.fixture
def sample_search_results():
    """Sample search results for testing"""
    return SearchResults(
        documents=[
            "Lesson 1 content: This is an introduction to MCP. It covers basic concepts.",
            "MCP stands for Model Context Protocol. It helps with integration.",
        ],
        metadata=[
            {
                "course_title": "Introduction to MCP",
                "lesson_number": 1,
                "chunk_index": 0,
            },
            {
                "course_title": "Introduction to MCP",
                "lesson_number": 1,
                "chunk_index": 1,
            },
        ],
        distances=[0.1, 0.2],
    )


@pytest.fixture
def empty_search_results():
    """Empty search results for testing"""
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def mock_vector_store(sample_search_results):
    """Mock VectorStore that returns sample results"""
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = sample_search_results
    mock_store.get_lesson_link.return_value = "https://example.com/mcp/lesson1"
    return mock_store


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing AI generator"""
    mock_client = Mock()

    # Create mock response without tool use
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [Mock(text="This is a test response")]

    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_anthropic_client_with_tools():
    """Mock Anthropic client that simulates tool calling"""
    mock_client = Mock()

    # First response: Claude requests to use a tool
    tool_use_response = Mock()
    tool_use_response.stop_reason = "tool_use"

    # Mock tool use content block
    tool_block = Mock()
    tool_block.type = "tool_use"
    tool_block.name = "search_course_content"
    tool_block.id = "tool_123"
    tool_block.input = {"query": "What is MCP?"}

    tool_use_response.content = [tool_block]

    # Second response: Final answer after tool execution
    final_response = Mock()
    final_response.stop_reason = "end_turn"
    final_response.content = [Mock(text="MCP stands for Model Context Protocol.")]

    # Return different responses on consecutive calls
    mock_client.messages.create.side_effect = [tool_use_response, final_response]

    return mock_client


@pytest.fixture
def temp_chroma_db():
    """Create a temporary ChromaDB directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_config(temp_chroma_db):
    """Test configuration with temporary database"""
    config = Config()
    config.CHROMA_PATH = temp_chroma_db
    config.MAX_RESULTS = 5  # Ensure non-zero for tests
    config.ANTHROPIC_API_KEY = "test-key-123"
    return config


@pytest.fixture
def real_vector_store(temp_chroma_db, sample_course, sample_chunks):
    """Real VectorStore instance with test data"""
    store = VectorStore(
        chroma_path=temp_chroma_db, embedding_model="all-MiniLM-L6-v2", max_results=5
    )

    # Add test data
    store.add_course_metadata(sample_course)
    store.add_course_content(sample_chunks)

    return store


@pytest.fixture
def search_tool(mock_vector_store):
    """CourseSearchTool with mock vector store"""
    return CourseSearchTool(mock_vector_store)


@pytest.fixture
def tool_manager(search_tool):
    """ToolManager with registered search tool"""
    manager = ToolManager()
    manager.register_tool(search_tool)
    return manager


# ============================================================================
# API Testing Fixtures
# ============================================================================

@pytest.fixture
def mock_rag_system():
    """Mock RAGSystem for API testing"""
    mock_rag = Mock()

    # Mock query method to return predictable responses
    mock_rag.query.return_value = (
        "This is a test answer about MCP.",
        [{"text": "Introduction to MCP - Lesson 1", "link": "https://example.com/lesson1"}]
    )

    # Mock get_course_analytics method
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Introduction to MCP", "Advanced Python"]
    }

    # Mock session manager
    mock_rag.session_manager.create_session.return_value = "test_session_123"

    return mock_rag


@pytest.fixture
def test_app(mock_rag_system):
    """FastAPI test application without static file mounting"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional, Dict, Any

    # Create a minimal app for testing
    app = FastAPI(title="Course Materials RAG System - Test")

    # Add CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Pydantic models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Dict[str, Any]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # API endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id or mock_rag_system.session_manager.create_session()
            answer, sources = mock_rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        return {"message": "RAG System API"}

    return app


@pytest.fixture
def client(test_app):
    """Test client for making API requests"""
    from fastapi.testclient import TestClient
    return TestClient(test_app)
