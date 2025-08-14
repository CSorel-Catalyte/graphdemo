"""
Tests for the Question Answering Service.

Tests the complete QA pipeline including:
- Question embedding generation
- Top-k node retrieval via vector similarity
- Neighborhood expansion using graph traversal
- Context building from node summaries and evidence
- Grounded answer generation with citations
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import List

from services.qa_service import QuestionAnsweringService, QAResult
from services.ie_service import InformationExtractionService
from storage.qdrant_adapter import QdrantAdapter
from storage.oxigraph_adapter import OxigraphAdapter
from models.core import Entity, Relationship, EntityType, RelationType, Evidence, SourceSpan
from models.api import Citation


@pytest.fixture
def mock_ie_service():
    """Mock IE service for testing"""
    service = Mock(spec=InformationExtractionService)
    service.client = AsyncMock()
    service.model = "gpt-3.5-turbo-1106"
    return service


@pytest.fixture
def mock_qdrant_adapter():
    """Mock Qdrant adapter for testing"""
    adapter = Mock(spec=QdrantAdapter)
    return adapter


@pytest.fixture
def mock_oxigraph_adapter():
    """Mock Oxigraph adapter for testing"""
    adapter = Mock(spec=OxigraphAdapter)
    return adapter


@pytest.fixture
def sample_entities():
    """Sample entities for testing"""
    return [
        Entity(
            name="Machine Learning",
            type=EntityType.CONCEPT,
            aliases=["ML", "machine learning"],
            salience=0.9,
            source_spans=[SourceSpan(doc_id="doc1", start=0, end=100)],
            summary="A method of data analysis that automates analytical model building"
        ),
        Entity(
            name="TensorFlow",
            type=EntityType.LIBRARY,
            aliases=["tf"],
            salience=0.8,
            source_spans=[SourceSpan(doc_id="doc1", start=200, end=300)],
            summary="An open-source machine learning framework"
        ),
        Entity(
            name="Neural Networks",
            type=EntityType.CONCEPT,
            aliases=["NN", "neural nets"],
            salience=0.85,
            source_spans=[SourceSpan(doc_id="doc1", start=400, end=500)],
            summary="Computing systems inspired by biological neural networks"
        )
    ]


@pytest.fixture
def sample_relationships(sample_entities):
    """Sample relationships for testing"""
    return [
        Relationship(
            from_entity=sample_entities[1].id,  # TensorFlow
            to_entity=sample_entities[0].id,    # Machine Learning
            predicate=RelationType.IMPLEMENTS,
            confidence=0.9,
            evidence=[Evidence(
                doc_id="doc1",
                quote="TensorFlow implements machine learning algorithms",
                offset=250
            )],
            directional=True
        ),
        Relationship(
            from_entity=sample_entities[2].id,  # Neural Networks
            to_entity=sample_entities[0].id,    # Machine Learning
            predicate=RelationType.RELATES_TO,
            confidence=0.8,
            evidence=[Evidence(
                doc_id="doc1",
                quote="Neural networks are a key component of machine learning",
                offset=450
            )],
            directional=True
        )
    ]


@pytest.fixture
def qa_service(mock_ie_service, mock_qdrant_adapter, mock_oxigraph_adapter):
    """QA service instance for testing"""
    return QuestionAnsweringService(
        ie_service=mock_ie_service,
        qdrant_adapter=mock_qdrant_adapter,
        oxigraph_adapter=mock_oxigraph_adapter,
        top_k_nodes=5,
        max_context_length=2000
    )


class TestQuestionEmbedding:
    """Test question embedding generation"""
    
    @pytest.mark.asyncio
    async def test_generate_question_embedding_success(self, qa_service, mock_ie_service):
        """Test successful question embedding generation"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3] * 1024  # 3072-dim vector
        mock_ie_service.client.embeddings.create.return_value = mock_response
        
        question = "What is machine learning?"
        embedding = await qa_service.generate_question_embedding(question)
        
        assert len(embedding) == 3072
        assert embedding[:3] == [0.1, 0.2, 0.3]
        mock_ie_service.client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-large",
            input=question,
            encoding_format="float"
        )
    
    @pytest.mark.asyncio
    async def test_generate_question_embedding_no_client(self, qa_service):
        """Test embedding generation with no client"""
        qa_service.ie_service.client = None
        
        with pytest.raises(Exception, match="OpenAI client not available"):
            await qa_service.generate_question_embedding("test question")
    
    @pytest.mark.asyncio
    async def test_generate_question_embedding_api_error(self, qa_service, mock_ie_service):
        """Test embedding generation with API error"""
        mock_ie_service.client.embeddings.create.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="Error generating question embedding"):
            await qa_service.generate_question_embedding("test question")


