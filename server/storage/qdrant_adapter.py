"""
Qdrant vector database adapter for entity storage and similarity search.
Handles vector embeddings, entity canonicalization, and similarity queries.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
import numpy as np
from datetime import datetime
import asyncio
import time

from models.core import Entity, EntityType
from utils.error_handling import (
    error_handler, with_retry, handle_graceful_degradation,
    RetryConfig, ErrorClassifier
)

logger = logging.getLogger(__name__)


class QdrantAdapter:
    """Adapter for Qdrant vector database operations"""
    
    def __init__(self, url: str = "http://localhost:6333", collection_name: str = "entities"):
        """
        Initialize Qdrant adapter
        
        Args:
            url: Qdrant server URL
            collection_name: Name of the collection to use
        """
        self.url = url
        self.collection_name = collection_name
        self.client = None
        self._connection_retries = 3
        self._retry_delay = 1.0
        
    @with_retry(
        retry_config=RetryConfig(max_retries=3, base_delay=1.0, max_delay=30.0),
        circuit_breaker_name="qdrant_connection",
        context={"service": "qdrant", "operation": "connect"}
    )
    async def connect(self) -> bool:
        """
        Establish connection to Qdrant and initialize collection with enhanced error handling
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.client = QdrantClient(url=self.url)
            
            # Test connection
            collections = self.client.get_collections()
            logger.info(f"Connected to Qdrant at {self.url}")
            
            # Initialize collection if it doesn't exist
            await self._ensure_collection_exists()
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    async def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                
                # Create collection with 3072-dimensional vectors (OpenAI text-embedding-3-large)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=3072,
                        distance=models.Distance.COSINE
                    ),
                    optimizers_config=models.OptimizersConfig(
                        default_segment_number=2,
                        max_segment_size=20000,
                        memmap_threshold=20000,
                        indexing_threshold=20000,
                        flush_interval_sec=5,
                        max_optimization_threads=1
                    ),
                    hnsw_config=models.HnswConfig(
                        m=16,
                        ef_construct=100,
                        full_scan_threshold=10000,
                        max_indexing_threads=0,
                        on_disk=False
                    )
                )
                logger.info(f"Collection {self.collection_name} created successfully")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise
    
    @handle_graceful_degradation(fallback_value=False)
    @with_retry(
        retry_config=RetryConfig(max_retries=2, base_delay=0.5, max_delay=5.0),
        circuit_breaker_name="qdrant_storage",
        context={"service": "qdrant", "operation": "store_entity"}
    )
    async def store_entity(self, entity: Entity) -> bool:
        """
        Store or update an entity in the vector database with enhanced error handling
        
        Args:
            entity: Entity to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client:
            raise Exception("Qdrant client not connected")
            
        if not entity.embedding:
            logger.warning(f"Entity {entity.id} has no embedding, skipping storage")
            return False
            
        # Prepare payload with entity metadata
        payload = {
            "name": entity.name,
            "type": entity.type.value,
            "aliases": entity.aliases,
            "salience": entity.salience,
            "summary": entity.summary,
            "source_spans": [
                {
                    "doc_id": span.doc_id,
                    "start": span.start,
                    "end": span.end
                } for span in entity.source_spans
            ],
            "created_at": entity.created_at.isoformat(),
            "updated_at": entity.updated_at.isoformat()
        }
        
        # Upsert the entity
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=entity.id,
                    vector=entity.embedding,
                    payload=payload
                )
            ]
        )
        
        logger.debug(f"Stored entity {entity.id} ({entity.name})")
        return True
    
    async def store_entities(self, entities: List[Entity]) -> int:
        """
        Store multiple entities in batch
        
        Args:
            entities: List of entities to store
            
        Returns:
            int: Number of entities successfully stored
        """
        if not self.client:
            logger.error("Qdrant client not connected")
            return 0
            
        if not entities:
            return 0
            
        try:
            points = []
            stored_count = 0
            
            for entity in entities:
                if not entity.embedding:
                    logger.warning(f"Entity {entity.id} has no embedding, skipping")
                    continue
                    
                payload = {
                    "name": entity.name,
                    "type": entity.type.value,
                    "aliases": entity.aliases,
                    "salience": entity.salience,
                    "summary": entity.summary,
                    "source_spans": [
                        {
                            "doc_id": span.doc_id,
                            "start": span.start,
                            "end": span.end
                        } for span in entity.source_spans
                    ],
                    "created_at": entity.created_at.isoformat(),
                    "updated_at": entity.updated_at.isoformat()
                }
                
                points.append(
                    models.PointStruct(
                        id=entity.id,
                        vector=entity.embedding,
                        payload=payload
                    )
                )
                stored_count += 1
            
            if points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info(f"Stored {stored_count} entities in batch")
            
            return stored_count
            
        except Exception as e:
            logger.error(f"Error storing entities batch: {e}")
            return 0
    
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """
        Retrieve an entity by ID
        
        Args:
            entity_id: Entity ID to retrieve
            
        Returns:
            Entity if found, None otherwise
        """
        if not self.client:
            logger.error("Qdrant client not connected")
            return None
            
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[entity_id],
                with_payload=True,
                with_vectors=True
            )
            
            if not result:
                return None
                
            point = result[0]
            return self._point_to_entity(point)
            
        except Exception as e:
            logger.error(f"Error retrieving entity {entity_id}: {e}")
            return None
    
    async def find_similar_entities(
        self, 
        query_vector: List[float], 
        limit: int = 10,
        score_threshold: float = 0.86,
        entity_type: Optional[EntityType] = None
    ) -> List[Tuple[Entity, float]]:
        """
        Find entities similar to the query vector
        
        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (cosine)
            entity_type: Optional entity type filter
            
        Returns:
            List of (Entity, similarity_score) tuples
        """
        if not self.client:
            logger.error("Qdrant client not connected")
            return []
            
        if len(query_vector) != 3072:
            logger.error(f"Query vector must be 3072-dimensional, got {len(query_vector)}")
            return []
            
        try:
            # Build filter conditions
            filter_conditions = []
            if entity_type:
                filter_conditions.append(
                    models.FieldCondition(
                        key="type",
                        match=models.MatchValue(value=entity_type.value)
                    )
                )
            
            query_filter = None
            if filter_conditions:
                query_filter = models.Filter(
                    must=filter_conditions
                )
            
            # Perform similarity search
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=True
            )
            
            results = []
            for scored_point in search_result:
                entity = self._point_to_entity(scored_point)
                if entity:
                    results.append((entity, scored_point.score))
            
            logger.debug(f"Found {len(results)} similar entities with score >= {score_threshold}")
            return results
            
        except Exception as e:
            logger.error(f"Error finding similar entities: {e}")
            return []
    
    async def search_entities_by_text(
        self, 
        query_embedding: List[float], 
        limit: int = 8
    ) -> List[Tuple[Entity, float]]:
        """
        Search entities by text query embedding
        
        Args:
            query_embedding: Embedded query text
            limit: Maximum number of results
            
        Returns:
            List of (Entity, similarity_score) tuples
        """
        return await self.find_similar_entities(
            query_vector=query_embedding,
            limit=limit,
            score_threshold=0.0  # Return all results for search
        )
    
    async def get_entities_by_ids(self, entity_ids: List[str]) -> List[Entity]:
        """
        Retrieve multiple entities by their IDs
        
        Args:
            entity_ids: List of entity IDs
            
        Returns:
            List of found entities
        """
        if not self.client or not entity_ids:
            return []
            
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=entity_ids,
                with_payload=True,
                with_vectors=True
            )
            
            entities = []
            for point in result:
                entity = self._point_to_entity(point)
                if entity:
                    entities.append(entity)
            
            logger.debug(f"Retrieved {len(entities)} entities by IDs")
            return entities
            
        except Exception as e:
            logger.error(f"Error retrieving entities by IDs: {e}")
            return []
    
    async def count_entities(self) -> int:
        """
        Get total count of entities in the collection
        
        Returns:
            Number of entities
        """
        if not self.client:
            return 0
            
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count or 0
        except Exception as e:
            logger.error(f"Error counting entities: {e}")
            return 0
    
    async def delete_entity(self, entity_id: str) -> bool:
        """
        Delete an entity from the collection
        
        Args:
            entity_id: ID of entity to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
            
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[entity_id]
                )
            )
            logger.debug(f"Deleted entity {entity_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting entity {entity_id}: {e}")
            return False
    
    async def clear_collection(self) -> bool:
        """
        Clear all entities from the collection
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
            
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter()
                )
            )
            logger.info(f"Cleared collection {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            return False
    
    def _point_to_entity(self, point) -> Optional[Entity]:
        """
        Convert Qdrant point to Entity object
        
        Args:
            point: Qdrant point with payload and vector
            
        Returns:
            Entity object or None if conversion fails
        """
        try:
            payload = point.payload
            
            # Parse source spans
            source_spans = []
            for span_data in payload.get("source_spans", []):
                from models.core import SourceSpan
                source_spans.append(SourceSpan(
                    doc_id=span_data["doc_id"],
                    start=span_data["start"],
                    end=span_data["end"]
                ))
            
            # Create entity
            entity = Entity(
                id=str(point.id),
                name=payload["name"],
                type=EntityType(payload["type"]),
                aliases=payload.get("aliases", []),
                embedding=point.vector if point.vector else [],
                salience=payload.get("salience", 0.0),
                source_spans=source_spans,
                summary=payload.get("summary", ""),
                created_at=datetime.fromisoformat(payload["created_at"]),
                updated_at=datetime.fromisoformat(payload["updated_at"])
            )
            
            return entity
            
        except Exception as e:
            logger.error(f"Error converting point to entity: {e}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Qdrant connection and collection
        
        Returns:
            Dictionary with health status information
        """
        health_info = {
            "connected": False,
            "collection_exists": False,
            "entity_count": 0,
            "error": None
        }
        
        try:
            if not self.client:
                health_info["error"] = "Client not initialized"
                return health_info
            
            # Test connection
            collections = self.client.get_collections()
            health_info["connected"] = True
            
            # Check collection
            collection_names = [col.name for col in collections.collections]
            if self.collection_name in collection_names:
                health_info["collection_exists"] = True
                health_info["entity_count"] = await self.count_entities()
            else:
                health_info["error"] = f"Collection {self.collection_name} does not exist"
                
        except Exception as e:
            health_info["error"] = str(e)
            
        return health_info
    
    async def close(self):
        """Close the Qdrant client connection"""
        if self.client:
            try:
                self.client.close()
                logger.info("Qdrant client connection closed")
            except Exception as e:
                logger.error(f"Error closing Qdrant client: {e}")
            finally:
                self.client = None