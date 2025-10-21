"""Tests for CourseSearchTool.execute() method"""

import os
import sys
from unittest.mock import MagicMock, Mock

import pytest

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Course, Lesson
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults, VectorStore


class TestCourseSearchTool:
    """Test suite for CourseSearchTool.execute() method"""

    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock VectorStore"""
        mock_store = Mock(spec=VectorStore)
        return mock_store

    @pytest.fixture
    def search_tool(self, mock_vector_store):
        """Create CourseSearchTool with mock store"""
        return CourseSearchTool(mock_vector_store)

    def test_tool_definition(self, search_tool):
        """Test that tool definition is correctly formatted"""
        tool_def = search_tool.get_tool_definition()

        assert tool_def["name"] == "search_course_content"
        assert "description" in tool_def
        assert "input_schema" in tool_def
        assert tool_def["input_schema"]["required"] == ["query"]
        assert "query" in tool_def["input_schema"]["properties"]
        assert "course_name" in tool_def["input_schema"]["properties"]
        assert "lesson_number" in tool_def["input_schema"]["properties"]

    def test_execute_successful_search(self, search_tool, mock_vector_store):
        """Test execute with successful search results"""
        # Mock successful search results
        mock_results = SearchResults(
            documents=["This is content about MCP"],
            metadata=[{"course_title": "Introduction to MCP", "lesson_number": 1}],
            distances=[0.5],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"

        # Execute search
        result = search_tool.execute(query="What is MCP?")

        # Verify search was called
        mock_vector_store.search.assert_called_once_with(
            query="What is MCP?", course_name=None, lesson_number=None
        )

        # Verify result is formatted correctly
        assert "[Introduction to MCP - Lesson 1]" in result
        assert "This is content about MCP" in result

        # Verify sources are tracked
        assert len(search_tool.last_sources) == 1
        assert search_tool.last_sources[0]["text"] == "Introduction to MCP - Lesson 1"
        assert search_tool.last_sources[0]["link"] == "https://example.com/lesson1"

    def test_execute_with_course_filter(self, search_tool, mock_vector_store):
        """Test execute with course_name parameter"""
        mock_results = SearchResults(
            documents=["Content about fastapi"],
            metadata=[{"course_title": "FastAPI Course", "lesson_number": 2}],
            distances=[0.3],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results
        mock_vector_store.get_lesson_link.return_value = None

        result = search_tool.execute(query="How to use FastAPI?", course_name="FastAPI")

        # Verify search was called with course_name
        mock_vector_store.search.assert_called_once_with(
            query="How to use FastAPI?", course_name="FastAPI", lesson_number=None
        )

        assert "FastAPI Course" in result

    def test_execute_with_lesson_filter(self, search_tool, mock_vector_store):
        """Test execute with lesson_number parameter"""
        mock_results = SearchResults(
            documents=["Lesson 3 content"],
            metadata=[{"course_title": "Python Basics", "lesson_number": 3}],
            distances=[0.2],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson3"

        result = search_tool.execute(
            query="loops", course_name="Python", lesson_number=3
        )

        # Verify search was called with both filters
        mock_vector_store.search.assert_called_once_with(
            query="loops", course_name="Python", lesson_number=3
        )

        assert "Python Basics" in result
        assert "Lesson 3" in result

    def test_execute_with_error(self, search_tool, mock_vector_store):
        """Test execute when vector store returns an error"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="No course found matching 'NonExistent'",
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="test", course_name="NonExistent")

        # Should return the error message
        assert result == "No course found matching 'NonExistent'"

    def test_execute_with_empty_results(self, search_tool, mock_vector_store):
        """Test execute when no results are found"""
        mock_results = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="nonexistent topic")

        assert "No relevant content found" in result

    def test_execute_empty_results_with_filters(self, search_tool, mock_vector_store):
        """Test execute with empty results and filter info"""
        mock_results = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="test", course_name="MCP", lesson_number=5)

        assert "No relevant content found" in result
        assert "course 'MCP'" in result
        assert "lesson 5" in result

    def test_format_results_without_lesson_number(self, search_tool, mock_vector_store):
        """Test formatting when metadata doesn't have lesson_number"""
        mock_results = SearchResults(
            documents=["General course info"],
            metadata=[{"course_title": "Test Course"}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results
        mock_vector_store.get_lesson_link.return_value = None

        result = search_tool.execute(query="info")

        # Should not include "Lesson" in header
        assert "[Test Course]" in result
        assert "Lesson" not in result.split("\n")[0]

        # Source should not have lesson number
        assert search_tool.last_sources[0]["text"] == "Test Course"
        assert search_tool.last_sources[0]["link"] is None

    def test_multiple_results(self, search_tool, mock_vector_store):
        """Test formatting with multiple search results"""
        mock_results = SearchResults(
            documents=["Content 1", "Content 2", "Content 3"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
                {"course_title": "Course A", "lesson_number": 3},
            ],
            distances=[0.1, 0.2, 0.3],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com"

        result = search_tool.execute(query="test")

        # Should have all three results
        assert "Content 1" in result
        assert "Content 2" in result
        assert "Content 3" in result

        # Should have three sources
        assert len(search_tool.last_sources) == 3


class TestToolManager:
    """Test suite for ToolManager"""

    @pytest.fixture
    def tool_manager(self):
        """Create ToolManager instance"""
        return ToolManager()

    @pytest.fixture
    def mock_tool(self):
        """Create a mock tool"""
        tool = Mock()
        tool.get_tool_definition.return_value = {
            "name": "mock_tool",
            "description": "A mock tool",
        }
        tool.execute.return_value = "mock result"
        return tool

    def test_register_tool(self, tool_manager, mock_tool):
        """Test registering a tool"""
        tool_manager.register_tool(mock_tool)

        assert "mock_tool" in tool_manager.tools
        assert tool_manager.tools["mock_tool"] == mock_tool

    def test_get_tool_definitions(self, tool_manager, mock_tool):
        """Test getting all tool definitions"""
        tool_manager.register_tool(mock_tool)

        definitions = tool_manager.get_tool_definitions()

        assert len(definitions) == 1
        assert definitions[0]["name"] == "mock_tool"

    def test_execute_tool(self, tool_manager, mock_tool):
        """Test executing a registered tool"""
        tool_manager.register_tool(mock_tool)

        result = tool_manager.execute_tool("mock_tool", param="value")

        mock_tool.execute.assert_called_once_with(param="value")
        assert result == "mock result"

    def test_execute_nonexistent_tool(self, tool_manager):
        """Test executing a tool that doesn't exist"""
        result = tool_manager.execute_tool("nonexistent")

        assert "not found" in result

    def test_get_last_sources(self, tool_manager):
        """Test getting sources from search tool"""
        mock_search_tool = Mock()
        mock_search_tool.get_tool_definition.return_value = {
            "name": "search",
            "description": "Search",
        }
        mock_search_tool.last_sources = [{"text": "Source 1", "link": "link1"}]

        tool_manager.register_tool(mock_search_tool)

        sources = tool_manager.get_last_sources()
        assert len(sources) == 1
        assert sources[0]["text"] == "Source 1"

    def test_reset_sources(self, tool_manager):
        """Test resetting sources"""
        mock_search_tool = Mock()
        mock_search_tool.get_tool_definition.return_value = {
            "name": "search",
            "description": "Search",
        }
        mock_search_tool.last_sources = [{"text": "Source 1", "link": "link1"}]

        tool_manager.register_tool(mock_search_tool)
        tool_manager.reset_sources()

        assert mock_search_tool.last_sources == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
