"""
Tests for the Information Extraction Service.

This module contains comprehensive tests for the IE service including
JSON validation, error handling, retry logic, and integration tests.
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

try:
    from openai import AsyncOpenAI
    from openai.types.chat import ChatCompletion, ChatCompletionMessage
    from openai.types.chat.chat_completion import Choice
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from services.ie_service import (
    InformationExtractionService,
    IEServiceError,
    LLMAPIError,
    JSONParsingError,
    extract_entities_relations
)
from models.core import IEResult, Entity, Relationship, EntityType, RelationType


class TestInformationExtractionService:
    """Test cases for InformationExtractionService class."""
    
    @pytest.fixture
    def ie_service(self):
        """Create an IE service instance for testing."""
        return InformationExtractionService(
            api_key="test-api-key",
            model="gpt-3.5-turbo-1106",
            max_retries=2,
            base_delay=0.1,  # Fast retries for testing
            max_delay=1.0
        )
    
    @pytest.fixture
    def sample_text(self):
        """Sample text for testing extraction."""
        return """
        Machine Learning is a subset of Artificial Intelligence that enables computers to learn 
        without being explicitly programmed. TensorFlow is a popular library that implements 
        various ML algorithms. Google developed TensorFlow for internal use and later open-sourced it.
        """
    
    @pytest.fixture
    def valid_llm_response(self):
        """Valid LLM response for testing."""
        return {
            "entities": [
                {
                    "name": "Machine Learning",
                    "type": "Concept",
                    "aliases": ["ML"],
                    "salience": 0.9,
                    "summary": "A subset of AI that enables computers to learn automatically"
                },
                {
                    "name": "TensorFlow",
                    "type": "Library",
                    "aliases": ["TF"],
                    "salience": 0.8,
                    "summary": "Popular machine learning library developed by Google"
                },
                {
                    "name": "Google",
                    "type": "Organization",
                    "aliases": [],
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
                            "quote": "TensorFlow is a popular library that implements various ML algorithms",
                            "offset": 120
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
                            "offset": 200
                        }
                    ],
                    "directional": True
                }
            ]
        }
    
    def test_init(self):
        """Test service initialization."""
        service = InformationExtractionService(
            api_key="test-key",
            model="gpt-4-1106-preview",
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0
        )
        
        assert service.model == "gpt-4-1106-preview"
        assert service.max_retries == 5
        assert service.base_delay == 2.0
        assert service.max_delay == 120.0
        assert isinstance(service.client, AsyncOpenAI)
    
    def test_get_extraction_prompt(self, ie_service):
        """Test extraction prompt generation."""
        prompt = ie_service._get_extraction_prompt()
        
        assert "information extraction" in prompt.lower()
        assert "json" in prompt.lower()
        assert "entities" in prompt.lower()
        assert "relationships" in prompt.lower()
        
        # Check that all entity types are mentioned
        for entity_type in EntityType:
            assert entity_type.value in prompt
        
        # Check that all relationship types are mentioned
        for rel_type in RelationType:
            assert rel_type.value in prompt
    
    def test_calculate_text_offset(self, ie_service):
        """Test text offset calculation."""
        text = "This is a sample text with some content."
        
        # Test exact match
        assert ie_service._calculate_text_offset(text, "sample text") == 10
        
        # Test not found
        assert ie_service._calculate_text_offset(text, "not found") == -1
        
        # Test empty quote
        assert ie_service._calculate_text_offset(text, "") == 0
    
    def test_validate_and_convert_ie_output_valid(self, ie_service, valid_llm_response, sample_text):
        """Test validation and conversion of valid LLM output."""
        raw_json = json.dumps(valid_llm_response)
        
        result = ie_service._validate_and_convert_ie_output(
            raw_json, sample_text, "test_doc", "test_chunk"
        )
        
        assert isinstance(result, IEResult)
        assert result.doc_id == "test_doc"
        assert result.chunk_id == "test_chunk"
        assert len(result.entities) == 3
        assert len(result.relationships) == 2
        
        # Check entity properties
        ml_entity = next(e for e in result.entities if e.name == "Machine Learning")
        assert ml_entity.type == EntityType.CONCEPT
        assert "ML" in ml_entity.aliases
        assert ml_entity.salience == 0.9
        assert len(ml_entity.source_spans) == 1
        
        # Check relationship properties
        impl_rel = next(r for r in result.relationships if r.predicate == RelationType.IMPLEMENTS)
        assert impl_rel.confidence == 0.9
        assert impl_rel.directional is True
        assert len(impl_rel.evidence) == 1
        assert impl_rel.evidence[0].quote == "TensorFlow is a popular library that implements various ML algorithms"
    
    def test_validate_and_convert_ie_output_invalid_json(self, ie_service, sample_text):
        """Test handling of invalid JSON."""
        with pytest.raises(JSONParsingError, match="Invalid JSON"):
            ie_service._validate_and_convert_ie_output(
                "invalid json", sample_text, "test_doc", "test_chunk"
            )
    
    def test_validate_and_convert_ie_output_invalid_entity_type(self, ie_service, sample_text):
        """Test handling of invalid entity types."""
        invalid_response = {
            "entities": [
                {
                    "name": "Test Entity",
                    "type": "InvalidType",  # Invalid type
                    "aliases": [],
                    "salience": 0.5,
                    "summary": "Test summary"
                }
            ],
            "relationships": []
        }
        
        result = ie_service._validate_and_convert_ie_output(
            json.dumps(invalid_response), sample_text, "test_doc", "test_chunk"
        )
        
        # Should skip invalid entity
        assert len(result.entities) == 0
    
    def test_validate_and_convert_ie_output_invalid_relationship_type(self, ie_service, sample_text):
        """Test handling of invalid relationship types."""
        invalid_response = {
            "entities": [
                {
                    "name": "Entity1",
                    "type": "Concept",
                    "aliases": [],
                    "salience": 0.5,
                    "summary": "Test entity"
                },
                {
                    "name": "Entity2",
                    "type": "Library",
                    "aliases": [],
                    "salience": 0.5,
                    "summary": "Test entity"
                }
            ],
            "relationships": [
                {
                    "from": "Entity1",
                    "to": "Entity2",
                    "predicate": "invalid_relationship",  # Invalid type
                    "confidence": 0.8,
                    "evidence": [],
                    "directional": True
                }
            ]
        }
        
        result = ie_service._validate_and_convert_ie_output(
            json.dumps(invalid_response), sample_text, "test_doc", "test_chunk"
        )
        
        # Should have entities but skip invalid relationship
        assert len(result.entities) == 2
        assert len(result.relationships) == 0
    
    def test_validate_and_convert_ie_output_missing_entities_in_relationship(self, ie_service, sample_text):
        """Test handling of relationships referencing non-existent entities."""
        invalid_response = {
            "entities": [
                {
                    "name": "Entity1",
                    "type": "Concept",
                    "aliases": [],
                    "salience": 0.5,
                    "summary": "Test entity"
                }
            ],
            "relationships": [
                {
                    "from": "Entity1",
                    "to": "NonExistentEntity",  # References non-existent entity
                    "predicate": "relates_to",
                    "confidence": 0.8,
                    "evidence": [],
                    "directional": True
                }
            ]
        }
        
        result = ie_service._validate_and_convert_ie_output(
            json.dumps(invalid_response), sample_text, "test_doc", "test_chunk"
        )
        
        # Should have entity but skip invalid relationship
        assert len(result.entities) == 1
        assert len(result.relationships) == 0
    
    @pytest.mark.asyncio
    async def test_make_llm_request_success(self, ie_service, valid_llm_response):
        """Test successful LLM API request."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(valid_llm_response)
        
        with patch.object(ie_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await ie_service._make_llm_request("test text")
            
            assert result == json.dumps(valid_llm_response)
            mock_create.assert_called_once()
            
            # Check call arguments
            call_args = mock_create.call_args
            assert call_args[1]['model'] == ie_service.model
            assert call_args[1]['response_format'] == {"type": "json_object"}
            assert call_args[1]['temperature'] == 0.1
    
    @pytest.mark.asyncio
    async def test_make_llm_request_empty_response(self, ie_service):
        """Test handling of empty LLM response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        
        with patch.object(ie_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            with pytest.raises(LLMAPIError, match="Empty response from LLM"):
                await ie_service._make_llm_request("test text")
    
    @pytest.mark.asyncio
    async def test_make_llm_request_retry_logic(self, ie_service, valid_llm_response):
        """Test retry logic for failed LLM requests."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(valid_llm_response)
        
        with patch.object(ie_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            # First two calls fail, third succeeds
            mock_create.side_effect = [
                Exception("API Error 1"),
                Exception("API Error 2"),
                mock_response
            ]
            
            result = await ie_service._make_llm_request("test text")
            
            assert result == json.dumps(valid_llm_response)
            assert mock_create.call_count == 3
    
    @pytest.mark.asyncio
    async def test_make_llm_request_all_retries_fail(self, ie_service):
        """Test behavior when all retry attempts fail."""
        with patch.object(ie_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("Persistent API Error")
            
            with pytest.raises(LLMAPIError, match="All retry attempts failed"):
                await ie_service._make_llm_request("test text")
            
            # Should try max_retries + 1 times
            assert mock_create.call_count == ie_service.max_retries + 1
    
    @pytest.mark.asyncio
    async def test_extract_entities_relations_success(self, ie_service, sample_text, valid_llm_response):
        """Test successful entity and relationship extraction."""
        with patch.object(ie_service, '_make_llm_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = json.dumps(valid_llm_response)
            
            result = await ie_service.extract_entities_relations(sample_text, "test_doc", 0)
            
            assert isinstance(result, IEResult)
            assert result.doc_id == "test_doc"
            assert result.chunk_id == "test_doc_chunk_0"
            assert len(result.entities) == 3
            assert len(result.relationships) == 2
            assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_extract_entities_relations_empty_text(self, ie_service):
        """Test extraction from empty text."""
        result = await ie_service.extract_entities_relations("", "test_doc", 0)
        
        assert isinstance(result, IEResult)
        assert result.doc_id == "test_doc"
        assert result.chunk_id == "test_doc_chunk_0"
        assert len(result.entities) == 0
        assert len(result.relationships) == 0
    
    @pytest.mark.asyncio
    async def test_extract_entities_relations_llm_error(self, ie_service, sample_text):
        """Test handling of LLM API errors."""
        with patch.object(ie_service, '_make_llm_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = LLMAPIError("API Error")
            
            with pytest.raises(LLMAPIError):
                await ie_service.extract_entities_relations(sample_text, "test_doc", 0)
    
    @pytest.mark.asyncio
    async def test_extract_entities_relations_json_error(self, ie_service, sample_text):
        """Test handling of JSON parsing errors."""
        with patch.object(ie_service, '_make_llm_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = "invalid json"
            
            with pytest.raises(JSONParsingError):
                await ie_service.extract_entities_relations(sample_text, "test_doc", 0)
    
    @pytest.mark.asyncio
    async def test_extract_from_chunks_success(self, ie_service, valid_llm_response):
        """Test extraction from multiple chunks."""
        chunks = ["chunk 1 text", "chunk 2 text", "chunk 3 text"]
        
        with patch.object(ie_service, '_make_llm_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = json.dumps(valid_llm_response)
            
            results = await ie_service.extract_from_chunks(chunks, "test_doc", max_concurrent=2)
            
            assert len(results) == 3
            assert all(isinstance(r, IEResult) for r in results)
            assert all(r.doc_id == "test_doc" for r in results)
            
            # Check chunk IDs
            expected_chunk_ids = ["test_doc_chunk_0", "test_doc_chunk_1", "test_doc_chunk_2"]
            actual_chunk_ids = [r.chunk_id for r in results]
            assert actual_chunk_ids == expected_chunk_ids
    
    @pytest.mark.asyncio
    async def test_extract_from_chunks_empty_list(self, ie_service):
        """Test extraction from empty chunk list."""
        results = await ie_service.extract_from_chunks([], "test_doc")
        assert results == []
    
    @pytest.mark.asyncio
    async def test_extract_from_chunks_with_failures(self, ie_service, valid_llm_response):
        """Test extraction with some chunks failing."""
        chunks = ["chunk 1 text", "chunk 2 text", "chunk 3 text"]
        
        with patch.object(ie_service, 'extract_entities_relations', new_callable=AsyncMock) as mock_extract:
            # First chunk succeeds, second fails, third succeeds
            success_result = IEResult(entities=[], relationships=[], chunk_id="test", doc_id="test_doc")
            mock_extract.side_effect = [
                success_result,
                Exception("Extraction failed"),
                success_result
            ]
            
            results = await ie_service.extract_from_chunks(chunks, "test_doc")
            
            assert len(results) == 3
            assert all(isinstance(r, IEResult) for r in results)
            
            # Failed chunk should have empty result
            assert len(results[1].entities) == 0
            assert len(results[1].relationships) == 0
            assert results[1].chunk_id == "test_doc_chunk_1"


class TestConvenienceFunction:
    """Test cases for the convenience function."""
    
    @pytest.mark.asyncio
    async def test_extract_entities_relations_function(self, valid_llm_response):
        """Test the convenience function."""
        with patch('services.ie_service.InformationExtractionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            expected_result = IEResult(entities=[], relationships=[], chunk_id="test", doc_id="test_doc")
            mock_service.extract_entities_relations.return_value = expected_result
            
            result = await extract_entities_relations(
                "test text", "test_doc", "test-api-key", 0, "gpt-4-1106-preview"
            )
            
            assert result == expected_result
            mock_service_class.assert_called_once_with(api_key="test-api-key", model="gpt-4-1106-preview")
            mock_service.extract_entities_relations.assert_called_once_with("test text", "test_doc", 0)


if __name__ == "__main__":
    pytest.main([__file__])