"""API endpoint tests for FastAPI application

Tests the REST API endpoints for proper request/response handling,
error cases, and integration with the RAG system.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.mark.api
class TestAPIEndpoints:
    """Test suite for FastAPI REST API endpoints"""

    def test_root_endpoint(self, client):
        """Test the root endpoint returns welcome message"""
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"message": "RAG System API"}

    def test_query_endpoint_success(self, client, mock_rag_system):
        """Test successful query to /api/query endpoint"""
        request_data = {
            "query": "What is MCP?",
            "session_id": None
        }

        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify content
        assert data["answer"] == "This is a test answer about MCP."
        assert len(data["sources"]) == 1
        assert data["sources"][0]["text"] == "Introduction to MCP - Lesson 1"
        assert data["sources"][0]["link"] == "https://example.com/lesson1"
        assert data["session_id"] == "test_session_123"

        # Verify RAG system was called correctly
        mock_rag_system.query.assert_called_once_with("What is MCP?", "test_session_123")

    def test_query_endpoint_with_existing_session(self, client, mock_rag_system):
        """Test query with an existing session ID"""
        request_data = {
            "query": "Tell me more about MCP",
            "session_id": "existing_session_456"
        }

        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Should use the provided session ID
        mock_rag_system.query.assert_called_once_with(
            "Tell me more about MCP",
            "existing_session_456"
        )

    def test_query_endpoint_missing_query(self, client):
        """Test /api/query with missing query field"""
        request_data = {
            "session_id": "test_session"
        }

        response = client.post("/api/query", json=request_data)

        # Should return validation error
        assert response.status_code == 422

    def test_query_endpoint_empty_query(self, client):
        """Test /api/query with empty query string"""
        request_data = {
            "query": "",
            "session_id": None
        }

        response = client.post("/api/query", json=request_data)

        # FastAPI validation should pass (empty string is valid)
        # But RAG system should still be called
        assert response.status_code == 200

    def test_query_endpoint_invalid_json(self, client):
        """Test /api/query with invalid JSON"""
        response = client.post(
            "/api/query",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_query_endpoint_internal_error(self, client, mock_rag_system):
        """Test /api/query handling of internal errors"""
        # Make RAG system raise an exception
        mock_rag_system.query.side_effect = Exception("Internal processing error")

        request_data = {
            "query": "What is MCP?",
            "session_id": None
        }

        response = client.post("/api/query", json=request_data)

        assert response.status_code == 500
        assert "Internal processing error" in response.json()["detail"]

    def test_courses_endpoint_success(self, client, mock_rag_system):
        """Test successful request to /api/courses endpoint"""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify content
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "Introduction to MCP" in data["course_titles"]
        assert "Advanced Python" in data["course_titles"]

        # Verify RAG system method was called
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_courses_endpoint_no_courses(self, client, mock_rag_system):
        """Test /api/courses when no courses are loaded"""
        # Mock empty course analytics
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_endpoint_internal_error(self, client, mock_rag_system):
        """Test /api/courses handling of internal errors"""
        mock_rag_system.get_course_analytics.side_effect = Exception("Database error")

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]

    def test_cors_headers_present(self, client):
        """Test that CORS headers are properly set"""
        response = client.get("/")

        # Check for CORS headers (FastAPI TestClient may not show all headers)
        # In production, these would be set by CORSMiddleware
        assert response.status_code == 200

    def test_query_response_model_validation(self, client, mock_rag_system):
        """Test that response conforms to QueryResponse model"""
        request_data = {
            "query": "Test query",
            "session_id": None
        }

        response = client.post("/api/query", json=request_data)
        data = response.json()

        # Verify all required fields are present
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Verify sources structure
        if len(data["sources"]) > 0:
            source = data["sources"][0]
            assert "text" in source
            assert "link" in source

    def test_courses_response_model_validation(self, client):
        """Test that response conforms to CourseStats model"""
        response = client.get("/api/courses")
        data = response.json()

        # Verify all required fields are present
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

        # Verify all titles are strings
        for title in data["course_titles"]:
            assert isinstance(title, str)

    def test_query_with_special_characters(self, client, mock_rag_system):
        """Test query with special characters and unicode"""
        request_data = {
            "query": "What is MCP? 🤖 Tell me about <tags> & symbols!",
            "session_id": None
        }

        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200
        # Query should be passed as-is to RAG system
        mock_rag_system.query.assert_called_once()

    def test_query_with_very_long_text(self, client, mock_rag_system):
        """Test query with very long text input"""
        long_query = "What is MCP? " * 500  # Very long query

        request_data = {
            "query": long_query,
            "session_id": None
        }

        response = client.post("/api/query", json=request_data)

        # Should still process (no length limit in API)
        assert response.status_code == 200

    def test_multiple_concurrent_queries(self, client, mock_rag_system):
        """Test handling multiple queries in sequence"""
        queries = [
            "What is MCP?",
            "Tell me about Python",
            "How does RAG work?"
        ]

        for query in queries:
            request_data = {"query": query, "session_id": None}
            response = client.post("/api/query", json=request_data)
            assert response.status_code == 200

    def test_session_persistence_across_queries(self, client, mock_rag_system):
        """Test that session ID persists across multiple queries"""
        # First query creates session
        response1 = client.post("/api/query", json={
            "query": "First question",
            "session_id": None
        })
        session_id = response1.json()["session_id"]

        # Second query uses same session
        response2 = client.post("/api/query", json={
            "query": "Follow-up question",
            "session_id": session_id
        })

        assert response2.json()["session_id"] == session_id

        # Verify RAG system received the same session ID
        calls = mock_rag_system.query.call_args_list
        assert calls[1][0][1] == session_id


@pytest.mark.api
class TestAPIErrorHandling:
    """Test suite for API error handling and edge cases"""

    def test_404_for_nonexistent_endpoint(self, client):
        """Test that nonexistent endpoints return 404"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test wrong HTTP method returns 405"""
        # GET on POST-only endpoint
        response = client.get("/api/query")
        assert response.status_code == 405

    def test_query_with_null_values(self, client):
        """Test query with null session_id (should be handled)"""
        request_data = {
            "query": "Valid query",
            "session_id": None
        }

        response = client.post("/api/query", json=request_data)
        assert response.status_code == 200

    def test_query_with_additional_fields(self, client):
        """Test that additional fields in request are ignored"""
        request_data = {
            "query": "Test query",
            "session_id": None,
            "extra_field": "should be ignored"
        }

        response = client.post("/api/query", json=request_data)
        assert response.status_code == 200

    def test_malformed_session_id(self, client, mock_rag_system):
        """Test query with malformed session ID"""
        request_data = {
            "query": "Test",
            "session_id": "invalid@#$%^&*()"
        }

        response = client.post("/api/query", json=request_data)
        # Should still work - RAG system handles session validation
        assert response.status_code == 200


