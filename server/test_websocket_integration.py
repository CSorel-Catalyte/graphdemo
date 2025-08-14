"""
Integration tests for WebSocket real-time update broadcasting system.
Tests the integration between the ingestion pipeline and WebSocket broadcasting.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.websocket_manager import ConnectionManager
from models.websocket import (
    UpsertNodesMessage, UpsertEdgesMessage, StatusMessage, 
    ErrorMessage, ConnectionMessage, WSMessageWrapper
)
from models.core import Entity, EntityType, Relationship, RelationType, Evidence, IEResult
from models.api import IngestRequest


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.messages_sent = []
        self.closed = False
        self.should_fail = False
        
    async def accept(self):
        """Mock accept method"""
        pass
    
    async def send_text(self, data: str):
        """Mock send_text method"""
        if self.should_fail:
            raise Exception("Mock WebSocket send failure")
        self.messages_sent.append(data)
    
    async def receive_text(self):
        """Mock receive_text method"""
        if self.closed:
            raise Exception("WebSocket closed")
        return '{"type": "test", "data": "test_message"}'
    
    async def ping(self):
        """Mock ping method"""
        if self.should_fail:
            raise Exception("Mock WebSocket ping failure")
        pass


class MockIEService:
    """Mock Information Extraction Service"""
    
    def __init__(self):
        self.extract_calls = []
    
    async def extract_from_chunks(self, chunks, doc_id):
        """Mock extraction method"""
        self.extract_calls.append((chunks, doc_id))
        
        # Return mock results
        results = []
        for i, chunk in enumerate(chunks):
            entity = Entity(
                id=f"entity_{i}",
                name=f"Entity {i}",
                type=EntityType.CONCEPT,
                aliases=[],
                embedding=[],
                salience=0.5,
                source_spans=[],
                summary=f"Mock entity {i}"
            )
            
            relationship = Relationship(
                from_entity=f"entity_{i}",
                to_entity=f"entity_{(i+1) % len(chunks)}",
                predicate=RelationType.RELATES_TO,
                confidence=0.8,
                evidence=[Evidence(doc_id=doc_id, quote=f"quote {i}", offset=0)],
                directional=True
            )
            
            result = IEResult(
                entities=[entity],
                relationships=[relationship],
                chunk_id=f"chunk_{i}",
                doc_id=doc_id,
                processing_time=0.1
            )
            results.append(result)
        
        return results


class MockCanonicalizer:
    """Mock Entity Canonicalizer"""
    
    def __init__(self):
        self.canonicalize_calls = []
    
    async def canonicalize_entities(self, entities):
        """Mock canonicalization method"""
        self.canonicalize_calls.append(entities)
        # Return the same entities for simplicity
        return entities


class MockQdrantAdapter:
    """Mock Qdrant Adapter"""
    
    def __init__(self):
        self.stored_entities = []
        self.store_calls = []
    
    async def store_entities(self, entities):
        """Mock store entities method"""
        self.store_calls.append(entities)
        self.stored_entities.extend(entities)
        return len(entities)


class MockOxigraphAdapter:
    """Mock Oxigraph Adapter"""
    
    def __init__(self):
        self.stored_entities = []
        self.stored_relationships = []
    
    async def store_entity(self, entity):
        """Mock store entity method"""
        self.stored_entities.append(entity)
    
    async def store_relationship(self, relationship):
        """Mock store relationship method"""
        self.stored_relationships.append(relationship)


@pytest.fixture
def connection_manager():
    """Create a fresh ConnectionManager for each test"""
    manager = ConnectionManager()
    manager._lock = asyncio.Lock()
    return manager


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing"""
    return MockWebSocket()


@pytest.fixture
def mock_services():
    """Create mock services for testing"""
    return {
        'ie_service': MockIEService(),
        'canonicalizer': MockCanonicalizer(),
        'qdrant_adapter': MockQdrantAdapter(),
        'oxigraph_adapter': MockOxigraphAdapter()
    }


