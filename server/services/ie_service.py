"""
Information Extraction Service using OpenAI API.

This module provides LLM-based entity and relationship extraction from text chunks
with strict JSON parsing, retry logic, and comprehensive error handling.
"""

import json
import time
import asyncio
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

from pydantic import ValidationError

from models.core import Entity, Relationship, IEResult, EntityType, RelationType, Evidence, SourceSpan
from utils.error_handling import (
    error_handler, with_retry, handle_graceful_degradation,
    RetryConfig, ErrorClassifier
)


# Configure logging
logger = logging.getLogger(__name__)


class IEServiceError(Exception):
    """Base exception for Information Extraction Service errors"""
    pass


class LLMAPIError(IEServiceError):
    """Exception for LLM API related errors"""
    pass


class JSONParsingError(IEServiceError):
    """Exception for JSON parsing errors"""
    pass


class InformationExtractionService:
    """Service for extracting entities and relationships from text using OpenAI API."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo-1106",
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        """
        Initialize the Information Extraction Service.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model to use (must support JSON mode)
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay between retries (seconds)
        """
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI library not available. IE service will have limited functionality.")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=api_key)
        
        self.model = model
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        
        # Validate model supports JSON mode
        if "1106" not in model and "0125" not in model:
            logger.warning(f"Model {model} may not support JSON mode. Consider using gpt-3.5-turbo-1106 or gpt-4-1106-preview")
    
    def _get_extraction_prompt(self) -> str:
        """
        Get the system prompt for entity and relationship extraction.
        
        Returns:
            System prompt string for LLM
        """
        return """You are an expert information extraction system. Extract entities and relationships from the given text chunk.

ENTITY TYPES (use exactly these values):
- Concept: Abstract ideas, theories, methodologies, algorithms
- Library: Software libraries, frameworks, tools
- Person: Individual people (authors, researchers, etc.)
- Organization: Companies, institutions, research groups
- Paper: Research papers, publications, documents
- System: Software systems, platforms, architectures
- Metric: Measurements, benchmarks, performance indicators

RELATIONSHIP TYPES (use exactly these values):
- uses: Entity A uses Entity B
- implements: Entity A implements Entity B
- extends: Entity A extends Entity B
- contains: Entity A contains Entity B
- relates_to: General relationship between entities
- authored_by: Paper/work authored by Person
- published_by: Paper published by Organization
- compares_with: Entity A compares with Entity B
- depends_on: Entity A depends on Entity B
- influences: Entity A influences Entity B

EXTRACTION RULES:
1. Extract only entities explicitly mentioned in the text
2. Entity names should be canonical (e.g., "Machine Learning" not "ML")
3. Include aliases in the aliases field (e.g., ["ML", "machine learning"])
4. Salience score: 0.0-1.0 based on importance in the text
5. Confidence score: 0.0-1.0 based on certainty of relationship
6. Evidence quotes must be verbatim from text, max 200 characters
7. Summary should be concise, max 30 words
8. Only create relationships between extracted entities

