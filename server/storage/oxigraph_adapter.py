"""
Oxigraph RDF store adapter for relationship storage and graph traversal.
Handles triple storage, SPARQL queries, and neighborhood expansion.
"""

import logging
from typing import List, Optional, Dict, Any, Set, Tuple
from oxigraph import Store, NamedNode, Literal, BlankNode, Triple, Quad
import tempfile
import os
from datetime import datetime
import json
import asyncio

from models.core import Entity, Relationship, RelationType, Evidence

logger = logging.getLogger(__name__)


class OxigraphAdapter:
    """Adapter for Oxigraph RDF store operations"""
    
    def __init__(self, store_path: Optional[str] = None):
        """
        Initialize Oxigraph adapter
        
        Args:
            store_path: Path to persistent store (None for in-memory)
        """
        self.store_path = store_path
        self.store = None
        self._temp_dir = None
        
        # Define namespaces
        self.kg_ns = "http://knowledge-mapper.ai/kg/"
        self.rdf_ns = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        self.rdfs_ns = "http://www.w3.org/2000/01/rdf-schema#"
        
    async def connect(self) -> bool:
        """
        Initialize the RDF store
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            if self.store_path:
                # Use persistent store
                os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
                self.store = Store(self.store_path)
                logger.info(f"Initialized persistent Oxigraph store at {self.store_path}")
            else:
                # Use in-memory store for POC
                self.store = Store()
                logger.info("Initialized in-memory Oxigraph store")
            
            # Initialize basic schema
            await self._initialize_schema()
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Oxigraph store: {e}")
            return False
    
    async def _initialize_schema(self):
        """Initialize basic RDF schema and prefixes"""
        try:
            # Define basic entity and relationship types
            schema_triples = [
                # Entity type definitions
                (f"{self.kg_ns}Entity", f"{self.rdf_ns}type", f"{self.rdfs_ns}Class"),
                (f"{self.kg_ns}Concept", f"{self.rdfs_ns}subClassOf", f"{self.kg_ns}Entity"),
                (f"{self.kg_ns}Library", f"{self.rdfs_ns}subClassOf", f"{self.kg_ns}Entity"),
                (f"{self.kg_ns}Person", f"{self.rdfs_ns}subClassOf", f"{self.kg_ns}Entity"),
                (f"{self.kg_ns}Organization", f"{self.rdfs_ns}subClassOf", f"{self.kg_ns}Entity"),
                (f"{self.kg_ns}Paper", f"{self.rdfs_ns}subClassOf", f"{self.kg_ns}Entity"),
                (f"{self.kg_ns}System", f"{self.rdfs_ns}subClassOf", f"{self.kg_ns}Entity"),
                (f"{self.kg_ns}Metric", f"{self.rdfs_ns}subClassOf", f"{self.kg_ns}Entity"),
                
                # Property definitions
                (f"{self.kg_ns}name", f"{self.rdf_ns}type", f"{self.rdf_ns}Property"),
                (f"{self.kg_ns}type", f"{self.rdf_ns}type", f"{self.rdf_ns}Property"),
                (f"{self.kg_ns}salience", f"{self.rdf_ns}type", f"{self.rdf_ns}Property"),
                (f"{self.kg_ns}summary", f"{self.rdf_ns}type", f"{self.rdf_ns}Property"),
                (f"{self.kg_ns}confidence", f"{self.rdf_ns}type", f"{self.rdf_ns}Property"),
                (f"{self.kg_ns}evidence", f"{self.rdf_ns}type", f"{self.rdf_ns}Property"),
            ]
            
            for subject, predicate, obj in schema_triples:
                triple = Triple(
                    NamedNode(subject),
                    NamedNode(predicate),
                    NamedNode(obj)
                )
                self.store.add(triple)
                
            logger.debug("Initialized RDF schema")
            
        except Exception as e:
            logger.error(f"Error initializing schema: {e}")
            raise
    
    async def store_entity(self, entity: Entity) -> bool:
        """
        Store an entity as RDF triples
        
        Args:
            entity: Entity to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.store:
            logger.error("Oxigraph store not initialized")
            return False
            
        try:
            entity_uri = NamedNode(f"{self.kg_ns}entity/{entity.id}")
            
            # Core entity triples
            triples = [
                Triple(entity_uri, NamedNode(f"{self.rdf_ns}type"), NamedNode(f"{self.kg_ns}{entity.type.value}")),
                Triple(entity_uri, NamedNode(f"{self.kg_ns}name"), Literal(entity.name)),
                Triple(entity_uri, NamedNode(f"{self.kg_ns}type"), Literal(entity.type.value)),
                Triple(entity_uri, NamedNode(f"{self.kg_ns}salience"), Literal(str(entity.salience))),
                Triple(entity_uri, NamedNode(f"{self.kg_ns}summary"), Literal(entity.summary)),
                Triple(entity_uri, NamedNode(f"{self.kg_ns}created_at"), Literal(entity.created_at.isoformat())),
                Triple(entity_uri, NamedNode(f"{self.kg_ns}updated_at"), Literal(entity.updated_at.isoformat())),
            ]
            
            # Add aliases
            for alias in entity.aliases:
                triples.append(
                    Triple(entity_uri, NamedNode(f"{self.kg_ns}alias"), Literal(alias))
                )
            
            # Add source spans
            for i, span in enumerate(entity.source_spans):
                span_node = BlankNode(f"span_{entity.id}_{i}")
                triples.extend([
                    Triple(entity_uri, NamedNode(f"{self.kg_ns}source_span"), span_node),
                    Triple(span_node, NamedNode(f"{self.kg_ns}doc_id"), Literal(span.doc_id)),
                    Triple(span_node, NamedNode(f"{self.kg_ns}start"), Literal(str(span.start))),
                    Triple(span_node, NamedNode(f"{self.kg_ns}end"), Literal(str(span.end))),
                ])
            
            # Remove existing triples for this entity (upsert behavior)
            await self._remove_entity_triples(entity.id)
            
            # Add new triples
            for triple in triples:
                self.store.add(triple)
            
            logger.debug(f"Stored entity {entity.id} ({entity.name}) as RDF triples")
            return True
            
        except Exception as e:
            logger.error(f"Error storing entity {entity.id}: {e}")
            return False
    
    async def store_relationship(self, relationship: Relationship) -> bool:
        """
        Store a relationship as RDF triples
        
        Args:
            relationship: Relationship to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.store:
            logger.error("Oxigraph store not initialized")
            return False
            
        try:
            from_uri = NamedNode(f"{self.kg_ns}entity/{relationship.from_entity}")
            to_uri = NamedNode(f"{self.kg_ns}entity/{relationship.to_entity}")
            predicate_uri = NamedNode(f"{self.kg_ns}{relationship.predicate.value}")
            
            # Create relationship identifier
            rel_id = f"{relationship.from_entity}_{relationship.predicate.value}_{relationship.to_entity}"
            rel_uri = NamedNode(f"{self.kg_ns}relationship/{rel_id}")
            
            # Core relationship triples
            triples = [
                # Main relationship triple
                Triple(from_uri, predicate_uri, to_uri),
                
                # Relationship metadata
                Triple(rel_uri, NamedNode(f"{self.rdf_ns}type"), NamedNode(f"{self.kg_ns}Relationship")),
                Triple(rel_uri, NamedNode(f"{self.kg_ns}from"), from_uri),
                Triple(rel_uri, NamedNode(f"{self.kg_ns}to"), to_uri),
                Triple(rel_uri, NamedNode(f"{self.kg_ns}predicate"), Literal(relationship.predicate.value)),
                Triple(rel_uri, NamedNode(f"{self.kg_ns}confidence"), Literal(str(relationship.confidence))),
                Triple(rel_uri, NamedNode(f"{self.kg_ns}directional"), Literal(str(relationship.directional).lower())),
                Triple(rel_uri, NamedNode(f"{self.kg_ns}created_at"), Literal(relationship.created_at.isoformat())),
            ]
            
            # Add evidence
            for i, evidence in enumerate(relationship.evidence):
                evidence_node = BlankNode(f"evidence_{rel_id}_{i}")
                triples.extend([
                    Triple(rel_uri, NamedNode(f"{self.kg_ns}evidence"), evidence_node),
                    Triple(evidence_node, NamedNode(f"{self.kg_ns}doc_id"), Literal(evidence.doc_id)),
                    Triple(evidence_node, NamedNode(f"{self.kg_ns}quote"), Literal(evidence.quote)),
                    Triple(evidence_node, NamedNode(f"{self.kg_ns}offset"), Literal(str(evidence.offset))),
                ])
            
            # Remove existing relationship triples (upsert behavior)
            await self._remove_relationship_triples(rel_id)
            
            # Add new triples
            for triple in triples:
                self.store.add(triple)
            
            logger.debug(f"Stored relationship {relationship.from_entity} -> {relationship.to_entity}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing relationship: {e}")
            return False
    
    async def get_neighbors(
        self, 
        entity_id: str, 
        hops: int = 1, 
        limit: int = 200,
        relationship_types: Optional[List[RelationType]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get neighboring entities using SPARQL graph traversal
        
        Args:
            entity_id: Central entity ID
            hops: Number of hops to traverse (1 or 2)
            limit: Maximum number of results
            relationship_types: Optional filter for relationship types
            
        Returns:
            List of neighbor information dictionaries
        """
        if not self.store:
            logger.error("Oxigraph store not initialized")
            return []
            
        try:
            entity_uri = f"{self.kg_ns}entity/{entity_id}"
            
            # Build relationship type filter
            type_filter = ""
            if relationship_types:
                type_values = " ".join([f'"{rt.value}"' for rt in relationship_types])
                type_filter = f"FILTER(?predicate_name IN ({type_values}))"
            
            if hops == 1:
                # 1-hop neighbors
                sparql_query = f"""
                PREFIX kg: <{self.kg_ns}>
                PREFIX rdf: <{self.rdf_ns}>
                
                SELECT DISTINCT ?neighbor ?neighbor_name ?neighbor_type ?predicate_name ?confidence ?directional
                WHERE {{
                    {{
                        <{entity_uri}> ?predicate ?neighbor .
                        ?neighbor kg:name ?neighbor_name .
                        ?neighbor kg:type ?neighbor_type .
                        
                        # Get relationship metadata
                        ?rel_uri kg:from <{entity_uri}> ;
                                kg:to ?neighbor ;
                                kg:predicate ?predicate_name ;
                                kg:confidence ?confidence ;
                                kg:directional ?directional .
                    }}
                    UNION
                    {{
                        ?neighbor ?predicate <{entity_uri}> .
                        ?neighbor kg:name ?neighbor_name .
                        ?neighbor kg:type ?neighbor_type .
                        
                        # Get relationship metadata (reverse direction)
                        ?rel_uri kg:from ?neighbor ;
                                kg:to <{entity_uri}> ;
                                kg:predicate ?predicate_name ;
                                kg:confidence ?confidence ;
                                kg:directional ?directional .
                    }}
                    
                    {type_filter}
                }}
                LIMIT {limit}
                """
            else:
                # 2-hop neighbors
                sparql_query = f"""
                PREFIX kg: <{self.kg_ns}>
                PREFIX rdf: <{self.rdf_ns}>
                
                SELECT DISTINCT ?neighbor ?neighbor_name ?neighbor_type ?predicate_name ?confidence ?directional ?hop_count
                WHERE {{
                    {{
                        # 1-hop
                        <{entity_uri}> ?predicate1 ?intermediate .
                        ?intermediate ?predicate2 ?neighbor .
                        ?neighbor kg:name ?neighbor_name .
                        ?neighbor kg:type ?neighbor_type .
                        
                        ?rel_uri kg:from ?intermediate ;
                                kg:to ?neighbor ;
                                kg:predicate ?predicate_name ;
                                kg:confidence ?confidence ;
                                kg:directional ?directional .
                        
                        BIND(2 AS ?hop_count)
                        FILTER(?neighbor != <{entity_uri}>)
                    }}
                    UNION
                    {{
                        # Direct neighbors (1-hop)
                        <{entity_uri}> ?predicate ?neighbor .
                        ?neighbor kg:name ?neighbor_name .
                        ?neighbor kg:type ?neighbor_type .
                        
                        ?rel_uri kg:from <{entity_uri}> ;
                                kg:to ?neighbor ;
                                kg:predicate ?predicate_name ;
                                kg:confidence ?confidence ;
                                kg:directional ?directional .
                        
                        BIND(1 AS ?hop_count)
                    }}
                    
                    {type_filter}
                }}
                ORDER BY ?hop_count ?confidence
                LIMIT {limit}
                """
            
            # Execute SPARQL query
            results = []
            for result in self.store.query(sparql_query):
                neighbor_info = {
                    "entity_id": str(result["neighbor"]).replace(f"{self.kg_ns}entity/", ""),
                    "name": str(result["neighbor_name"]),
                    "type": str(result["neighbor_type"]),
                    "predicate": str(result["predicate_name"]),
                    "confidence": float(str(result["confidence"])),
                    "directional": str(result["directional"]).lower() == "true",
                    "hop_count": int(str(result.get("hop_count", 1)))
                }
                results.append(neighbor_info)
            
            logger.debug(f"Found {len(results)} neighbors for entity {entity_id} within {hops} hops")
            return results
            
        except Exception as e:
            logger.error(f"Error getting neighbors for {entity_id}: {e}")
            return []
    
    async def get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get all relationships for a specific entity
        
        Args:
            entity_id: Entity ID
            
        Returns:
            List of relationship information
        """
        if not self.store:
            return []
            
        try:
            entity_uri = f"{self.kg_ns}entity/{entity_id}"
            
            sparql_query = f"""
            PREFIX kg: <{self.kg_ns}>
            
            SELECT ?from_entity ?to_entity ?predicate ?confidence ?directional ?evidence_quote ?evidence_doc
            WHERE {{
                ?rel_uri kg:from ?from_entity ;
                        kg:to ?to_entity ;
                        kg:predicate ?predicate ;
                        kg:confidence ?confidence ;
                        kg:directional ?directional .
                
                OPTIONAL {{
                    ?rel_uri kg:evidence ?evidence .
                    ?evidence kg:quote ?evidence_quote ;
                             kg:doc_id ?evidence_doc .
                }}
                
                FILTER(?from_entity = <{entity_uri}> || ?to_entity = <{entity_uri}>)
            }}
            """
            
            relationships = []
            for result in self.store.query(sparql_query):
                rel_info = {
                    "from_entity": str(result["from_entity"]).replace(f"{self.kg_ns}entity/", ""),
                    "to_entity": str(result["to_entity"]).replace(f"{self.kg_ns}entity/", ""),
                    "predicate": str(result["predicate"]),
                    "confidence": float(str(result["confidence"])),
                    "directional": str(result["directional"]).lower() == "true",
                    "evidence": []
                }
                
                if result.get("evidence_quote"):
                    rel_info["evidence"].append({
                        "quote": str(result["evidence_quote"]),
                        "doc_id": str(result["evidence_doc"])
                    })
                
                relationships.append(rel_info)
            
            return relationships
            
        except Exception as e:
            logger.error(f"Error getting relationships for {entity_id}: {e}")
            return []
    
    async def query_sparql(self, sparql_query: str) -> List[Dict[str, Any]]:
        """
        Execute a custom SPARQL query
        
        Args:
            sparql_query: SPARQL query string
            
        Returns:
            List of query results
        """
        if not self.store:
            return []
            
        try:
            results = []
            for result in self.store.query(sparql_query):
                # Convert result to dictionary
                result_dict = {}
                for var_name in result:
                    result_dict[var_name] = str(result[var_name])
                results.append(result_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"Error executing SPARQL query: {e}")
            return []
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the RDF graph
        
        Returns:
            Dictionary with graph statistics
        """
        if not self.store:
            return {}
            
        try:
            stats = {}
            
            # Count entities by type
            entity_count_query = f"""
            PREFIX kg: <{self.kg_ns}>
            
            SELECT ?type (COUNT(?entity) AS ?count)
            WHERE {{
                ?entity kg:type ?type .
            }}
            GROUP BY ?type
            """
            
            entity_counts = {}
            for result in self.store.query(entity_count_query):
                entity_type = str(result["type"])
                count = int(str(result["count"]))
                entity_counts[entity_type] = count
            
            stats["entity_counts"] = entity_counts
            stats["total_entities"] = sum(entity_counts.values())
            
            # Count relationships by type
            rel_count_query = f"""
            PREFIX kg: <{self.kg_ns}>
            
            SELECT ?predicate (COUNT(?rel) AS ?count)
            WHERE {{
                ?rel kg:predicate ?predicate .
            }}
            GROUP BY ?predicate
            """
            
            relationship_counts = {}
            for result in self.store.query(rel_count_query):
                predicate = str(result["predicate"])
                count = int(str(result["count"]))
                relationship_counts[predicate] = count
            
            stats["relationship_counts"] = relationship_counts
            stats["total_relationships"] = sum(relationship_counts.values())
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting graph statistics: {e}")
            return {}
    
    async def export_graph(self) -> Dict[str, Any]:
        """
        Export the entire graph as structured data
        
        Returns:
            Dictionary containing all entities and relationships
        """
        if not self.store:
            return {"entities": [], "relationships": []}
            
        try:
            # Export entities
            entities_query = f"""
            PREFIX kg: <{self.kg_ns}>
            
            SELECT ?entity ?name ?type ?salience ?summary
            WHERE {{
                ?entity kg:name ?name ;
                       kg:type ?type ;
                       kg:salience ?salience ;
                       kg:summary ?summary .
            }}
            """
            
            entities = []
            for result in self.store.query(entities_query):
                entity_id = str(result["entity"]).replace(f"{self.kg_ns}entity/", "")
                entities.append({
                    "id": entity_id,
                    "name": str(result["name"]),
                    "type": str(result["type"]),
                    "salience": float(str(result["salience"])),
                    "summary": str(result["summary"])
                })
            
            # Export relationships
            relationships_query = f"""
            PREFIX kg: <{self.kg_ns}>
            
            SELECT ?from_entity ?to_entity ?predicate ?confidence ?directional
            WHERE {{
                ?rel kg:from ?from_entity ;
                    kg:to ?to_entity ;
                    kg:predicate ?predicate ;
                    kg:confidence ?confidence ;
                    kg:directional ?directional .
            }}
            """
            
            relationships = []
            for result in self.store.query(relationships_query):
                relationships.append({
                    "from": str(result["from_entity"]).replace(f"{self.kg_ns}entity/", ""),
                    "to": str(result["to_entity"]).replace(f"{self.kg_ns}entity/", ""),
                    "predicate": str(result["predicate"]),
                    "confidence": float(str(result["confidence"])),
                    "directional": str(result["directional"]).lower() == "true"
                })
            
            return {
                "entities": entities,
                "relationships": relationships,
                "exported_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error exporting graph: {e}")
            return {"entities": [], "relationships": []}
    
    async def _remove_entity_triples(self, entity_id: str):
        """Remove all triples for a specific entity"""
        try:
            entity_uri = NamedNode(f"{self.kg_ns}entity/{entity_id}")
            
            # Remove triples where entity is subject
            for triple in self.store.quads_for_pattern(entity_uri, None, None):
                self.store.remove(triple)
            
            # Remove triples where entity is object
            for triple in self.store.quads_for_pattern(None, None, entity_uri):
                self.store.remove(triple)
                
        except Exception as e:
            logger.error(f"Error removing entity triples for {entity_id}: {e}")
    
    async def _remove_relationship_triples(self, rel_id: str):
        """Remove all triples for a specific relationship"""
        try:
            rel_uri = NamedNode(f"{self.kg_ns}relationship/{rel_id}")
            
            # Remove relationship metadata triples
            for triple in self.store.quads_for_pattern(rel_uri, None, None):
                self.store.remove(triple)
                
        except Exception as e:
            logger.error(f"Error removing relationship triples for {rel_id}: {e}")
    
    async def clear_graph(self) -> bool:
        """
        Clear all data from the graph
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.store:
            return False
            
        try:
            # Remove all triples
            for triple in self.store:
                self.store.remove(triple)
            
            # Reinitialize schema
            await self._initialize_schema()
            
            logger.info("Cleared RDF graph")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing graph: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Oxigraph store
        
        Returns:
            Dictionary with health status information
        """
        health_info = {
            "initialized": False,
            "entity_count": 0,
            "relationship_count": 0,
            "error": None
        }
        
        try:
            if not self.store:
                health_info["error"] = "Store not initialized"
                return health_info
            
            health_info["initialized"] = True
            
            # Get statistics
            stats = await self.get_graph_statistics()
            health_info["entity_count"] = stats.get("total_entities", 0)
            health_info["relationship_count"] = stats.get("total_relationships", 0)
            
        except Exception as e:
            health_info["error"] = str(e)
            
        return health_info
    
    async def close(self):
        """Close the Oxigraph store"""
        if self.store:
            try:
                # Oxigraph store doesn't need explicit closing
                logger.info("Oxigraph store closed")
            except Exception as e:
                logger.error(f"Error closing Oxigraph store: {e}")
            finally:
                self.store = None
                
        if self._temp_dir:
            try:
                import shutil
                shutil.rmtree(self._temp_dir)
            except Exception as e:
                logger.error(f"Error cleaning up temp directory: {e}")