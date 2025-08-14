"""
Smoke tests for all API endpoints
Tests basic functionality without requiring external dependencies
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add the server directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app

client = TestClient(app)

class TestSmokeTests:
    """Smoke tests for all API endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns basic info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
        
    def test_health_endpoint(self):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        
    def test_health_metrics_endpoint(self):
        """Test health metrics endpoint"""
        response = client.get("/health/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "uptime" in data
        assert "memory_usage" in data
        
    def test_health_errors_endpoint(self):
        """Test health errors endpoint"""
        response = client.get("/health/errors")
        assert response.status_code == 200
        data = response.json()
        assert "error_count" in data
        
    @patch('services.ie_service.IEService.extract_entities_relations')
    @patch('services.canonicalization.CanonicalizeService.canonicalize_entities')
    @patch('storage.qdrant_adapter.QdrantAdapter.store_entities')
    @patch('storage.oxigraph_adapter.OxigraphAdapter.store_relationships')
    def test_ingest_endpoint_structure(self, mock_store_rel, mock_store_ent, 
                                     mock_canon, mock_extract):
        """Test ingest endpoint accepts proper structure"""
        # Mock successful extraction
        mock_extract.return_value = {
            "entities": [
                {
                    "name": "Test Entity",
                    "type": "Concept",
                    "aliases": [],
                    "source_spans": [{"start": 0, "end": 11}]
                }
            ],
            "relationships": []
        }
        mock_canon.return_value = []
        mock_store_ent.return_value = None
        mock_store_rel.return_value = None
        
        # Test valid request
        response = client.post("/ingest", json={
            "doc_id": "test_doc",
            "text": "Test content for ingestion"
        })
        assert response.status_code == 200
        
        # Test invalid request
        response = client.post("/ingest", json={
            "invalid_field": "test"
        })
        assert response.status_code == 422
        
    def test_search_endpoint_structure(self):
        """Test search endpoint structure (may return empty results)"""
        # Test with query parameter
        response = client.get("/search?q=test")
        assert response.status_code in [200, 404]  # 404 OK for empty database
        
        # Test without query parameter
        response = client.get("/search")
        assert response.status_code == 422  # Missing required parameter
        
    def test_neighbors_endpoint_structure(self):
        """Test neighbors endpoint structure"""
        # Test with node_id parameter
        response = client.get("/neighbors?node_id=test_id")
        assert response.status_code in [200, 404]  # 404 OK for non-existent node
        
        # Test without node_id parameter
        response = client.get("/neighbors")
        assert response.status_code == 422  # Missing required parameter
        
    @patch('services.ie_service.IEService.generate_answer')
    def test_ask_endpoint_structure(self, mock_generate):
        """Test ask endpoint structure"""
        # Mock answer generation
        mock_generate.return_value = {
            "answer": "Test answer",
            "citations": []
        }
        
        # Test with question parameter
        response = client.get("/ask?q=test question")
        assert response.status_code == 200
        
        # Test without question parameter
        response = client.get("/ask")
        assert response.status_code == 422  # Missing required parameter
        
    def test_graph_export_endpoint(self):
        """Test graph export endpoint"""
        response = client.get("/graph/export")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        
    def test_websocket_endpoint_exists(self):
        """Test WebSocket endpoint exists (connection test)"""
        # We can't easily test WebSocket in sync tests, but we can check the endpoint exists
        # This will be covered in integration tests
        pass

class TestAPIValidation:
    """Test API input validation"""
    
    def test_ingest_validation(self):
        """Test ingest endpoint input validation"""
        # Missing doc_id
        response = client.post("/ingest", json={"text": "test"})
        assert response.status_code == 422
        
        # Missing text
        response = client.post("/ingest", json={"doc_id": "test"})
        assert response.status_code == 422
        
        # Empty text
        response = client.post("/ingest", json={"doc_id": "test", "text": ""})
        assert response.status_code == 422
        
        # Text too long (if we have limits)
        very_long_text = "x" * 100000
        response = client.post("/ingest", json={
            "doc_id": "test", 
            "text": very_long_text
        })
        # Should either accept or reject gracefully
        assert response.status_code in [200, 422, 413]
        
    def test_search_validation(self):
        """Test search endpoint input validation"""
        # Empty query
        response = client.get("/search?q=")
        assert response.status_code in [200, 422]
        
        # Very long query
        long_query = "x" * 1000
        response = client.get(f"/search?q={long_query}")
        assert response.status_code in [200, 422]
        
        # Invalid k parameter
        response = client.get("/search?q=test&k=-1")
        assert response.status_code == 422
        
        response = client.get("/search?q=test&k=abc")
        assert response.status_code == 422
        
    def test_neighbors_validation(self):
        """Test neighbors endpoint input validation"""
        # Invalid hops parameter
        response = client.get("/neighbors?node_id=test&hops=-1")
        assert response.status_code == 422
        
        response = client.get("/neighbors?node_id=test&hops=abc")
        assert response.status_code == 422
        
        # Invalid limit parameter
        response = client.get("/neighbors?node_id=test&limit=-1")
        assert response.status_code == 422

class TestErrorHandling:
    """Test error handling scenarios"""
    
    @patch('services.ie_service.IEService.extract_entities_relations')
    def test_ingest_ie_service_failure(self, mock_extract):
        """Test ingest handles IE service failures gracefully"""
        # Mock IE service failure
        mock_extract.side_effect = Exception("IE service failed")
        
        response = client.post("/ingest", json={
            "doc_id": "test_doc",
            "text": "Test content"
        })
        assert response.status_code == 500
        
    @patch('storage.qdrant_adapter.QdrantAdapter.search_similar')
    def test_search_database_failure(self, mock_search):
        """Test search handles database failures gracefully"""
        # Mock database failure
        mock_search.side_effect = Exception("Database connection failed")
        
        response = client.get("/search?q=test")
        assert response.status_code == 500

if __name__ == "__main__":
    pytest.main([__file__, "-v"])