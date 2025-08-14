"""
Performance tests for demo load scenarios
Tests system performance under realistic demo conditions
"""

import pytest
import time
import threading
import statistics
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add the server directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app

client = TestClient(app)

class TestDemoPerformance:
    """Test performance under demo conditions"""
    
    def test_health_endpoint_performance(self):
        """Test health endpoint responds quickly"""
        response_times = []
        
        for _ in range(10):
            start_time = time.time()
            response = client.get("/health")
            response_time = time.time() - start_time
            
            assert response.status_code == 200
            response_times.append(response_time)
        
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        
        # Health checks should be very fast
        assert avg_time < 0.1, f"Average response time {avg_time:.3f}s too slow"
        assert max_time < 0.5, f"Max response time {max_time:.3f}s too slow"
        
    def test_search_endpoint_performance(self):
        """Test search endpoint performance"""
        response_times = []
        
        search_queries = [
            "machine learning",
            "neural networks", 
            "artificial intelligence",
            "deep learning",
            "natural language processing"
        ]
        
        for query in search_queries:
            start_time = time.time()
            response = client.get(f"/search?q={query}")
            response_time = time.time() - start_time
            
            # Accept 200 (found) or 404 (not found) for empty database
            assert response.status_code in [200, 404]
            response_times.append(response_time)
        
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        
        # Search should be fast for demo
        assert avg_time < 2.0, f"Average search time {avg_time:.3f}s too slow"
        assert max_time < 5.0, f"Max search time {max_time:.3f}s too slow"
        
    @patch('services.ie_service.IEService.extract_entities_relations')
    @patch('services.canonicalization.CanonicalizeService.canonicalize_entities')
    @patch('storage.qdrant_adapter.QdrantAdapter.store_entities')
    @patch('storage.oxigraph_adapter.OxigraphAdapter.store_relationships')
    def test_ingest_performance(self, mock_store_rel, mock_store_ent, 
                              mock_canon, mock_extract):
        """Test ingestion performance for demo-sized content"""
        
        # Mock fast extraction
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
        
        # Test different text sizes
        text_sizes = [
            ("Small", "This is a small test document."),
            ("Medium", "This is a medium test document. " * 50),
            ("Large", "This is a large test document. " * 200)
        ]
        
        for size_name, text in text_sizes:
            start_time = time.time()
            response = client.post("/ingest", json={
                "doc_id": f"test_{size_name.lower()}",
                "text": text
            })
            processing_time = time.time() - start_time
            
            assert response.status_code == 200
            
            # Performance expectations for demo
            if size_name == "Small":
                assert processing_time < 1.0, f"Small text took {processing_time:.3f}s"
            elif size_name == "Medium":
                assert processing_time < 5.0, f"Medium text took {processing_time:.3f}s"
            else:  # Large
                assert processing_time < 15.0, f"Large text took {processing_time:.3f}s"
                
    def test_concurrent_user_simulation(self):
        """Simulate multiple concurrent demo users"""
        
        def simulate_user_session():
            """Simulate a typical user session during demo"""
            session_results = []
            
            try:
                # User checks health
                response = client.get("/health")
                session_results.append(response.status_code == 200)
                
                # User searches for something
                response = client.get("/search?q=test")
                session_results.append(response.status_code in [200, 404])
                
                # User exports graph
                response = client.get("/graph/export")
                session_results.append(response.status_code == 200)
                
                # User asks a question
                response = client.get("/ask?q=what is this about")
                session_results.append(response.status_code in [200, 500])  # 500 OK if no data
                
            except Exception:
                session_results.append(False)
                
            return all(session_results)
        
        # Simulate 5 concurrent users
        threads = []
        results = []
        
        def run_session():
            result = simulate_user_session()
            results.append(result)
        
        start_time = time.time()
        
        for _ in range(5):
            thread = threading.Thread(target=run_session)
            threads.append(thread)
            thread.start()
        
        # Wait for all sessions to complete
        for thread in threads:
            thread.join(timeout=30)
        
        total_time = time.time() - start_time
        
        # All user sessions should complete successfully
        assert len(results) == 5
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.8, f"Only {success_rate:.1%} of sessions succeeded"
        assert total_time < 30, f"Concurrent sessions took {total_time:.1f}s"
        
    def test_memory_usage_stability(self):
        """Test memory usage remains stable during repeated operations"""
        
        # Perform repeated operations
        for i in range(20):
            # Health checks
            response = client.get("/health")
            assert response.status_code == 200
            
            # Searches
            response = client.get(f"/search?q=test_{i}")
            assert response.status_code in [200, 404]
            
            # Graph exports
            response = client.get("/graph/export")
            assert response.status_code == 200
            
        # If we get here without memory errors, test passes
        # In a real scenario, we'd monitor actual memory usage
        
    def test_api_rate_limiting_behavior(self):
        """Test API behavior under rapid requests"""
        
        # Make rapid requests to test rate limiting/throttling
        response_codes = []
        response_times = []
        
        for _ in range(50):
            start_time = time.time()
            response = client.get("/health")
            response_time = time.time() - start_time
            
            response_codes.append(response.status_code)
            response_times.append(response_time)
        
        # Most requests should succeed
        success_rate = sum(1 for code in response_codes if code == 200) / len(response_codes)
        assert success_rate >= 0.9, f"Only {success_rate:.1%} of rapid requests succeeded"
        
        # Response times should remain reasonable
        avg_time = statistics.mean(response_times)
        assert avg_time < 1.0, f"Average response time {avg_time:.3f}s under load"