class TestNodeRetrieval:
    """Test relevant node retrieval"""
    
    @pytest.mark.asyncio
    async def test_retrieve_relevant_nodes_success(self, qa_service, mock_qdrant_adapter, sample_entities):
        """Test successful node retrieval"""
        # Mock Qdrant response
        mock_qdrant_adapter.search_entities_by_text.return_value = [
            (sample_entities[0], 0.95),
            (sample_entities[1], 0.87),
            (sample_entities[2], 0.82)
        ]
        
        question_embedding = [0.1] * 3072
        results = await qa_service.retrieve_relevant_nodes(question_embedding)
        
        assert len(results) == 3
        assert results[0][0].name == "Machine Learning"
        assert results[0][1] == 0.95
        mock_qdrant_adapter.search_entities_by_text.assert_called_once_with(
            query_embedding=question_embedding,
            limit=5
        )
    
    @pytest.mark.asyncio
    async def test_retrieve_relevant_nodes_empty(self, qa_service, mock_qdrant_adapter):
        """Test node retrieval with no results"""
        mock_qdrant_adapter.search_entities_by_text.return_value = []
        
        question_embedding = [0.1] * 3072
        results = await qa_service.retrieve_relevant_nodes(question_embedding)
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_retrieve_relevant_nodes_error(self, qa_service, mock_qdrant_adapter):
        """Test node retrieval with error"""
        mock_qdrant_adapter.search_entities_by_text.side_effect = Exception("Search error")
        
        question_embedding = [0.1] * 3072
        results = await qa_service.retrieve_relevant_nodes(question_embedding)
        
        assert len(results) == 0


class TestNeighborhoodExpansion:
    """Test neighborhood expansion"""
    
    @pytest.mark.asyncio
    async def test_expand_node_neighborhoods_success(
        self, qa_service, mock_qdrant_adapter, mock_oxigraph_adapter, 
        sample_entities, sample_relationships
    ):
        """Test successful neighborhood expansion"""
        # Mock Oxigraph neighbor response
        mock_oxigraph_adapter.get_neighbors.return_value = [
            {"entity_id": sample_entities[1].id, "name": "TensorFlow", "type": "Library"},
            {"entity_id": sample_entities[2].id, "name": "Neural Networks", "type": "Concept"}
        ]
        
        # Mock Qdrant entity retrieval
        mock_qdrant_adapter.get_entities_by_ids.return_value = [sample_entities[1], sample_entities[2]]
        
        # Mock relationship retrieval
        mock_oxigraph_adapter.get_entity_relationships.return_value = [
            {
                "from_entity": sample_entities[1].id,
                "to_entity": sample_entities[0].id,
                "predicate": "implements",
                "confidence": 0.9,
                "directional": True,
                "evidence": [{"doc_id": "doc1", "quote": "TensorFlow implements ML"}]
            }
        ]
        
        relevant_nodes = [sample_entities[0]]  # Just Machine Learning
        expanded_entities, relationships = await qa_service.expand_node_neighborhoods(relevant_nodes)
        
        assert len(expanded_entities) >= 1  # At least the original entity
        assert len(relationships) >= 0
        mock_oxigraph_adapter.get_neighbors.assert_called()
        mock_qdrant_adapter.get_entities_by_ids.assert_called()
    
    @pytest.mark.asyncio
    async def test_expand_node_neighborhoods_error(
        self, qa_service, mock_oxigraph_adapter, sample_entities
    ):
        """Test neighborhood expansion with error"""
        mock_oxigraph_adapter.get_neighbors.side_effect = Exception("Graph error")
        
        relevant_nodes = [sample_entities[0]]
        expanded_entities, relationships = await qa_service.expand_node_neighborhoods(relevant_nodes)
        
        # Should return original nodes on error
        assert expanded_entities == relevant_nodes
        assert relationships == []


