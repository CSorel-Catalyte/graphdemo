"""
Integration test for IE service to verify it can be imported and basic functionality works.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_ie_service_import():
    """Test that IE service can be imported."""
    try:
        from services.ie_service import InformationExtractionService, IEServiceError, LLMAPIError, JSONParsingError
        print("✓ IE service imports successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import IE service: {e}")
        return False


def test_ie_service_initialization():
    """Test that IE service can be initialized."""
    try:
        from services.ie_service import InformationExtractionService
        
        service = InformationExtractionService(
            api_key="test-key",
            model="gpt-3.5-turbo-1106",
            max_retries=2,
            base_delay=0.1
        )
        
        assert service.model == "gpt-3.5-turbo-1106"
        assert service.max_retries == 2
        assert service.base_delay == 0.1
        
        print("✓ IE service initializes correctly")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize IE service: {e}")
        return False


def test_prompt_generation():
    """Test that extraction prompt can be generated."""
    try:
        from services.ie_service import InformationExtractionService
        
        service = InformationExtractionService(api_key="test-key")
        prompt = service._get_extraction_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should be a substantial prompt
        assert "entities" in prompt.lower()
        assert "relationships" in prompt.lower()
        assert "json" in prompt.lower()
        
        print("✓ Extraction prompt generates correctly")
        return True
    except Exception as e:
        print(f"✗ Failed to generate extraction prompt: {e}")
        return False


def test_text_offset_calculation():
    """Test text offset calculation."""
    try:
        from services.ie_service import InformationExtractionService
        
        service = InformationExtractionService(api_key="test-key")
        
        text = "This is a sample text with some content."
        offset = service._calculate_text_offset(text, "sample text")
        
        assert offset == 10  # "sample text" starts at position 10
        
        # Test not found case
        offset_not_found = service._calculate_text_offset(text, "not found")
        assert offset_not_found == -1
        
        print("✓ Text offset calculation works correctly")
        return True
    except Exception as e:
        print(f"✗ Failed text offset calculation: {e}")
        return False


def test_json_validation_basic():
    """Test basic JSON validation without LLM calls."""
    try:
        from services.ie_service import InformationExtractionService
        import json
        
        service = InformationExtractionService(api_key="test-key")
        
        # Test valid JSON structure
        valid_response = {
            "entities": [
                {
                    "name": "Test Entity",
                    "type": "Concept",
                    "aliases": ["alias"],
                    "salience": 0.8,
                    "summary": "Test summary"
                }
            ],
            "relationships": []
        }
        
        raw_json = json.dumps(valid_response)
        chunk_text = "Test entity appears in this text."
        
        result = service._validate_and_convert_ie_output(
            raw_json, chunk_text, "test_doc", "test_chunk"
        )
        
        assert result.doc_id == "test_doc"
        assert result.chunk_id == "test_chunk"
        assert len(result.entities) == 1
        assert result.entities[0].name == "Test Entity"
        
        print("✓ JSON validation works correctly")
        return True
    except Exception as e:
        print(f"✗ JSON validation failed: {e}")
        return False


def test_invalid_json_handling():
    """Test handling of invalid JSON."""
    try:
        from services.ie_service import InformationExtractionService, JSONParsingError
        
        service = InformationExtractionService(api_key="test-key")
        
        try:
            service._validate_and_convert_ie_output(
                "invalid json", "test text", "test_doc", "test_chunk"
            )
            print("✗ Should have raised JSONParsingError")
            return False
        except JSONParsingError:
            print("✓ Invalid JSON handling works correctly")
            return True
    except Exception as e:
        print(f"✗ Invalid JSON handling test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("Running IE Service Integration Tests...")
    print("=" * 50)
    
    tests = [
        test_ie_service_import,
        test_ie_service_initialization,
        test_prompt_generation,
        test_text_offset_calculation,
        test_json_validation_basic,
        test_invalid_json_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)