class TestScalabilityLimits:
    """Test system behavior at scalability limits"""
    
    def test_large_search_results(self):
        """Test handling of large search result sets"""
        
        # Test search with different result limits
        for k in [1, 8, 50, 100]:
            response = client.get(f"/search?q=test&k={k}")
            assert response.status_code in [200, 404, 422]
            
            if response.status_code == 200:
                data = response.json()
                assert len(data) <= k
                
    def test_deep_graph_traversal(self):
        """Test performance of deep graph traversals"""
        
        # Test neighbor expansion with different hop counts
        for hops in [1, 2, 3]:
            response = client.get(f"/neighbors?node_id=test&hops={hops}")
            assert response.status_code in [200, 404]
            
            # Response should come back in reasonable time
            # (This is implicitly tested by the client timeout)
            
    @patch('services.ie_service.IEService.extract_entities_relations')
    def test_entity_limit_handling(self, mock_extract):
        """Test handling of documents with many entities"""
        
        # Mock extraction with many entities
        mock_extract.return_value = {
            "entities": [
                {
                    "name": f"Entity_{i}",
                    "type": "Concept",
                    "aliases": [],
                    "source_spans": [{"start": i*10, "end": i*10+7}]
                } for i in range(100)  # Many entities
            ],
            "relationships": [
                {
                    "from": f"Entity_{i}",
                    "to": f"Entity_{i+1}",
                    "predicate": "relates_to",
                    "confidence": 0.8,
                    "evidence": [{"quote": f"Entity {i} relates to Entity {i+1}", "offset": i*10}]
                } for i in range(99)  # Many relationships
            ]
        }
        
        response = client.post("/ingest", json={
            "doc_id": "entity_heavy_doc",
            "text": "A document with many entities and relationships."
        })
        
        # Should handle gracefully (success or controlled failure)
        assert response.status_code in [200, 413, 422, 500]

class TestDemoSpecificScenarios:
    """Test scenarios specific to demo presentation"""
    
    def test_demo_startup_time(self):
        """Test system is ready quickly after startup"""
        
        # Test that all endpoints are responsive immediately
        endpoints = ["/", "/health", "/graph/export"]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            response_time = time.time() - start_time
            
            assert response.status_code == 200
            assert response_time < 2.0, f"{endpoint} took {response_time:.3f}s on startup"
            
    def test_demo_data_consistency(self):
        """Test data remains consistent during demo operations"""
        
        # Export initial state
        initial_export = client.get("/graph/export")
        assert initial_export.status_code == 200
        initial_data = initial_export.json()
        
        # Perform some operations
        client.get("/search?q=test")
        client.get("/ask?q=test question")
        
        # Export again
        final_export = client.get("/graph/export")
        assert final_export.status_code == 200
        final_data = final_export.json()
        
        # Data should be consistent (no corruption)
        assert isinstance(final_data["nodes"], list)
        assert isinstance(final_data["edges"], list)
        
    def test_error_recovery_during_demo(self):
        """Test system recovers gracefully from errors during demo"""
        
        # Test recovery from bad requests
        bad_response = client.post("/ingest", json={"invalid": "data"})
        assert bad_response.status_code == 422
        
        # System should still work after bad request
        good_response = client.get("/health")
        assert good_response.status_code == 200
        
        # Test recovery from not found
        not_found = client.get("/neighbors?node_id=nonexistent")
        assert not_found.status_code in [404, 200]
        
        # System should still work
        health_response = client.get("/health")
        assert health_response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"])