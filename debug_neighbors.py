#!/usr/bin/env python3
"""
Debug script to check why neighbors aren't being found
"""

import asyncio
import sys
import os
sys.path.append('server')

from storage.oxigraph_adapter import OxigraphAdapter
from models.core import Entity, EntityType

async def debug_neighbors():
    """Debug the neighbors functionality"""
    
    # Initialize adapter
    adapter = OxigraphAdapter()
    await adapter.initialize()
    
    # Test entity ID from the frontend (BERT)
    entity_id = "19014118e42ab3c72800aa283d3a144c890189fc1cd3567ff927b12bd03ad43e"
    
    print(f"Debugging neighbors for entity: {entity_id}")
    
    # First, check if the entity exists
    entity = await adapter.get_entity(entity_id)
    if entity:
        print(f"✓ Found entity: {entity.name} ({entity.type})")
    else:
        print("✗ Entity not found!")
        return
    
    # Check what relationships exist in the store using a simple SPARQL query
    print("\n=== Checking all relationships in store ===")
    
    if adapter.store:
        # Simple query to see all triples
        simple_query = f"""
        PREFIX kg: <{adapter.kg_ns}>
        
        SELECT ?s ?p ?o
        WHERE {{
            ?s ?p ?o .
            FILTER(CONTAINS(STR(?s), "{entity_id}") || CONTAINS(STR(?o), "{entity_id}"))
        }}
        LIMIT 20
        """
        
        print("Triples involving this entity:")
        count = 0
        for result in adapter.store.query(simple_query):
            print(f"  {result['s']} -> {result['p']} -> {result['o']}")
            count += 1
        
        if count == 0:
            print("  No triples found involving this entity!")
        
        # Check for direct relationships (without metadata)
        direct_query = f"""
        PREFIX kg: <{adapter.kg_ns}>
        
        SELECT ?neighbor ?predicate
        WHERE {{
            {{
                <{adapter.kg_ns}entity/{entity_id}> ?predicate ?neighbor .
                FILTER(?predicate != <{adapter.rdf_ns}type>)
                FILTER(?predicate != <{adapter.kg_ns}name>)
                FILTER(?predicate != <{adapter.kg_ns}type>)
                FILTER(?predicate != <{adapter.kg_ns}aliases>)
                FILTER(?predicate != <{adapter.kg_ns}created_at>)
                FILTER(?predicate != <{adapter.kg_ns}updated_at>)
            }}
            UNION
            {{
                ?neighbor ?predicate <{adapter.kg_ns}entity/{entity_id}> .
                FILTER(?predicate != <{adapter.rdf_ns}type>)
                FILTER(?predicate != <{adapter.kg_ns}name>)
                FILTER(?predicate != <{adapter.kg_ns}type>)
                FILTER(?predicate != <{adapter.kg_ns}aliases>)
                FILTER(?predicate != <{adapter.kg_ns}created_at>)
                FILTER(?predicate != <{adapter.kg_ns}updated_at>)
            }}
        }}
        """
        
        print("\nDirect relationships:")
        count = 0
        for result in adapter.store.query(direct_query):
            print(f"  {result['neighbor']} via {result['predicate']}")
            count += 1
        
        if count == 0:
            print("  No direct relationships found!")
    
    # Try the actual get_neighbors function
    print("\n=== Testing get_neighbors function ===")
    neighbors = await adapter.get_neighbors(entity_id, hops=1, limit=10)
    print(f"get_neighbors returned {len(neighbors)} results:")
    for neighbor in neighbors:
        print(f"  {neighbor}")

if __name__ == "__main__":
    asyncio.run(debug_neighbors())