"""Tests for AIGenerator tool calling functionality"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_generator import AIGenerator
from search_tools import ToolManager, CourseSearchTool


class TestAIGeneratorToolCalling:
    """Test suite for AIGenerator tool calling behavior"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client"""
        with patch('ai_generator.anthropic.Anthropic') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def ai_generator(self, mock_anthropic_client):
        """Create AIGenerator with mock client"""
        generator = AIGenerator(
            api_key="test_key",
            model="claude-sonnet-4-20250514",
            max_tool_rounds=2
        )
        generator.client = mock_anthropic_client
        return generator

    @pytest.fixture
    def mock_tool_manager(self):
        """Create a mock ToolManager"""
        manager = Mock(spec=ToolManager)
        manager.execute_tool.return_value = "[Course A]\nSome search results"
        return manager

    @pytest.fixture
    def sample_tools(self):
        """Sample tool definitions"""
        return [{
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }]

    def test_generate_response_without_tools(self, ai_generator, mock_anthropic_client):
        """Test basic response generation without tools"""
        # Mock response without tool use
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(type="text", text="This is a general answer")]
        
        mock_anthropic_client.messages.create.return_value = mock_response

        result = ai_generator.generate_response(
            query="What is Python?",
            conversation_history=None,
            tools=None,
            tool_manager=None
        )

        assert result == "This is a general answer"
        assert mock_anthropic_client.messages.create.call_count == 1

    def test_generate_response_with_tool_use(self, ai_generator, mock_anthropic_client, 
                                             mock_tool_manager, sample_tools):
        """Test response generation when Claude calls a tool"""
        # First response: Claude requests tool use
        tool_use_response = Mock()
        tool_use_response.stop_reason = "tool_use"
        tool_use_content = Mock(
            type="tool_use",
            id="tool_123",
            name="search_course_content",
            input={"query": "What is MCP?"}
        )
        tool_use_response.content = [tool_use_content]

        # Second response: Claude provides answer with tool results
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(type="text", text="MCP stands for Model Context Protocol")]

        mock_anthropic_client.messages.create.side_effect = [
            tool_use_response,
            final_response
        ]

        result = ai_generator.generate_response(
            query="What is MCP?",
            conversation_history=None,
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="What is MCP?"
        )

        # Verify final answer
        assert result == "MCP stands for Model Context Protocol"

        # Verify two API calls were made
        assert mock_anthropic_client.messages.create.call_count == 2

    def test_generate_response_no_tool_use(self, ai_generator, mock_anthropic_client,
                                          mock_tool_manager, sample_tools):
        """Test when Claude decides not to use tools"""
        # Claude responds directly without using tools
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(type="text", text="This is common knowledge")]

        mock_anthropic_client.messages.create.return_value = mock_response

        result = ai_generator.generate_response(
            query="What is 2+2?",
            conversation_history=None,
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Tool should not be executed
        mock_tool_manager.execute_tool.assert_not_called()

        # Should get direct answer
        assert result == "This is common knowledge"

        # Only one API call
        assert mock_anthropic_client.messages.create.call_count == 1

    def test_tool_execution_error_handling(self, ai_generator, mock_anthropic_client,
                                          mock_tool_manager, sample_tools):
        """Test handling of tool execution errors"""
        # First response: tool use
        tool_use_response = Mock()
        tool_use_response.stop_reason = "tool_use"
        tool_use_content = Mock(
            type="tool_use",
            id="tool_123",
            name="search_course_content",
            input={"query": "test"}
        )
        tool_use_response.content = [tool_use_content]

        # Tool execution raises an exception
        mock_tool_manager.execute_tool.side_effect = Exception("Database error")

        # Second response: Claude handles error
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(type="text", text="I couldn't find that information")]

        mock_anthropic_client.messages.create.side_effect = [
            tool_use_response,
            final_response
        ]

        result = ai_generator.generate_response(
            query="test query",
            conversation_history=None,
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Should still return a response
        assert result == "I couldn't find that information"

    def test_max_tool_rounds_reached(self, ai_generator, mock_anthropic_client,
                                    mock_tool_manager, sample_tools):
        """Test behavior when max tool rounds is reached"""
        # Both calls result in tool use (max_tool_rounds=2)
        tool_use_response = Mock()
        tool_use_response.stop_reason = "tool_use"
        tool_use_content = Mock(
            type="tool_use",
            id="tool_123",
            name="search_course_content",
            input={"query": "test"}
        )
        tool_use_response.content = [tool_use_content]

        # Final call without tools forces answer
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(type="text", text="Based on available information...")]

        mock_anthropic_client.messages.create.side_effect = [
            tool_use_response,  # Round 1
            tool_use_response,  # Round 2
            final_response      # Final call without tools
        ]

        result = ai_generator.generate_response(
            query="complex query",
            conversation_history=None,
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Should make 3 calls: 2 with tools + 1 final without tools
        assert mock_anthropic_client.messages.create.call_count == 3

        # Should get final answer
        assert result == "Based on available information..."

    def test_conversation_history_included(self, ai_generator, mock_anthropic_client,
                                          mock_tool_manager, sample_tools):
        """Test that conversation history is included in system prompt"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(type="text", text="Context-aware response")]

        mock_anthropic_client.messages.create.return_value = mock_response

        history = "User: What is MCP?\nAssistant: MCP stands for Model Context Protocol."

        result = ai_generator.generate_response(
            query="Tell me more about it",
            conversation_history=history,
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Check that system prompt includes history
        call_args = mock_anthropic_client.messages.create.call_args
        system_content = call_args.kwargs.get('system', '')
        
        assert "Previous conversation" in system_content
        assert history in system_content

    def test_extract_text_response_with_multiple_blocks(self, ai_generator):
        """Test extracting text from response with multiple content blocks"""
        mock_response = Mock()
        mock_response.content = [
            Mock(type="thinking", text="Let me think..."),
            Mock(type="text", text="Here is the answer"),
            Mock(type="metadata", data={})
        ]

        result = ai_generator._extract_text_response(mock_response)

        # Should extract the text block
        assert result == "Here is the answer"

    def test_extract_text_response_no_text(self, ai_generator):
        """Test extracting text when no text block exists"""
        mock_response = Mock()
        mock_response.content = [
            Mock(type="metadata", data={})
        ]

        result = ai_generator._extract_text_response(mock_response)

        # Should return fallback message
        assert "couldn't generate a response" in result

    def test_tool_parameters_passed_correctly(self, ai_generator, mock_anthropic_client,
                                              mock_tool_manager, sample_tools):
        """Test that tool parameters are passed correctly"""
        tool_use_response = Mock()
        tool_use_response.stop_reason = "tool_use"
        tool_use_content = Mock(
            type="tool_use",
            id="tool_123",
            name="search_course_content",
            input={
                "query": "FastAPI basics",
                "course_name": "FastAPI Course",
                "lesson_number": 2
            }
        )
        tool_use_response.content = [tool_use_content]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(type="text", text="Answer")]

        mock_anthropic_client.messages.create.side_effect = [
            tool_use_response,
            final_response
        ]

        result = ai_generator.generate_response(
            query="test",
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Verify all parameters were passed to execute_tool
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="FastAPI basics",
            course_name="FastAPI Course",
            lesson_number=2
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
