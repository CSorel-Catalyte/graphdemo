"""
End-to-end tests for complete user workflows
Tests the entire system integration for demo scenarios
"""

import pytest
import json
import time
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add the server directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app

client = TestClient(app)

class TestCompleteWorkflows:
    """Test complete user workflows end-to-end"""
    
    @patch('services.ie_service.IEService.extract_entities_relations')
    @patch('services.canonicalization.CanonicalizeService.canonicalize_entities')
    @patch('storage.qdrant_adapter.QdrantAdapter.store_entities')
    @patch('storage.oxigraph_adapter.OxigraphAdapter.store_relationships')
    @patch('storage.qdrant_adapter.QdrantAdapter.search_similar')
    def test_ingest_to_search_workflow(self, mock_search, mock_store_rel, 
                                     mock_store_ent, mock_canon, mock_extract):
        """Test complete workflow: ingest text -> search for entities"""
        
        # Mock extraction results
        mock_extract.return_value = {
            "entities": [
                {
                    "name": "Machine Learning",
                    "type": "Concept",
                    "aliases": ["ML", "machine learning"],
                    "source_spans": [{"start": 0, "end": 16}]
                },
                {
                    "name": "Neural Networks",
                    "type": "Concept", 
                    "aliases": ["neural nets"],
                    "source_spans": [{"start": 20, "end": 35}]
                }
            ],
            "relationships": [
                {
                    "from": "Machine Learning",
                    "to": "Neural Networks",
                    "predicate": "uses",
                    "confidence": 0.9,
                    "evidence": [{"quote": "ML uses neural networks", "offset": 0}]
                }
            ]
        }
        
        # Mock canonicalization (no merging needed)
        mock_canon.return_value = []
        
        # Mock storage operations
        mock_store_ent.return_value = None
        mock_store_rel.return_value = None
        
        # Step 1: Ingest text
        ingest_response = client.post("/ingest", json={
            "doc_id": "ml_intro",
            "text": "Machine Learning uses Neural Networks for pattern recognition."
        })
        assert ingest_response.status_code == 200
        ingest_data = ingest_response.json()
        assert ingest_data["status"] == "success"
        
        # Mock search results
        mock_search.return_value = [
            {
                "id": "ml_concept_123",
                "name": "Machine Learning",
                "type": "Concept",
                "salience": 0.8,
                "summary": "A field of AI focused on algorithms"
            }
        ]
        
        # Step 2: Search for ingested content
        search_response = client.get("/search?q=machine learning")
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert len(search_data) > 0
        assert search_data[0]["name"] == "Machine Learning"
        
    @patch('storage.oxigraph_adapter.OxigraphAdapter.get_neighbors')
    @patch('storage.qdrant_adapter.QdrantAdapter.get_entity_by_id')
    def test_search_to_navigation_workflow(self, mock_get_entity, mock_get_neighbors):
        """Test workflow: search -> select node -> explore neighbors"""
        
        # Mock entity retrieval
        mock_get_entity.return_value = {
            "id": "ml_concept_123",
            "name": "Machine Learning",
            "type": "Concept",
            "salience": 0.8,
            "summary": "A field of AI focused on algorithms",
            "evidence": [
                {"quote": "ML is a subset of AI", "doc_id": "intro_doc"}
            ]
        }
        
        # Mock neighbor retrieval
        mock_get_neighbors.return_value = {
            "nodes": [
                {
                    "id": "ai_concept_456",
                    "name": "Artificial Intelligence",
                    "type": "Concept",
                    "salience": 0.9
                },
                {
                    "id": "nn_concept_789",
                    "name": "Neural Networks",
                    "type": "Concept",
                    "salience": 0.7
                }
            ],
            "edges": [
                {
                    "from": "ml_concept_123",
                    "to": "ai_concept_456",
                    "predicate": "subset_of",
                    "confidence": 0.95
                }
            ]
        }
        
        # Step 1: Get neighbors of a node
        neighbors_response = client.get("/neighbors?node_id=ml_concept_123")
        assert neighbors_response.status_code == 200
        neighbors_data = neighbors_response.json()
        assert "nodes" in neighbors_data
        assert "edges" in neighbors_data
        assert len(neighbors_data["nodes"]) == 2
        
    @patch('services.ie_service.IEService.generate_answer')
    @patch('storage.qdrant_adapter.QdrantAdapter.search_similar')
    @patch('storage.oxigraph_adapter.OxigraphAdapter.get_neighbors')
    def test_question_answering_workflow(self, mock_get_neighbors, 
                                       mock_search, mock_generate):
        """Test workflow: ask question -> get grounded answer with citations"""
        
        # Mock search for relevant nodes
        mock_search.return_value = [
            {
                "id": "ml_concept_123",
                "name": "Machine Learning",
                "type": "Concept",
                "salience": 0.8,
                "summary": "A field of AI that enables computers to learn"
            }
        ]
        
        # Mock neighbor expansion
        mock_get_neighbors.return_value = {
            "nodes": [
                {
                    "id": "ai_concept_456", 
                    "name": "Artificial Intelligence",
                    "type": "Concept",
                    "summary": "Intelligence demonstrated by machines"
                }
            ],
            "edges": []
        }
        
        # Mock answer generation
        mock_generate.return_value = {
            "answer": "Machine Learning is a subset of Artificial Intelligence that enables computers to learn and improve from experience without being explicitly programmed.",
            "citations": [
                {
                    "node_id": "ml_concept_123",
                    "quote": "ML enables computers to learn from data",
                    "doc_id": "ml_intro"
                }
            ]
        }
        
        # Ask a question
        qa_response = client.get("/ask?q=What is machine learning?")
        assert qa_response.status_code == 200
        qa_data = qa_response.json()
        assert "answer" in qa_data
        assert "citations" in qa_data
        assert len(qa_data["citations"]) > 0
        assert qa_data["citations"][0]["node_id"] == "ml_concept_123"
        
    def test_export_import_workflow(self):
        """Test workflow: export graph -> verify format -> import capability"""
        
        # Export current graph state
        export_response = client.get("/graph/export")
        assert export_response.status_code == 200
        export_data = export_response.json()
        
        # Verify export format
        assert "nodes" in export_data
        assert "edges" in export_data
        assert isinstance(export_data["nodes"], list)
        assert isinstance(export_data["edges"], list)
        
        # Verify export can be serialized/deserialized
        json_str = json.dumps(export_data)
        reimported = json.loads(json_str)
        assert reimported == export_data