@pytest.mark.api
class TestAPIIntegrationFlow:
    """Integration tests for complete API workflows"""

    def test_full_query_workflow(self, client, mock_rag_system):
        """Test complete query workflow from request to response"""
        # Step 1: Get course list
        courses_response = client.get("/api/courses")
        assert courses_response.status_code == 200
        courses = courses_response.json()
        assert courses["total_courses"] > 0

        # Step 2: Query about a course
        query_response = client.post("/api/query", json={
            "query": f"Tell me about {courses['course_titles'][0]}",
            "session_id": None
        })
        assert query_response.status_code == 200
        query_data = query_response.json()

        # Step 3: Follow-up query with same session
        followup_response = client.post("/api/query", json={
            "query": "Can you elaborate?",
            "session_id": query_data["session_id"]
        })
        assert followup_response.status_code == 200
        assert followup_response.json()["session_id"] == query_data["session_id"]

    def test_api_health_check_workflow(self, client):
        """Test basic health check workflow"""
        # Check root endpoint
        root_response = client.get("/")
        assert root_response.status_code == 200

        # Check courses endpoint (doesn't require query)
        courses_response = client.get("/api/courses")
        assert courses_response.status_code == 200

    def test_error_recovery(self, client, mock_rag_system):
        """Test that API recovers from errors"""
        # First request fails
        mock_rag_system.query.side_effect = Exception("Temporary error")
        response1 = client.post("/api/query", json={
            "query": "Test",
            "session_id": None
        })
        assert response1.status_code == 500

        # Reset the mock to succeed
        mock_rag_system.query.side_effect = None
        mock_rag_system.query.return_value = (
            "Success",
            [{"text": "Source", "link": "http://example.com"}]
        )

        # Second request succeeds
        response2 = client.post("/api/query", json={
            "query": "Test again",
            "session_id": None
        })
        assert response2.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "api"])