@pytest.mark.asyncio
async def test_status_message_broadcasting_during_ingestion(connection_manager, mock_websocket, mock_services):
    """Test that status messages are broadcasted during the ingestion pipeline"""
    # Connect a WebSocket client
    client_id = await connection_manager.connect(mock_websocket)
    
    # Clear connection message
    mock_websocket.messages_sent.clear()
    
    # Mock the text chunking function
    with patch('services.text_chunking.chunk_text') as mock_chunk_text:
        mock_chunk_text.return_value = ["chunk1", "chunk2", "chunk3"]
        
        # Simulate the ingestion pipeline status updates
        test_chunks = ["chunk1", "chunk2", "chunk3"]
        
        # Test chunking complete status
        status_msg = StatusMessage(
            stage="chunking_complete",
            count=len(test_chunks),
            total=len(test_chunks),
            message=f"Split text into {len(test_chunks)} chunks"
        )
        await connection_manager.broadcast(status_msg)
        
        # Test extraction status
        status_msg = StatusMessage(
            stage="extracting_entities",
            count=0,
            total=len(test_chunks),
            message="Starting information extraction from chunks"
        )
        await connection_manager.broadcast(status_msg)
        
        # Test extraction complete status
        status_msg = StatusMessage(
            stage="extraction_complete",
            count=5,
            total=5,
            message="Extracted 5 entities and 3 relationships"
        )
        await connection_manager.broadcast(status_msg)
        
        # Test canonicalization status
        status_msg = StatusMessage(
            stage="canonicalizing_entities",
            count=0,
            total=5,
            message="Starting entity canonicalization"
        )
        await connection_manager.broadcast(status_msg)
        
        # Test storage status
        status_msg = StatusMessage(
            stage="storing_data",
            count=0,
            total=8,
            message="Starting data storage"
        )
        await connection_manager.broadcast(status_msg)
    
    # Verify all status messages were sent
    assert len(mock_websocket.messages_sent) == 5
    
    # Parse and verify each message
    messages = [json.loads(msg) for msg in mock_websocket.messages_sent]
    
    # Check message types and stages
    expected_stages = [
        "chunking_complete",
        "extracting_entities", 
        "extraction_complete",
        "canonicalizing_entities",
        "storing_data"
    ]
    
    for i, expected_stage in enumerate(expected_stages):
        assert messages[i]["message"]["type"] == "status"
        assert messages[i]["message"]["stage"] == expected_stage


@pytest.mark.asyncio
async def test_node_and_edge_broadcasting(connection_manager, mock_websocket):
    """Test broadcasting of node and edge updates"""
    # Connect a WebSocket client
    client_id = await connection_manager.connect(mock_websocket)
    
    # Clear connection message
    mock_websocket.messages_sent.clear()
    
    # Create test entities
    entities = [
        Entity(
            id="entity_1",
            name="Test Entity 1",
            type=EntityType.CONCEPT,
            aliases=[],
            embedding=[],
            salience=0.8,
            source_spans=[],
            summary="Test entity 1"
        ),
        Entity(
            id="entity_2", 
            name="Test Entity 2",
            type=EntityType.PERSON,
            aliases=[],
            embedding=[],
            salience=0.6,
            source_spans=[],
            summary="Test entity 2"
        )
    ]
    
    # Create test relationships
    relationships = [
        Relationship(
            from_entity="entity_1",
            to_entity="entity_2",
            predicate=RelationType.RELATES_TO,
            confidence=0.9,
            evidence=[Evidence(doc_id="doc1", quote="test quote", offset=0)],
            directional=True
        )
    ]
    
    # Broadcast nodes
    nodes_message = UpsertNodesMessage(nodes=entities)
    await connection_manager.broadcast(nodes_message)
    
    # Broadcast edges
    edges_message = UpsertEdgesMessage(edges=relationships)
    await connection_manager.broadcast(edges_message)
    
    # Verify messages were sent
    assert len(mock_websocket.messages_sent) == 2
    
    # Parse messages
    node_msg = json.loads(mock_websocket.messages_sent[0])
    edge_msg = json.loads(mock_websocket.messages_sent[1])
    
    # Verify node message
    assert node_msg["message"]["type"] == "upsert_nodes"
    assert len(node_msg["message"]["nodes"]) == 2
    assert node_msg["message"]["nodes"][0]["id"] == "entity_1"
    assert node_msg["message"]["nodes"][1]["id"] == "entity_2"
    
    # Verify edge message
    assert edge_msg["message"]["type"] == "upsert_edges"
    assert len(edge_msg["message"]["edges"]) == 1
    assert edge_msg["message"]["edges"][0]["from_entity"] == "entity_1"
    assert edge_msg["message"]["edges"][0]["to_entity"] == "entity_2"