class TestMultiDocumentWorkflows:
    """Test multi-document processing workflows"""
    
    @patch('services.ie_service.IEService.extract_entities_relations')
    @patch('services.canonicalization.CanonicalizeService.canonicalize_entities')
    @patch('storage.qdrant_adapter.QdrantAdapter.store_entities')
    @patch('storage.oxigraph_adapter.OxigraphAdapter.store_relationships')
    def test_multi_document_entity_merging(self, mock_store_rel, mock_store_ent, 
                                         mock_canon, mock_extract):
        """Test entity merging across multiple documents"""
        
        # Mock extraction for first document
        mock_extract.return_value = {
            "entities": [
                {
                    "name": "Machine Learning",
                    "type": "Concept",
                    "aliases": ["ML"],
                    "source_spans": [{"start": 0, "end": 16}]
                }
            ],
            "relationships": []
        }
        
        # Mock canonicalization (no merging for first doc)
        mock_canon.return_value = []
        
        # Ingest first document
        response1 = client.post("/ingest", json={
            "doc_id": "doc1",
            "text": "Machine Learning is a powerful technique."
        })
        assert response1.status_code == 200
        
        # Mock extraction for second document (same entity, different alias)
        mock_extract.return_value = {
            "entities": [
                {
                    "name": "machine learning",  # Different case
                    "type": "Concept",
                    "aliases": ["artificial learning"],
                    "source_spans": [{"start": 0, "end": 16}]
                }
            ],
            "relationships": []
        }
        
        # Mock canonicalization (should merge entities)
        mock_canon.return_value = [
            {
                "action": "merge",
                "entities": ["Machine Learning", "machine learning"],
                "canonical_name": "Machine Learning"
            }
        ]
        
        # Ingest second document
        response2 = client.post("/ingest", json={
            "doc_id": "doc2", 
            "text": "machine learning algorithms are improving rapidly."
        })
        assert response2.status_code == 200
        
    @patch('services.ie_service.IEService.extract_entities_relations')
    @patch('services.canonicalization.CanonicalizeService.canonicalize_entities')
    @patch('storage.qdrant_adapter.QdrantAdapter.store_entities')
    @patch('storage.oxigraph_adapter.OxigraphAdapter.store_relationships')
    def test_conflict_detection_workflow(self, mock_store_rel, mock_store_ent,
                                       mock_canon, mock_extract):
        """Test detection of conflicting information across documents"""
        
        # Mock extraction with conflicting information
        mock_extract.side_effect = [
            # First document
            {
                "entities": [
                    {
                        "name": "GPT-3",
                        "type": "System",
                        "aliases": [],
                        "source_spans": [{"start": 0, "end": 5}]
                    }
                ],
                "relationships": [
                    {
                        "from": "GPT-3",
                        "to": "175B parameters",
                        "predicate": "has_parameter_count",
                        "confidence": 0.9,
                        "evidence": [{"quote": "GPT-3 has 175B parameters", "offset": 0}]
                    }
                ]
            },
            # Second document with conflicting info
            {
                "entities": [
                    {
                        "name": "GPT-3",
                        "type": "System", 
                        "aliases": [],
                        "source_spans": [{"start": 0, "end": 5}]
                    }
                ],
                "relationships": [
                    {
                        "from": "GPT-3",
                        "to": "170B parameters",
                        "predicate": "has_parameter_count", 
                        "confidence": 0.8,
                        "evidence": [{"quote": "GPT-3 contains 170B parameters", "offset": 0}]
                    }
                ]
            }
        ]
        
        # Mock canonicalization detecting conflict
        mock_canon.side_effect = [
            [],  # No conflicts in first doc
            [
                {
                    "action": "conflict",
                    "entity": "GPT-3",
                    "conflicting_relationships": [
                        "has_parameter_count: 175B parameters",
                        "has_parameter_count: 170B parameters"
                    ]
                }
            ]
        ]
        
        # Ingest first document
        response1 = client.post("/ingest", json={
            "doc_id": "paper1",
            "text": "GPT-3 has 175B parameters according to OpenAI."
        })
        assert response1.status_code == 200
        
        # Ingest second document with conflicting info
        response2 = client.post("/ingest", json={
            "doc_id": "paper2",
            "text": "GPT-3 contains 170B parameters as reported."
        })
        assert response2.status_code == 200