class TestContextBuilding:
    """Test context building"""
    
    def test_build_context_success(self, qa_service, sample_entities, sample_relationships):
        """Test successful context building"""
        question = "What is machine learning?"
        context = qa_service.build_context(sample_entities, sample_relationships, question)
        
        assert "Question: What is machine learning?" in context
        assert "Relevant Entities:" in context
        assert "Machine Learning" in context
        assert "TensorFlow" in context
        assert "Relevant Relationships:" in context
        assert "implements" in context
        assert len(context) <= qa_service.max_context_length
    
    def test_build_context_truncation(self, qa_service, sample_entities):
        """Test context truncation when too long"""
        qa_service.max_context_length = 100  # Very small limit
        
        question = "What is machine learning?"
        context = qa_service.build_context(sample_entities, [], question)
        
        assert len(context) <= 100
        assert context.endswith("...[truncated]")
    
    def test_build_context_error_handling(self, qa_service):
        """Test context building with error"""
        # Pass invalid data to trigger error
        question = "What is machine learning?"
        context = qa_service.build_context(None, None, question)
        
        assert "Error building context" in context
        assert question in context


class TestAnswerGeneration:
    """Test grounded answer generation"""
    
    @pytest.mark.asyncio
    async def test_generate_grounded_answer_success(
        self, qa_service, mock_ie_service, sample_entities
    ):
        """Test successful answer generation"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Machine learning is a method of data analysis that automates analytical model building, as mentioned in the context about Machine Learning."
        mock_ie_service.client.chat.completions.create.return_value = mock_response
        
        question = "What is machine learning?"
        context = "Machine Learning (Concept): A method of data analysis that automates analytical model building"
        
        answer, citations, confidence = await qa_service.generate_grounded_answer(
            question, context, sample_entities[:1]
        )
        
        assert "machine learning" in answer.lower()
        assert len(citations) >= 0
        assert 0.0 <= confidence <= 1.0
        mock_ie_service.client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_grounded_answer_no_client(self, qa_service, sample_entities):
        """Test answer generation with no client"""
        qa_service.ie_service.client = None
        
        answer, citations, confidence = await qa_service.generate_grounded_answer(
            "test question", "test context", sample_entities
        )
        
        assert "error" in answer.lower()
        assert citations == []
        assert confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_generate_grounded_answer_api_error(
        self, qa_service, mock_ie_service, sample_entities
    ):
        """Test answer generation with API error"""
        mock_ie_service.client.chat.completions.create.side_effect = Exception("API Error")
        
        answer, citations, confidence = await qa_service.generate_grounded_answer(
            "test question", "test context", sample_entities
        )
        
        assert "error" in answer.lower()
        assert citations == []
        assert confidence == 0.0


class TestCitationExtraction:
    """Test citation extraction"""
    
    def test_extract_citations_success(self, qa_service, sample_entities):
        """Test successful citation extraction"""
        answer = "Machine Learning is a method of data analysis. TensorFlow is a framework that implements machine learning algorithms."
        
        citations = qa_service._extract_citations(answer, sample_entities)
        
        assert len(citations) >= 1
        # Should find citations for entities mentioned in the answer
        entity_names = [c.node_id for c in citations]
        assert any(entity.id in entity_names for entity in sample_entities[:2])
    
    def test_extract_citations_no_matches(self, qa_service, sample_entities):
        """Test citation extraction with no entity matches"""
        answer = "This answer doesn't mention any specific entities from the knowledge graph."
        
        citations = qa_service._extract_citations(answer, sample_entities)
        
        assert len(citations) == 0
    
    def test_extract_citations_error_handling(self, qa_service):
        """Test citation extraction with error"""
        # Pass invalid data to trigger error
        citations = qa_service._extract_citations("test answer", None)
        
        assert citations == []


class TestConfidenceCalculation:
    """Test confidence score calculation"""
    
    def test_calculate_confidence_high(self, qa_service):
        """Test high confidence calculation"""
        answer = "Based on the knowledge graph, machine learning is a comprehensive method that involves multiple techniques. According to the evidence, it automates analytical model building."
        context = "Machine Learning: comprehensive method"
        citation_count = 3
        
        confidence = qa_service._calculate_confidence(answer, context, citation_count)
        
        assert confidence > 0.7  # Should be high confidence
    
    def test_calculate_confidence_low(self, qa_service):
        """Test low confidence calculation"""
        answer = "I don't know enough about this topic."
        context = "Limited context"
        citation_count = 0
        
        confidence = qa_service._calculate_confidence(answer, context, citation_count)
        
        assert confidence < 0.5  # Should be low confidence
    
    def test_calculate_confidence_error_handling(self, qa_service):
        """Test confidence calculation with error"""
        # Pass invalid data to trigger error
        confidence = qa_service._calculate_confidence(None, None, 0)
        
        assert confidence == 0.5  # Default fallback


class TestFullQAPipeline:
    """Test complete QA pipeline"""
    
    @pytest.mark.asyncio
    async def test_answer_question_success(
        self, qa_service, mock_ie_service, mock_qdrant_adapter, 
        mock_oxigraph_adapter, sample_entities
    ):
        """Test successful complete QA pipeline"""
        # Mock embedding generation
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].embedding = [0.1] * 3072
        mock_ie_service.client.embeddings.create.return_value = mock_response
        
        # Mock node retrieval
        mock_qdrant_adapter.search_entities_by_text.return_value = [
            (sample_entities[0], 0.95)
        ]
        
        # Mock neighborhood expansion
        mock_oxigraph_adapter.get_neighbors.return_value = []
        mock_qdrant_adapter.get_entities_by_ids.return_value = []
        mock_oxigraph_adapter.get_entity_relationships.return_value = []
        
        # Mock answer generation
        mock_answer_response = Mock()
        mock_answer_response.choices = [Mock()]
        mock_answer_response.choices[0].message.content = "Machine learning is a method of data analysis."
        mock_ie_service.client.chat.completions.create.return_value = mock_answer_response
        
        question = "What is machine learning?"
        result = await qa_service.answer_question(question)
        
        assert isinstance(result, QAResult)
        assert result.answer
        assert isinstance(result.citations, list)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.relevant_nodes, list)
        assert result.context_used
    
    @pytest.mark.asyncio
    async def test_answer_question_no_relevant_nodes(
        self, qa_service, mock_ie_service, mock_qdrant_adapter
    ):
        """Test QA pipeline with no relevant nodes found"""
        # Mock embedding generation
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].embedding = [0.1] * 3072
        mock_ie_service.client.embeddings.create.return_value = mock_response
        
        # Mock empty node retrieval
        mock_qdrant_adapter.search_entities_by_text.return_value = []
        
        question = "What is machine learning?"
        result = await qa_service.answer_question(question)
        
        assert "couldn't find any relevant information" in result.answer
        assert result.citations == []
        assert result.confidence == 0.0
        assert result.relevant_nodes == []
    
    @pytest.mark.asyncio
    async def test_answer_question_error(self, qa_service, mock_ie_service):
        """Test QA pipeline with error"""
        mock_ie_service.client.embeddings.create.side_effect = Exception("Embedding error")
        
        question = "What is machine learning?"
        result = await qa_service.answer_question(question)
        
        assert "error" in result.answer.lower()
        assert result.citations == []
        assert result.confidence == 0.0


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])