Return valid JSON with this exact structure:
{
  "entities": [
    {
      "name": "Entity Name",
      "type": "EntityType",
      "aliases": ["alias1", "alias2"],
      "salience": 0.8,
      "summary": "Brief description of the entity"
    }
  ],
  "relationships": [
    {
      "from": "Entity Name 1",
      "to": "Entity Name 2",
      "predicate": "relationship_type",
      "confidence": 0.9,
      "evidence": [
        {
          "quote": "exact quote from text",
          "offset": 123
        }
      ],
      "directional": true
    }
  ]
}"""

    def _calculate_text_offset(self, text: str, quote: str) -> int:
        """
        Calculate the character offset of a quote in the text.
        
        Args:
            text: The full text
            quote: The quote to find
            
        Returns:
            Character offset of the quote, or 0 if not found
        """
        try:
            return text.find(quote)
        except Exception:
            return 0

    def _validate_and_convert_ie_output(
        self, 
        raw_json: str, 
        chunk_text: str, 
        doc_id: str, 
        chunk_id: str
    ) -> IEResult:
        """
        Validate and convert raw JSON output to IEResult.
        
        Args:
            raw_json: Raw JSON string from LLM
            chunk_text: Original text chunk
            doc_id: Document identifier
            chunk_id: Chunk identifier
            
        Returns:
            Validated IEResult object
            
        Raises:
            JSONParsingError: If JSON is invalid or doesn't match expected structure
        """
        try:
            # Parse JSON
            data = json.loads(raw_json)
            
            if not isinstance(data, dict):
                raise JSONParsingError("Response must be a JSON object")
            
            entities = []
            relationships = []
            
            # Process entities
            for entity_data in data.get("entities", []):
                try:
                    # Validate entity type
                    entity_type = entity_data.get("type")
                    if entity_type not in [e.value for e in EntityType]:
                        logger.warning(f"Invalid entity type '{entity_type}', skipping entity")
                        continue
                    
                    # Create source span for the entire chunk (simplified)
                    source_span = SourceSpan(
                        doc_id=doc_id,
                        start=0,
                        end=len(chunk_text)
                    )
                    
                    # Create entity
                    entity = Entity(
                        name=entity_data["name"],
                        type=EntityType(entity_type),
                        aliases=entity_data.get("aliases", []),
                        salience=max(0.0, min(1.0, entity_data.get("salience", 0.5))),
                        source_spans=[source_span],
                        summary=entity_data.get("summary", "")[:300]  # Truncate to max length
                    )
                    entities.append(entity)
                    
                except (KeyError, ValueError, ValidationError) as e:
                    logger.warning(f"Invalid entity data: {e}, skipping entity")
                    continue
            
            # Create entity name to ID mapping for relationships
            entity_name_to_id = {entity.name: entity.id for entity in entities}
            
            # Process relationships
            for rel_data in data.get("relationships", []):
                try:
                    # Validate relationship type
                    predicate = rel_data.get("predicate")
                    if predicate not in [r.value for r in RelationType]:
                        logger.warning(f"Invalid relationship type '{predicate}', skipping relationship")
                        continue
                    
                    from_name = rel_data["from"]
                    to_name = rel_data["to"]
                    
                    # Check if both entities exist
                    if from_name not in entity_name_to_id or to_name not in entity_name_to_id:
                        logger.warning(f"Relationship references unknown entities: {from_name} -> {to_name}")
                        continue
                    
                    # Process evidence
                    evidence_list = []
                    for evidence_data in rel_data.get("evidence", []):
                        quote = evidence_data.get("quote", "")[:200]  # Truncate to max length
                        offset = evidence_data.get("offset", self._calculate_text_offset(chunk_text, quote))
                        
                        evidence = Evidence(
                            doc_id=doc_id,
                            quote=quote,
                            offset=max(0, offset)
                        )
                        evidence_list.append(evidence)
                    
                    # Create relationship
                    relationship = Relationship(
                        from_entity=entity_name_to_id[from_name],
                        to_entity=entity_name_to_id[to_name],
                        predicate=RelationType(predicate),
                        confidence=max(0.0, min(1.0, rel_data.get("confidence", 0.5))),
                        evidence=evidence_list,
                        directional=rel_data.get("directional", True)
                    )
                    relationships.append(relationship)
                    
                except (KeyError, ValueError, ValidationError) as e:
                    logger.warning(f"Invalid relationship data: {e}, skipping relationship")
                    continue
            
            return IEResult(
                entities=entities,
                relationships=relationships,
                chunk_id=chunk_id,
                doc_id=doc_id
            )
            
        except json.JSONDecodeError as e:
            raise JSONParsingError(f"Invalid JSON: {e}")
        except Exception as e:
            raise JSONParsingError(f"Error processing extraction output: {e}")

    @with_retry(
        retry_config=RetryConfig(max_retries=3, base_delay=1.0, max_delay=60.0),
        circuit_breaker_name="openai_api",
        context={"service": "information_extraction", "operation": "llm_request"}
    )
    async def _make_llm_request(self, chunk_text: str) -> str:
        """
        Make a request to the LLM API with enhanced error handling.
        
        Args:
            chunk_text: Text chunk to process
            
        Returns:
            Raw JSON response from LLM
            
        Raises:
            LLMAPIError: If request fails
        """
        if not OPENAI_AVAILABLE or self.client is None:
            raise LLMAPIError("OpenAI client not available. Please install the openai package.")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_extraction_prompt()},
                    {"role": "user", "content": f"Extract entities and relationships from this text:\n\n{chunk_text}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=4000,  # Sufficient for complex extractions
                timeout=30.0
            )
            
            content = response.choices[0].message.content
            if not content:
                raise LLMAPIError("Empty response from LLM")
            
            return content.strip()
            
        except Exception as e:
            # Classify and re-raise with more context
            if "rate_limit" in str(e).lower():
                raise LLMAPIError(f"Rate limit exceeded: {e}")
            elif "quota" in str(e).lower():
                raise LLMAPIError(f"API quota exceeded: {e}")
            elif "timeout" in str(e).lower():
                raise LLMAPIError(f"Request timeout: {e}")
            else:
                raise LLMAPIError(f"LLM API error: {e}")

    async def extract_entities_relations(
        self, 
        chunk_text: str, 
        doc_id: str, 
        chunk_index: int = 0
    ) -> IEResult:
        """
        Extract entities and relationships from a text chunk.
        
        Args:
            chunk_text: Text chunk to process
            doc_id: Document identifier
            chunk_index: Index of the chunk within the document
            
        Returns:
            IEResult containing extracted entities and relationships
            
        Raises:
            IEServiceError: If extraction fails
        """
        if not chunk_text or not chunk_text.strip():
            return IEResult(
                entities=[],
                relationships=[],
                chunk_id=f"{doc_id}_chunk_{chunk_index}",
                doc_id=doc_id
            )
        
        start_time = time.time()
        chunk_id = f"{doc_id}_chunk_{chunk_index}"
        
        try:
            logger.info(f"Starting extraction for chunk {chunk_id}")
            
            # Make LLM request with retry logic
            raw_json = await self._make_llm_request(chunk_text)
            
            # Validate and convert response
            result = self._validate_and_convert_ie_output(
                raw_json, chunk_text, doc_id, chunk_id
            )
            
            # Set processing time
            result.processing_time = time.time() - start_time
            
            logger.info(
                f"Extraction completed for chunk {chunk_id}: "
                f"{len(result.entities)} entities, {len(result.relationships)} relationships "
                f"in {result.processing_time:.2f}s"
            )
            
            return result
            
        except (LLMAPIError, JSONParsingError) as e:
            logger.error(f"Extraction failed for chunk {chunk_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during extraction for chunk {chunk_id}: {e}")
            raise IEServiceError(f"Extraction failed: {e}")

    async def extract_from_chunks(
        self, 
        chunks: List[str], 
        doc_id: str,
        max_concurrent: int = 2
    ) -> List[IEResult]:
        """
        Extract entities and relationships from multiple text chunks concurrently.
        
        Args:
            chunks: List of text chunks to process
            doc_id: Document identifier
            max_concurrent: Maximum number of concurrent LLM requests
            
        Returns:
            List of IEResult objects, one per chunk
        """
        if not chunks:
            return []
        
        logger.info(f"Starting extraction for {len(chunks)} chunks from document {doc_id}")
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_with_semaphore(chunk_text: str, chunk_index: int) -> IEResult:
            async with semaphore:
                return await self.extract_entities_relations(chunk_text, doc_id, chunk_index)
        
        # Process chunks concurrently
        tasks = [
            extract_with_semaphore(chunk, i) 
            for i, chunk in enumerate(chunks)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process chunk {i} from document {doc_id}: {result}")
                # Create empty result for failed chunks
                successful_results.append(IEResult(
                    entities=[],
                    relationships=[],
                    chunk_id=f"{doc_id}_chunk_{i}",
                    doc_id=doc_id
                ))
            else:
                successful_results.append(result)
        
        total_entities = sum(len(r.entities) for r in successful_results)
        total_relationships = sum(len(r.relationships) for r in successful_results)
        
        logger.info(
            f"Extraction completed for document {doc_id}: "
            f"{total_entities} entities, {total_relationships} relationships "
            f"from {len(chunks)} chunks"
        )
        
        return successful_results


# Convenience function for single chunk extraction
async def extract_entities_relations(
    chunk_text: str,
    doc_id: str,
    api_key: str,
    chunk_index: int = 0,
    model: str = "gpt-3.5-turbo-1106"
) -> IEResult:
    """
    Convenience function to extract entities and relationships from a single chunk.
    
    Args:
        chunk_text: Text chunk to process
        doc_id: Document identifier
        api_key: OpenAI API key
        chunk_index: Index of the chunk within the document
        model: OpenAI model to use
        
    Returns:
        IEResult containing extracted entities and relationships
    """
    service = InformationExtractionService(api_key=api_key, model=model)
    return await service.extract_entities_relations(chunk_text, doc_id, chunk_index)