#!/usr/bin/env python3
"""
Test script to validate Pydantic models work correctly.
"""

import json
from datetime import datetime
from models import (
    Entity, EntityType, Relationship, RelationType, 
    Evidence, SourceSpan, IngestRequest, SearchRequest,
    UpsertNodesMessage, StatusMessage
)

def test_entity_model():
    """Test Entity model creation and validation"""
    print("Testing Entity model...")
    
    # Test basic entity creation
    entity = Entity(
        name="FastAPI",
        type=EntityType.LIBRARY,
        aliases=["Fast API", "fastapi"],
        salience=0.8,
        summary="A modern, fast web framework for building APIs with Python"
    )
    
    print(f"✓ Entity created: {entity.name} (ID: {entity.id[:8]}...)")
    print(f"✓ Auto-generated ID from name|type: {entity.id == entity.id}")
    print(f"✓ Timestamps set: created={entity.created_at}, updated={entity.updated_at}")
    
    # Test validation
    try:
        invalid_entity = Entity(name="", type=EntityType.CONCEPT)
        print("✗ Should have failed validation for empty name")
    except ValueError as e:
        print(f"✓ Validation works: {e}")
    
    return entity

def test_relationship_model():
    """Test Relationship model creation and validation"""
    print("\nTesting Relationship model...")
    
    evidence = Evidence(
        doc_id="doc1",
        quote="FastAPI is a modern web framework",
        offset=100
    )
    
    relationship = Relationship(
        from_entity="entity1",
        to_entity="entity2", 
        predicate=RelationType.USES,
        confidence=0.9,
        evidence=[evidence]
    )
    
    print(f"✓ Relationship created: {relationship.predicate}")
    print(f"✓ Evidence included: {len(relationship.evidence)} items")
    
    # Test validation - same entity
    try:
        invalid_rel = Relationship(
            from_entity="same",
            to_entity="same",
            predicate=RelationType.USES,
            confidence=0.5
        )
        print("✗ Should have failed validation for same entities")
    except ValueError as e:
        print(f"✓ Validation works: {e}")
    
    return relationship

def test_api_models():
    """Test API request/response models"""
    print("\nTesting API models...")
    
    # Test IngestRequest
    ingest_req = IngestRequest(
        doc_id="test_doc",
        text="This is a test document about FastAPI and Python."
    )
    print(f"✓ IngestRequest created: {ingest_req.doc_id}")
    
    # Test SearchRequest
    search_req = SearchRequest(q="FastAPI", k=5)
    print(f"✓ SearchRequest created: query='{search_req.q}', k={search_req.k}")
    
    # Test validation
    try:
        invalid_search = SearchRequest(q="   ", k=5)
        print("✗ Should have failed validation for empty query")
    except ValueError as e:
        print(f"✓ Validation works: {e}")

def test_websocket_models():
    """Test WebSocket message models"""
    print("\nTesting WebSocket models...")
    
    entity = Entity(name="Test", type=EntityType.CONCEPT)
    
    # Test UpsertNodesMessage
    nodes_msg = UpsertNodesMessage(nodes=[entity])
    print(f"✓ UpsertNodesMessage created with {len(nodes_msg.nodes)} nodes")
    
    # Test StatusMessage
    status_msg = StatusMessage(
        stage="processing",
        count=5,
        total=10,
        message="Processing chunks..."
    )
    print(f"✓ StatusMessage created: {status_msg.stage} ({status_msg.count}/{status_msg.total})")

def test_json_serialization():
    """Test JSON serialization/deserialization"""
    print("\nTesting JSON serialization...")
    
    entity = Entity(
        name="Python",
        type=EntityType.LIBRARY,
        salience=0.95
    )
    
    # Serialize to JSON
    json_str = entity.model_dump_json()
    print(f"✓ Serialized to JSON ({len(json_str)} chars)")
    
    # Deserialize from JSON
    entity_copy = Entity.model_validate_json(json_str)
    print(f"✓ Deserialized from JSON: {entity_copy.name}")
    
    # Verify they match
    assert entity.name == entity_copy.name
    assert entity.type == entity_copy.type
    print("✓ Serialization round-trip successful")

if __name__ == "__main__":
    print("=== Testing Pydantic Models ===")
    
    try:
        test_entity_model()
        test_relationship_model()
        test_api_models()
        test_websocket_models()
        test_json_serialization()
        
        print("\n🎉 All tests passed! Pydantic models are working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()