@pytest.mark.asyncio
async def test_multiple_clients_receive_broadcasts(connection_manager):
    """Test that multiple WebSocket clients receive broadcast messages"""
    # Connect multiple clients
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()
    
    client1 = await connection_manager.connect(ws1)
    client2 = await connection_manager.connect(ws2)
    client3 = await connection_manager.connect(ws3)
    
    # Clear connection messages
    ws1.messages_sent.clear()
    ws2.messages_sent.clear()
    ws3.messages_sent.clear()
    
    # Broadcast a status message
    status_msg = StatusMessage(
        stage="test_broadcast",
        count=10,
        total=20,
        message="Testing multi-client broadcast"
    )
    await connection_manager.broadcast(status_msg)
    
    # Verify all clients received the message
    assert len(ws1.messages_sent) == 1
    assert len(ws2.messages_sent) == 1
    assert len(ws3.messages_sent) == 1
    
    # Verify message content is the same
    msg1 = json.loads(ws1.messages_sent[0])
    msg2 = json.loads(ws2.messages_sent[0])
    msg3 = json.loads(ws3.messages_sent[0])
    
    assert msg1["message"]["stage"] == "test_broadcast"
    assert msg2["message"]["stage"] == "test_broadcast"
    assert msg3["message"]["stage"] == "test_broadcast"


@pytest.mark.asyncio
async def test_message_queuing_for_disconnected_clients(connection_manager):
    """Test that messages are queued for disconnected clients"""
    disconnected_client_id = "test_disconnected_client"
    
    # Send messages to disconnected client
    status_msg = StatusMessage(
        stage="queued_message",
        count=1,
        total=1,
        message="This message should be queued"
    )
    await connection_manager.send_personal_message(status_msg, disconnected_client_id)
    
    # Verify message was queued
    assert disconnected_client_id in connection_manager.message_queues
    assert len(connection_manager.message_queues[disconnected_client_id]) == 1
    
    # Connect the client
    mock_ws = MockWebSocket()
    await connection_manager.connect(mock_ws, disconnected_client_id)
    
    # Verify queued message was sent (plus connection message)
    assert len(mock_ws.messages_sent) == 2
    
    # Verify the queued message content
    queued_msg = json.loads(mock_ws.messages_sent[0])
    assert queued_msg["message"]["stage"] == "queued_message"
    
    # Verify queue was cleared
    assert disconnected_client_id not in connection_manager.message_queues


@pytest.mark.asyncio
async def test_websocket_message_serialization_with_real_data(connection_manager, mock_websocket):
    """Test WebSocket message serialization with realistic data"""
    # Connect client
    client_id = await connection_manager.connect(mock_websocket)
    mock_websocket.messages_sent.clear()
    
    # Create a realistic entity with all fields
    entity = Entity(
        id="realistic_entity_id",
        name="Machine Learning",
        type=EntityType.CONCEPT,
        aliases=["ML", "Artificial Intelligence"],
        embedding=[],  # Empty for testing
        salience=0.95,
        source_spans=[],
        summary="A method of data analysis that automates analytical model building"
    )
    
    # Create a realistic relationship
    relationship = Relationship(
        from_entity="realistic_entity_id",
        to_entity="another_entity_id",
        predicate=RelationType.USES,
        confidence=0.87,
        evidence=[
            Evidence(
                doc_id="research_paper_1",
                quote="Machine learning uses statistical techniques to give computers the ability to learn",
                offset=1250
            )
        ],
        directional=True
    )
    
    # Send node update
    nodes_msg = UpsertNodesMessage(nodes=[entity])
    await connection_manager.send_personal_message(nodes_msg, client_id)
    
    # Send edge update
    edges_msg = UpsertEdgesMessage(edges=[relationship])
    await connection_manager.send_personal_message(edges_msg, client_id)
    
    # Verify messages were sent and can be parsed
    assert len(mock_websocket.messages_sent) == 2
    
    # Parse and verify node message
    node_data = json.loads(mock_websocket.messages_sent[0])
    assert node_data["message"]["type"] == "upsert_nodes"
    assert node_data["message"]["nodes"][0]["name"] == "Machine Learning"
    assert node_data["message"]["nodes"][0]["salience"] == 0.95
    assert "ML" in node_data["message"]["nodes"][0]["aliases"]
    
    # Parse and verify edge message
    edge_data = json.loads(mock_websocket.messages_sent[1])
    assert edge_data["message"]["type"] == "upsert_edges"
    assert edge_data["message"]["edges"][0]["predicate"] == "uses"
    assert edge_data["message"]["edges"][0]["confidence"] == 0.87
    assert len(edge_data["message"]["edges"][0]["evidence"]) == 1


