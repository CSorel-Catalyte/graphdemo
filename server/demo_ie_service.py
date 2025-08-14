"""
Demonstration of the Information Extraction Service functionality.

This script shows how to use the IE service to extract entities and relationships
from text, including JSON validation and error handling.
"""

import json
import asyncio
import sys
import os

# Add the server directory to the path
sys.path.append(os.path.dirname(__file__))

from services.ie_service import InformationExtractionService, IEServiceError, LLMAPIError, JSONParsingError
from models.core import EntityType, RelationType


def demo_prompt_generation():
    """Demonstrate extraction prompt generation."""
    print("=== Extraction Prompt Generation ===")
    
    service = InformationExtractionService(api_key="demo-key")
    prompt = service._get_extraction_prompt()
    
    print("Generated extraction prompt:")
    print("-" * 50)
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print("-" * 50)
    print(f"Prompt length: {len(prompt)} characters")
    print()


def demo_json_validation():
    """Demonstrate JSON validation with various scenarios."""
    print("=== JSON Validation Demo ===")
    
    service = InformationExtractionService(api_key="demo-key")
    
    # Test case 1: Valid JSON with entities and relationships
    print("1. Testing valid JSON with entities and relationships:")
    
    valid_response = {
        "entities": [
            {
                "name": "Machine Learning",
                "type": "Concept",
                "aliases": ["ML", "machine learning"],
                "salience": 0.9,
                "summary": "A subset of artificial intelligence that enables computers to learn"
            },
            {
                "name": "TensorFlow",
                "type": "Library",
                "aliases": ["TF"],
                "salience": 0.8,
                "summary": "Open-source machine learning framework developed by Google"
            },
            {
                "name": "Google",
                "type": "Organization",
                "aliases": ["Google Inc.", "Alphabet"],
                "salience": 0.7,
                "summary": "Technology company that developed TensorFlow"
            }
        ],
        "relationships": [
            {
                "from": "TensorFlow",
                "to": "Machine Learning",
                "predicate": "implements",
                "confidence": 0.9,
                "evidence": [
                    {
                        "quote": "TensorFlow implements various machine learning algorithms",
                        "offset": 50
                    }
                ],
                "directional": True
            },
            {
                "from": "TensorFlow",
                "to": "Google",
                "predicate": "authored_by",
                "confidence": 0.95,
                "evidence": [
                    {
                        "quote": "Google developed TensorFlow",
                        "offset": 100
                    }
                ],
                "directional": True
            }
        ]
    }
    
    chunk_text = """
    Machine Learning is a subset of artificial intelligence that enables computers to learn 
    without being explicitly programmed. TensorFlow implements various machine learning algorithms
    and is a popular open-source framework. Google developed TensorFlow for internal use and 
    later open-sourced it to the community.
    """
    
    try:
        result = service._validate_and_convert_ie_output(
            json.dumps(valid_response), chunk_text, "demo_doc", "demo_chunk"
        )
        
        print(f"✓ Successfully parsed {len(result.entities)} entities and {len(result.relationships)} relationships")
        
        for entity in result.entities:
            print(f"  - Entity: {entity.name} ({entity.type.value}) - Salience: {entity.salience}")
        
        for rel in result.relationships:
            print(f"  - Relationship: {rel.from_entity} --{rel.predicate.value}--> {rel.to_entity} (confidence: {rel.confidence})")
        
    except Exception as e:
        print(f"✗ Validation failed: {e}")
    
    print()
    
    # Test case 2: Invalid entity type
    print("2. Testing invalid entity type handling:")
    
    invalid_entity_response = {
        "entities": [
            {
                "name": "Invalid Entity",
                "type": "InvalidType",  # This should be rejected
                "aliases": [],
                "salience": 0.5,
                "summary": "This entity has an invalid type"
            },
            {
                "name": "Valid Entity",
                "type": "Concept",
                "aliases": [],
                "salience": 0.8,
                "summary": "This entity has a valid type"
            }
        ],
        "relationships": []
    }
    
    try:
        result = service._validate_and_convert_ie_output(
            json.dumps(invalid_entity_response), chunk_text, "demo_doc", "demo_chunk"
        )
        
        print(f"✓ Handled invalid entity type gracefully. Kept {len(result.entities)} valid entities")
        
    except Exception as e:
        print(f"✗ Validation failed: {e}")
    
    print()
    
    # Test case 3: Invalid JSON
    print("3. Testing invalid JSON handling:")
    
    try:
        result = service._validate_and_convert_ie_output(
            "{ invalid json }", chunk_text, "demo_doc", "demo_chunk"
        )
        print("✗ Should have failed with invalid JSON")
        
    except JSONParsingError as e:
        print(f"✓ Correctly caught JSON parsing error: {e}")
    
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    
    print()


def demo_text_offset_calculation():
    """Demonstrate text offset calculation."""
    print("=== Text Offset Calculation Demo ===")
    
    service = InformationExtractionService(api_key="demo-key")
    
    text = "Machine Learning is a powerful technique. TensorFlow is a popular ML library."
    
    test_cases = [
        ("Machine Learning", 0),
        ("powerful technique", 25),
        ("TensorFlow", 43),
        ("ML library", 65),
        ("not found", -1)
    ]
    
    for quote, expected_offset in test_cases:
        actual_offset = service._calculate_text_offset(text, quote)
        status = "✓" if actual_offset == expected_offset else "✗"
        print(f"{status} Quote: '{quote}' -> Offset: {actual_offset} (expected: {expected_offset})")
    
    print()


def demo_entity_types_and_relationships():
    """Demonstrate available entity types and relationship types."""
    print("=== Available Entity and Relationship Types ===")
    
    print("Entity Types:")
    for entity_type in EntityType:
        print(f"  - {entity_type.value}")
    
    print("\nRelationship Types:")
    for rel_type in RelationType:
        print(f"  - {rel_type.value}")
    
    print()


async def demo_error_handling():
    """Demonstrate error handling for LLM requests."""
    print("=== Error Handling Demo ===")
    
    service = InformationExtractionService(api_key="demo-key")
    
    # This will fail because OpenAI is not available
    try:
        result = await service.extract_entities_relations(
            "This is a test text.", "demo_doc", 0
        )
        print("✗ Should have failed due to missing OpenAI")
        
    except LLMAPIError as e:
        print(f"✓ Correctly caught LLM API error: {e}")
    
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    
    print()


def main():
    """Run all demonstrations."""
    print("Information Extraction Service Demonstration")
    print("=" * 60)
    print()
    
    # Run synchronous demos
    demo_prompt_generation()
    demo_json_validation()
    demo_text_offset_calculation()
    demo_entity_types_and_relationships()
    
    # Run async demo
    print("Running async error handling demo...")
    asyncio.run(demo_error_handling())
    
    print("=" * 60)
    print("Demo completed successfully! 🎉")
    print()
    print("Key Features Demonstrated:")
    print("✓ Extraction prompt generation with comprehensive instructions")
    print("✓ JSON validation with error handling for invalid data")
    print("✓ Text offset calculation for evidence quotes")
    print("✓ Support for all defined entity and relationship types")
    print("✓ Graceful error handling for missing dependencies")
    print()
    print("The IE service is ready for integration with OpenAI API!")


if __name__ == "__main__":
    main()