class TestPerformanceWorkflows:
    """Test performance under demo load scenarios"""
    
    def test_concurrent_requests(self):
        """Test system handles concurrent requests gracefully"""
        import threading
        import time
        
        results = []
        
        def make_request():
            try:
                response = client.get("/health")
                results.append(response.status_code == 200)
            except Exception:
                results.append(False)
        
        # Create multiple concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all requests to complete
        for thread in threads:
            thread.join(timeout=30)
        
        # All requests should succeed
        assert len(results) == 10
        assert all(results), "Some concurrent requests failed"
        
    @patch('services.ie_service.IEService.extract_entities_relations')
    def test_large_text_processing(self, mock_extract):
        """Test processing of large text documents"""
        
        # Mock extraction for large text
        mock_extract.return_value = {
            "entities": [
                {
                    "name": f"Entity_{i}",
                    "type": "Concept",
                    "aliases": [],
                    "source_spans": [{"start": i*10, "end": i*10+7}]
                } for i in range(50)  # Many entities
            ],
            "relationships": []
        }
        
        # Create large text (but within reasonable limits)
        large_text = "This is a test document. " * 200  # ~5000 characters
        
        start_time = time.time()
        response = client.post("/ingest", json={
            "doc_id": "large_doc",
            "text": large_text
        })
        processing_time = time.time() - start_time
        
        assert response.status_code == 200
        assert processing_time < 30  # Should process within 30 seconds
        
    def test_response_times(self):
        """Test API response times are acceptable for demo"""
        
        endpoints = [
            ("/", "GET"),
            ("/health", "GET"),
            ("/search?q=test", "GET"),
            ("/graph/export", "GET")
        ]
        
        for endpoint, method in endpoints:
            start_time = time.time()
            
            if method == "GET":
                response = client.get(endpoint)
            
            response_time = time.time() - start_time
            
            # All endpoints should respond within 5 seconds for demo
            assert response_time < 5.0, f"{endpoint} took {response_time:.2f}s"
            assert response.status_code in [200, 404, 422]  # Valid status codes

if __name__ == "__main__":
    pytest.main([__file__, "-v"])