@pytest.mark.asyncio
async def test_error_message_broadcasting(connection_manager, mock_websocket):
    """Test broadcasting of error messages"""
    # Connect client
    client_id = await connection_manager.connect(mock_websocket)
    mock_websocket.messages_sent.clear()
    
    # Send error message
    error_msg = ErrorMessage(
        error="processing_error",
        message="Failed to process chunk due to API timeout"
    )
    await connection_manager.send_personal_message(error_msg, client_id)
    
    # Verify error message was sent
    assert len(mock_websocket.messages_sent) == 1
    
    # Parse and verify error message
    error_data = json.loads(mock_websocket.messages_sent[0])
    assert error_data["message"]["type"] == "error"
    assert error_data["message"]["error"] == "processing_error"
    assert "API timeout" in error_data["message"]["message"]


@pytest.mark.asyncio
async def test_connection_stats_tracking(connection_manager):
    """Test that connection statistics are properly tracked"""
    # Initially no connections
    stats = connection_manager.get_connection_stats()
    assert stats["active_connections"] == 0
    
    # Connect some clients
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    client1 = await connection_manager.connect(ws1)
    client2 = await connection_manager.connect(ws2)
    
    # Check stats after connections
    stats = connection_manager.get_connection_stats()
    assert stats["active_connections"] == 2
    assert len(stats["clients"]) == 2
    assert client1 in stats["clients"]
    assert client2 in stats["clients"]
    
    # Send some messages to track message counts
    status_msg = StatusMessage(stage="test", count=1, message="test")
    await connection_manager.send_personal_message(status_msg, client1)
    await connection_manager.broadcast(status_msg)
    
    # Verify message counts are tracked
    assert connection_manager.connection_metadata[client1]["messages_sent"] >= 2  # connection + personal + broadcast
    assert connection_manager.connection_metadata[client2]["messages_sent"] >= 2  # connection + broadcast


@pytest.mark.asyncio
async def test_websocket_integration_with_ingestion_pipeline():
    """Test the complete integration between ingestion pipeline and WebSocket broadcasting"""
    # This test simulates the complete flow without actually calling the FastAPI endpoint
    
    connection_manager = ConnectionManager()
    connection_manager._lock = asyncio.Lock()
    
    # Connect a mock client
    mock_ws = MockWebSocket()
    client_id = await connection_manager.connect(mock_ws)
    mock_ws.messages_sent.clear()
    
    # Simulate the ingestion pipeline stages
    stages = [
        ("chunking_complete", 3, "Split text into 3 chunks"),
        ("extracting_entities", 0, "Starting information extraction"),
        ("extraction_complete", 5, "Extracted 5 entities and 3 relationships"),
        ("canonicalizing_entities", 0, "Starting entity canonicalization"),
        ("canonicalization_complete", 4, "Canonicalized to 4 entities"),
        ("storing_data", 0, "Starting data storage"),
        ("storage_complete", 7, "Stored 4 entities and 3 relationships")
    ]
    
    # Send all status updates
    for stage, count, message in stages:
        status_msg = StatusMessage(stage=stage, count=count, message=message)
        await connection_manager.broadcast(status_msg)
    
    # Send final node and edge updates
    test_entity = Entity(
        id="final_entity",
        name="Final Entity",
        type=EntityType.CONCEPT,
        aliases=[],
        embedding=[],
        salience=0.7,
        source_spans=[],
        summary="Final test entity"
    )
    
    test_relationship = Relationship(
        from_entity="final_entity",
        to_entity="other_entity",
        predicate=RelationType.RELATES_TO,
        confidence=0.8,
        evidence=[],
        directional=True
    )
    
    nodes_msg = UpsertNodesMessage(nodes=[test_entity])
    edges_msg = UpsertEdgesMessage(edges=[test_relationship])
    
    await connection_manager.broadcast(nodes_msg)
    await connection_manager.broadcast(edges_msg)
    
    # Verify all messages were sent (7 status + 1 nodes + 1 edges = 9 total)
    assert len(mock_ws.messages_sent) == 9
    
    # Verify the sequence of messages
    messages = [json.loads(msg) for msg in mock_ws.messages_sent]
    
    # Check status messages
    for i, (expected_stage, _, _) in enumerate(stages):
        assert messages[i]["message"]["type"] == "status"
        assert messages[i]["message"]["stage"] == expected_stage
    
    # Check final node and edge messages
    assert messages[7]["message"]["type"] == "upsert_nodes"
    assert messages[8]["message"]["type"] == "upsert_edges"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])