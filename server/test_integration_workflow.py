#!/usr/bin/env python3
"""
Integration test for the complete ingestion workflow.
This test demonstrates the full pipeline when all services are properly configured.
"""
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

# Mock the services for testing
def create_mock_services():
    """Create mock services for testing the complete workflow"""
    
    # Mock Qdrant adapter
    mock_qdrant = Mock()
    mock_qdrant.connect = AsyncMock(return_value=True)
    mock_qdrant.store_entities = AsyncMock(return_value=3)
    mock_qdrant.get_entity = AsyncMock(return_value=None)
    mock_qdrant.get_entities_by_ids = AsyncMock(return_value=[])
    mock_qdrant.close = AsyncMock()
    
    # Mock Oxigraph adapter
    mock_oxigraph = Mock()
    mock_oxigraph.connect = AsyncMock(return_value=True)
    mock_oxigraph.store_entity = AsyncMock(return_value=True)
    mock_oxigraph.store_relationship = AsyncMock(return_value=True)
    mock_oxigraph.get_neighbors = AsyncMock(return_value=[])
    mock_oxigraph.get_entity_relationships = AsyncMock(return_value=[])
    mock_oxigraph.export_graph = AsyncMock(return_value={"entities": [], "relationships": []})
    mock_oxigraph.close = AsyncMock()
    
    # Mock IE service
    mock_ie_service = Mock()
    mock_ie_service.extract_from_chunks = AsyncMock()
    
    # Mock canonicalizer
    mock_canonicalizer = Mock()
    mock_canonicalizer.canonicalize_entities = AsyncMock()
    
    return mock_qdrant, mock_oxigraph, mock_ie_service, mock_canonicalizer

def test_complete_workflow():
    """Test the complete ingestion workflow with mocked services"""
    
    # Create mock services
    mock_qdrant, mock_oxigraph, mock_ie_service, mock_canonicalizer = create_mock_services()
    
    # Mock the IE results
    from models.core import Entity, Relationship, IEResult, EntityType, RelationType, Evidence, SourceSpan
    from datetime import datetime
    
    # Create sample entities
    sample_entities = [
        Entity(
            id="entity_1",
            name="Machine Learning",
            type=EntityType.CONCEPT,
            aliases=["ML"],
            embedding=[0.1] * 3072,  # Mock embedding
            salience=0.9,
            source_spans=[SourceSpan(doc_id="test_doc", start=0, end=100)],
            summary="A subset of artificial intelligence"
        ),
        Entity(
            id="entity_2", 
            name="TensorFlow",
            type=EntityType.LIBRARY,
            aliases=["TF"],
            embedding=[0.2] * 3072,
            salience=0.8,
            source_spans=[SourceSpan(doc_id="test_doc", start=100, end=200)],
            summary="Machine learning framework by Google"
        )
    ]
    
    # Create sample relationships
    sample_relationships = [
        Relationship(
            from_entity="entity_2",
            to_entity="entity_1",
            predicate=RelationType.IMPLEMENTS,
            confidence=0.9,
            evidence=[Evidence(doc_id="test_doc", quote="TensorFlow implements machine learning", offset=150)],
            directional=True
        )
    ]
    
    # Mock IE results
    ie_result = IEResult(
        entities=sample_entities,
        relationships=sample_relationships,
        chunk_id="test_chunk_0",
        doc_id="test_doc"
    )
    
    mock_ie_service.extract_from_chunks.return_value = [ie_result]
    mock_canonicalizer.canonicalize_entities.return_value = sample_entities
    
    # Patch the global services in main module
    with patch('main.qdrant_adapter', mock_qdrant), \
         patch('main.oxigraph_adapter', mock_oxigraph), \
         patch('main.ie_service', mock_ie_service), \
         patch('main.canonicalizer', mock_canonicalizer):
        
        from main import app
        client = TestClient(app)
        
        # Test the ingestion workflow
        print("Testing complete ingestion workflow...")
        
        sample_text = """
        Machine Learning is a powerful subset of Artificial Intelligence. 
        TensorFlow is a popular machine learning framework developed by Google.
        It provides comprehensive tools for building and training neural networks.
        """
        
        response = client.post("/ingest", json={
            "doc_id": "integration_test_doc",
            "text": sample_text
        })
        
        print(f"Ingestion Status: {response.status_code}")
        print(f"Ingestion Response: {response.json()}")
        
        # Verify the workflow was executed
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        assert result["chunks_processed"] > 0
        assert result["entities_extracted"] == 2
        assert result["relationships_extracted"] == 1
        
        # Verify service calls were made
        mock_ie_service.extract_from_chunks.assert_called_once()
        mock_canonicalizer.canonicalize_entities.assert_called_once()
        mock_qdrant.store_entities.assert_called_once()
        
        print("✅ Complete ingestion workflow test passed!")
        
        # Test search endpoint (with mocked services)
        print("\nTesting search endpoint...")
        response = client.get("/search?q=machine learning&k=5")
        print(f"Search Status: {response.status_code}")
        print(f"Search Response: {response.json()}")
        
        # Test export endpoint
        print("\nTesting export endpoint...")
        response = client.get("/graph/export")
        print(f"Export Status: {response.status_code}")
        print(f"Export Response: {response.json()}")
        
        print("✅ All integration tests passed!")

def test_error_handling():
    """Test error handling in various scenarios"""
    from main import app
    client = TestClient(app)
    
    print("\nTesting error handling...")
    
    # Test empty text ingestion
    response = client.post("/ingest", json={
        "doc_id": "empty_test",
        "text": ""
    })
    print(f"Empty text status: {response.status_code}")
    assert response.status_code == 422  # Validation error
    
    # Test invalid search parameters
    response = client.get("/search?q=&k=100")
    print(f"Invalid search status: {response.status_code}")
    assert response.status_code == 400
    
    # Test invalid neighbors parameters
    response = client.get("/neighbors?node_id=&hops=5")
    print(f"Invalid neighbors status: {response.status_code}")
    assert response.status_code == 400
    
    print("✅ Error handling tests passed!")

if __name__ == "__main__":
    print("Running integration workflow tests...")
    
    # Test complete workflow with mocked services
    test_complete_workflow()
    
    # Test error handling
    test_error_handling()
    
    print("\nAll integration tests completed successfully!")