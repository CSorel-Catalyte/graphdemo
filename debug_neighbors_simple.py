#!/usr/bin/env python3
"""
Simple debug script to check neighbors functionality
"""

import asyncio
import sys
import os
sys.path.append('server')

from storage.oxigraph_adapter import OxigraphAdapter

async def debug_neighbors():
    """Debug the neighbors functionality"""
    
    adapter = OxigraphAdapter()
    await adapter.initialize()
    
    # BERT entity ID from frontend
    entity_id = "19014118e42ab3c72800aa283d3a144c890189fc1cd3567ff927b12bd03ad43e"
    
    print(f"Debugging neighbors for entity: {entity_id}")
    
    # Check if entity exists
    entity = await adapter.get_entity(entity_id)
    if entity:
        print(f"✓ Found entity: {entity.name} ({entity.type})")
    else:
        print("✗ Entity not found!")
        return
    
    # Check direct relationships with simple query
    if adapter.store:
        entity_uri = f"{adapter.kg_ns}entity/{entity_id}"
        
        # Very simple query - just find anything connected
        simple_query = f"""
        SELECT ?s ?p ?o
        WHERE {{
            {{ <{entity_uri}> ?p ?o }}
            UNION
            {{ ?s ?p <{entity_uri}> }}
        }}
        LIMIT 50
        """
        
        print("\nAll triples involving this entity:")
        results = list(adapter.store.query(simple_query))
        print(f"Found {len(results)} triples")
        
        for i, result in enumerate(results[:10]):  # Show first 10
            print(f"  {i+1}. {result['s']} -> {result['p']} -> {result['o']}")
        
        if len(results) > 10:
            print(f"  ... and {len(results) - 10} more")
    
    # Test get_neighbors
    print(f"\nTesting get_neighbors:")
    neighbors = await adapter.get_neighbors(entity_id, hops=1, limit=10)
    print(f"Found {len(neighbors)} neighbors")
    
    for neighbor in neighbors:
        print(f"  - {neighbor}")

if __name__ == "__main__":
    asyncio.run(debug_neighbors())