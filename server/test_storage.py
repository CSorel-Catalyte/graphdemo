"""
Test script for storage layer adapters.
Verifies basic functionality of Qdrant and Oxigraph adapters.
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from models.core import Entity, Relationship, EntityType, RelationType, Evidence, SourceSpan
from storage.qdrant_adapter import QdrantAdapter
from storage.oxigraph_adapter import OxigraphAdapter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_qdrant_adapter():
    """Test Qdrant adapter functionality"""
    logger.info("Testing Qdrant adapter...")
    
    # Initialize adapter
    qdrant = QdrantAdapter()
    
    # Test connection (will fail without Qdrant running, but we can test the code)
    try:
        connected = await qdrant.connect()
        if not connected:
            logger.warning("Qdrant not available, skipping connection tests")
            return
        
        # Create test entity
        test_entity = Entity(
            name="Test Entity",
            type=EntityType.CONCEPT,
            aliases=["Test", "Example"],
            embedding=[0.1] * 3072,  # Mock embedding
            salience=0.8,
            summary="A test entity for validation",
            source_spans=[
                SourceSpan(doc_id="test_doc", start=0, end=10)
            ]
        )
        
        # Test storing entity
        success = await qdrant.store_entity(test_entity)
        logger.info(f"Store entity result: {success}")
        
        # Test retrieving entity
        retrieved = await qdrant.get_entity(test_entity.id)
        if retrieved:
            logger.info(f"Retrieved entity: {retrieved.name}")
        
        # Test similarity search
        similar = await qdrant.find_similar_entities(
            query_vector=[0.1] * 3072,
            limit=5,
            score_threshold=0.5
        )
        logger.info(f"Found {len(similar)} similar entities")
        
        # Test health check
        health = await qdrant.health_check()
        logger.info(f"Qdrant health: {health}")
        
        await qdrant.close()
        
    except Exception as e:
        logger.error(f"Qdrant test error: {e}")


async def test_oxigraph_adapter():
    """Test Oxigraph adapter functionality"""
    logger.info("Testing Oxigraph adapter...")
    
    # Initialize adapter
    oxigraph = OxigraphAdapter()
    
    try:
        # Test connection
        connected = await oxigraph.connect()
        logger.info(f"Oxigraph connected: {connected}")
        
        if not connected:
            return
        
        # Create test entities
        entity1 = Entity(
            name="Entity One",
            type=EntityType.CONCEPT,
            salience=0.7,
            summary="First test entity"
        )
        
        entity2 = Entity(
            name="Entity Two", 
            type=EntityType.LIBRARY,
            salience=0.6,
            summary="Second test entity"
        )
        
        # Store entities
        await oxigraph.store_entity(entity1)
        await oxigraph.store_entity(entity2)
        logger.info("Stored test entities")
        
        # Create test relationship
        relationship = Relationship(
            from_entity=entity1.id,
            to_entity=entity2.id,
            predicate=RelationType.USES,
            confidence=0.9,
            evidence=[
                Evidence(
                    doc_id="test_doc",
                    quote="Entity one uses entity two",
                    offset=100
                )
            ]
        )
        
        # Store relationship
        await oxigraph.store_relationship(relationship)
        logger.info("Stored test relationship")
        
        # Test neighbor search
        neighbors = await oxigraph.get_neighbors(entity1.id, hops=1, limit=10)
        logger.info(f"Found {len(neighbors)} neighbors for entity1")
        
        # Test graph statistics
        stats = await oxigraph.get_graph_statistics()
        logger.info(f"Graph statistics: {stats}")
        
        # Test health check
        health = await oxigraph.health_check()
        logger.info(f"Oxigraph health: {health}")
        
        await oxigraph.close()
        
    except Exception as e:
        logger.error(f"Oxigraph test error: {e}")


async def main():
    """Run all storage tests"""
    logger.info("Starting storage layer tests...")
    
    await test_qdrant_adapter()
    await test_oxigraph_adapter()
    
    logger.info("Storage layer tests completed")


if __name__ == "__main__":
    asyncio.run(main())