"""Integration tests for RAG system query handling"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rag_system import RAGSystem
from config import Config
from vector_store import SearchResults
from models import Course, Lesson, CourseChunk


class TestRAGIntegration:
    """Integration tests for the full RAG query flow"""

    @pytest.fixture
    def mock_config(self):
        """Create test config"""
        config = Mock(spec=Config)
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "./test_chroma_db"
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        config.MAX_RESULTS = 5
        config.ANTHROPIC_API_KEY = "test_key"
        config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
        config.MAX_HISTORY = 2
        config.MAX_TOOL_ROUNDS = 2
        return config

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store"""
        with patch('rag_system.VectorStore') as MockVectorStore:
            mock_store = Mock()
            MockVectorStore.return_value = mock_store
            yield mock_store

    @pytest.fixture
    def mock_ai_generator(self):
        """Create mock AI generator"""
        with patch('rag_system.AIGenerator') as MockAIGenerator:
            mock_gen = Mock()
            MockAIGenerator.return_value = mock_gen
            yield mock_gen

    @pytest.fixture
    def rag_system(self, mock_config, mock_vector_store, mock_ai_generator):
        """Create RAG system with mocked dependencies"""
        with patch('rag_system.DocumentProcessor'):
            with patch('rag_system.SessionManager'):
                system = RAGSystem(mock_config)
                system.vector_store = mock_vector_store
                system.ai_generator = mock_ai_generator
                return system

    def test_query_with_course_content_question(self, rag_system, mock_ai_generator):
        """Test querying course content (should trigger tool use)"""
        # Mock AI response
        mock_ai_generator.generate_response.return_value = "MCP stands for Model Context Protocol"

        # Mock sources from tool
        rag_system.tool_manager.get_last_sources = Mock(return_value=[
            {"text": "Introduction to MCP - Lesson 1", "link": "https://example.com/lesson1"}
        ])

        answer, sources = rag_system.query("What is MCP?")

        # Verify AI was called with tools
        assert mock_ai_generator.generate_response.called
        call_args = mock_ai_generator.generate_response.call_args
        
        # Should include query
        assert "What is MCP?" in call_args.kwargs['query']
        
        # Should have tools available
        assert call_args.kwargs['tools'] is not None
        assert call_args.kwargs['tool_manager'] is not None

        # Verify response
        assert answer == "MCP stands for Model Context Protocol"
        assert len(sources) == 1
        assert sources[0]["text"] == "Introduction to MCP - Lesson 1"

    def test_query_with_general_knowledge_question(self, rag_system, mock_ai_generator):
        """Test querying general knowledge (Claude may not use tools)"""
        # Mock AI decides not to use tools
        mock_ai_generator.generate_response.return_value = "Python is a programming language"
        
        # No sources from tool
        rag_system.tool_manager.get_last_sources = Mock(return_value=[])

        answer, sources = rag_system.query("What is Python?")

        # Should still call AI with tools available (Claude decides not to use them)
        assert mock_ai_generator.generate_response.called
        
        # Verify response
        assert answer == "Python is a programming language"
        assert len(sources) == 0

    def test_query_with_session_id(self, rag_system, mock_ai_generator):
        """Test query with session for conversation context"""
        session_id = "test_session_123"
        
        # Mock session manager
        mock_history = "User: Previous question\nAssistant: Previous answer"
        rag_system.session_manager.get_conversation_history = Mock(return_value=mock_history)
        rag_system.session_manager.add_exchange = Mock()

        mock_ai_generator.generate_response.return_value = "Follow-up answer"
        rag_system.tool_manager.get_last_sources = Mock(return_value=[])

        answer, sources = rag_system.query("Follow up question", session_id=session_id)

        # Verify history was retrieved
        rag_system.session_manager.get_conversation_history.assert_called_once_with(session_id)

        # Verify history was passed to AI
        call_args = mock_ai_generator.generate_response.call_args
        assert call_args.kwargs['conversation_history'] == mock_history

        # Verify exchange was saved
        rag_system.session_manager.add_exchange.assert_called_once_with(
            session_id, "Follow up question", "Follow-up answer"
        )

    def test_query_without_session_id(self, rag_system, mock_ai_generator):
        """Test query without session (no history)"""
        mock_ai_generator.generate_response.return_value = "Answer"
        rag_system.tool_manager.get_last_sources = Mock(return_value=[])

        answer, sources = rag_system.query("Question")

        # Verify no history passed
        call_args = mock_ai_generator.generate_response.call_args
        assert call_args.kwargs['conversation_history'] is None

    def test_query_tool_flow(self, rag_system, mock_ai_generator, mock_vector_store):
        """Test that query sets up tools correctly"""
        mock_ai_generator.generate_response.return_value = "Answer"
        rag_system.tool_manager.get_last_sources = Mock(return_value=[])

        answer, sources = rag_system.query("Test query")

        # Verify tools were passed
        call_args = mock_ai_generator.generate_response.call_args
        tools = call_args.kwargs['tools']
        
        # Should have both search and outline tools
        assert len(tools) == 2
        tool_names = [t["name"] for t in tools]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names

    def test_query_sources_reset_after_retrieval(self, rag_system, mock_ai_generator):
        """Test that sources are reset after being retrieved"""
        mock_ai_generator.generate_response.return_value = "Answer"
        
        # Mock sources
        mock_sources = [{"text": "Source 1", "link": "link1"}]
        rag_system.tool_manager.get_last_sources = Mock(return_value=mock_sources)
        rag_system.tool_manager.reset_sources = Mock()

        answer, sources = rag_system.query("Test")

        # Verify sources were retrieved
        rag_system.tool_manager.get_last_sources.assert_called_once()

        # Verify sources were reset
        rag_system.tool_manager.reset_sources.assert_called_once()

    def test_search_tool_integration_with_vector_store(self, rag_system, mock_vector_store):
        """Test that search tool correctly uses vector store"""
        # Setup mock vector store search results
        mock_results = SearchResults(
            documents=["Test content"],
            metadata=[{'course_title': 'Test Course', 'lesson_number': 1}],
            distances=[0.5],
            error=None
        )
        mock_vector_store.search.return_value = mock_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com"

        # Execute search through tool manager
        result = rag_system.tool_manager.execute_tool(
            "search_course_content",
            query="test query"
        )

        # Verify vector store was called
        mock_vector_store.search.assert_called_once_with(
            query="test query",
            course_name=None,
            lesson_number=None
        )

        # Verify result is formatted
        assert "Test Course" in result
        assert "Test content" in result

    def test_outline_tool_integration(self, rag_system, mock_vector_store):
        """Test that outline tool works correctly"""
        # Setup mock course catalog
        mock_vector_store._resolve_course_name.return_value = "Test Course"
        mock_vector_store.course_catalog.get.return_value = {
            'metadatas': [{
                'title': 'Test Course',
                'course_link': 'https://example.com/course',
                'instructor': 'John Doe',
                'lessons_json': '[{"lesson_number": 1, "lesson_title": "Intro"}]'
            }]
        }

        # Execute outline tool
        result = rag_system.tool_manager.execute_tool(
            "get_course_outline",
            course_name="Test"
        )

        # Verify result contains course info
        assert "Test Course" in result
        assert "John Doe" in result
        assert "Lesson 1: Intro" in result

    def test_query_handles_no_results(self, rag_system, mock_ai_generator, mock_vector_store):
        """Test query handling when search returns no results"""
        # Mock AI to use search tool that returns nothing
        mock_ai_generator.generate_response.return_value = "I couldn't find information on that topic"
        rag_system.tool_manager.get_last_sources = Mock(return_value=[])

        answer, sources = rag_system.query("nonexistent topic")

        assert "couldn't find" in answer.lower()
        assert len(sources) == 0

    def test_full_query_flow_simulation(self, mock_config):
        """Test a simulated full query flow with real tool interactions"""
        # This test uses real tool classes but mocks external dependencies
        with patch('rag_system.VectorStore') as MockVectorStore:
            with patch('rag_system.AIGenerator') as MockAIGenerator:
                with patch('rag_system.DocumentProcessor'):
                    with patch('rag_system.SessionManager'):
                        # Setup mocks
                        mock_store = Mock()
                        MockVectorStore.return_value = mock_store
                        
                        mock_ai = Mock()
                        MockAIGenerator.return_value = mock_ai

                        # Create RAG system
                        rag = RAGSystem(mock_config)

                        # Simulate vector store search
                        mock_results = SearchResults(
                            documents=["MCP is a protocol for context"],
                            metadata=[{'course_title': 'Intro to MCP', 'lesson_number': 1}],
                            distances=[0.3],
                            error=None
                        )
                        mock_store.search.return_value = mock_results
                        mock_store.get_lesson_link.return_value = "https://example.com/lesson1"

                        # Simulate AI response
                        mock_ai.generate_response.return_value = "MCP (Model Context Protocol) is a protocol for managing context"

                        # Execute query
                        answer, sources = rag.query("What is MCP?")

                        # Verify the flow
                        assert mock_ai.generate_response.called
                        assert "MCP" in answer
                        
                        # Sources should be populated from search results
                        # Note: sources come from tool execution during AI generation
                        # In real flow, AI would call the tool, which would populate last_sources


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
