"""Pytest configuration and fixtures for RAG system tests"""
import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any
import tempfile
import shutil
from pathlib import Path

from models import Course, Lesson, CourseChunk
from vector_store import VectorStore, SearchResults
from search_tools import CourseSearchTool, ToolManager
from ai_generator import AIGenerator
from config import Config


@pytest.fixture
def sample_course():
    """Sample course with lessons for testing"""
    return Course(
        title="Introduction to MCP",
        course_link="https://example.com/mcp",
        instructor="John Doe",
        lessons=[
            Lesson(lesson_number=1, title="Getting Started", lesson_link="https://example.com/mcp/lesson1"),
            Lesson(lesson_number=2, title="Advanced Topics", lesson_link="https://example.com/mcp/lesson2")
        ]
    )


@pytest.fixture
def sample_chunks():
    """Sample course chunks for testing"""
    return [
        CourseChunk(
            content="Lesson 1 content: This is an introduction to MCP. It covers basic concepts.",
            course_title="Introduction to MCP",
            lesson_number=1,
            chunk_index=0
        ),
        CourseChunk(
            content="MCP stands for Model Context Protocol. It helps with integration.",
            course_title="Introduction to MCP",
            lesson_number=1,
            chunk_index=1
        ),
        CourseChunk(
            content="Lesson 2 content: Advanced MCP features include streaming and caching.",
            course_title="Introduction to MCP",
            lesson_number=2,
            chunk_index=2
        )
    ]


@pytest.fixture
def sample_search_results():
    """Sample search results for testing"""
    return SearchResults(
        documents=[
            "Lesson 1 content: This is an introduction to MCP. It covers basic concepts.",
            "MCP stands for Model Context Protocol. It helps with integration."
        ],
        metadata=[
            {"course_title": "Introduction to MCP", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "Introduction to MCP", "lesson_number": 1, "chunk_index": 1}
        ],
        distances=[0.1, 0.2]
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
        chroma_path=temp_chroma_db,
        embedding_model="all-MiniLM-L6-v2",
        max_results=5
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
