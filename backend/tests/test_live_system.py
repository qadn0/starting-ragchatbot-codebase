"""Live system test to diagnose actual query failures"""

import pytest
import sys
import os
from unittest.mock import patch, Mock

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import config
from rag_system import RAGSystem
from vector_store import VectorStore


def test_vector_store_has_data():
    """Test that vector store actually has course data"""
    vector_store = VectorStore(
        chroma_path=config.CHROMA_PATH,
        embedding_model=config.EMBEDDING_MODEL,
        max_results=config.MAX_RESULTS
    )
    
    # Check course count
    course_count = vector_store.get_course_count()
    print(f"\n✓ Course count: {course_count}")
    assert course_count > 0, "No courses found in vector store!"
    
    # Get course titles
    titles = vector_store.get_existing_course_titles()
    print(f"✓ Course titles: {titles}")
    assert len(titles) > 0, "No course titles found!"
    

def test_vector_store_search_works():
    """Test that vector store search actually returns results"""
    vector_store = VectorStore(
        chroma_path=config.CHROMA_PATH,
        embedding_model=config.EMBEDDING_MODEL,
        max_results=config.MAX_RESULTS
    )
    
    # Try a simple search
    results = vector_store.search(query="What is computer use?")
    
    print(f"\n✓ Search returned {len(results.documents)} results")
    print(f"✓ Error: {results.error}")
    
    if results.documents:
        print(f"✓ First result preview: {results.documents[0][:100]}...")
        print(f"✓ First result metadata: {results.metadata[0]}")
    
    assert not results.error, f"Search returned error: {results.error}"
    assert len(results.documents) > 0, "Search returned no results!"


def test_search_tool_execute_with_real_data():
    """Test CourseSearchTool.execute() with real vector store"""
    from search_tools import CourseSearchTool
    
    vector_store = VectorStore(
        chroma_path=config.CHROMA_PATH,
        embedding_model=config.EMBEDDING_MODEL,
        max_results=config.MAX_RESULTS
    )
    
    search_tool = CourseSearchTool(vector_store)
    
    # Execute a search
    result = search_tool.execute(query="What is computer use?")
    
    print(f"\n✓ Search tool result length: {len(result)}")
    print(f"✓ Search tool result preview: {result[:200]}...")
    
    assert isinstance(result, str), "Result should be a string"
    assert len(result) > 0, "Result should not be empty"
    assert "No relevant content found" not in result, "Search should find content"


def test_tool_manager_integration():
    """Test that ToolManager correctly registers and executes tools"""
    from search_tools import ToolManager, CourseSearchTool
    
    vector_store = VectorStore(
        chroma_path=config.CHROMA_PATH,
        embedding_model=config.EMBEDDING_MODEL,
        max_results=config.MAX_RESULTS
    )
    
    tool_manager = ToolManager()
    search_tool = CourseSearchTool(vector_store)
    tool_manager.register_tool(search_tool)
    
    # Get tool definitions
    definitions = tool_manager.get_tool_definitions()
    print(f"\n✓ Tool definitions count: {len(definitions)}")
    print(f"✓ Tool names: {[t['name'] for t in definitions]}")
    
    assert len(definitions) > 0, "No tool definitions found"
    assert any(t['name'] == 'search_course_content' for t in definitions), "Search tool not registered"
    
    # Execute tool
    result = tool_manager.execute_tool(
        "search_course_content",
        query="What is computer use?"
    )
    
    print(f"✓ Execute result preview: {result[:200]}...")
    
    assert isinstance(result, str), "Result should be a string"
    assert len(result) > 0, "Result should not be empty"


def test_rag_system_query_with_mock_ai():
    """Test RAG system query with mocked AI to see if tools are being called"""
    
    # Mock only the AI generator, keep everything else real
    with patch('rag_system.AIGenerator') as MockAI:
        mock_ai_instance = Mock()
        
        # Track what parameters are passed to AI
        def capture_generate_response(*args, **kwargs):
            print("\n✓ AI generate_response called with:")
            print(f"  - query: {kwargs.get('query', 'N/A')[:100]}...")
            print(f"  - tools provided: {kwargs.get('tools') is not None}")
            if kwargs.get('tools'):
                print(f"  - tool count: {len(kwargs.get('tools', []))}")
                print(f"  - tool names: {[t['name'] for t in kwargs.get('tools', [])]}")
            print(f"  - tool_manager provided: {kwargs.get('tool_manager') is not None}")
            
            # Simulate AI calling the search tool
            if kwargs.get('tool_manager') and kwargs.get('tools'):
                print("\n  → Simulating AI calling search tool...")
                try:
                    tool_result = kwargs['tool_manager'].execute_tool(
                        'search_course_content',
                        query='What is computer use?'
                    )
                    print(f"  → Tool returned: {tool_result[:100]}...")
                except Exception as e:
                    print(f"  → Tool execution error: {e}")
            
            return "Mock AI response based on tool results"
        
        mock_ai_instance.generate_response = Mock(side_effect=capture_generate_response)
        MockAI.return_value = mock_ai_instance
        
        # Create RAG system
        rag_system = RAGSystem(config)
        
        # Execute query
        answer, sources = rag_system.query("What is computer use?")
        
        print(f"\n✓ Final answer: {answer}")
        print(f"✓ Sources count: {len(sources)}")
        if sources:
            print(f"✓ Sources: {sources}")
        
        # Verify AI was called with tools
        assert mock_ai_instance.generate_response.called
        call_kwargs = mock_ai_instance.generate_response.call_args.kwargs
        assert call_kwargs['tools'] is not None, "Tools not passed to AI!"
        assert call_kwargs['tool_manager'] is not None, "Tool manager not passed to AI!"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
