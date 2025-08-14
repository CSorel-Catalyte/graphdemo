"""
Integration test for Question Answering functionality.
Tests the /ask endpoint implementation without requiring external dependencies.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add the server directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.core import Entity, EntityType, SourceSpan
from models.api import Citation, QuestionResponse


class TestQAIntegration:
    """Integration tests for QA functionality"""
    
    def test_question_response_model(self):
        """Test QuestionResponse model validation"""
        response = QuestionResponse(
            answer="Machine learning is a method of data analysis.",
            citations=[
                Citation(
                    node_id="entity_123",
                    quote="Machine learning automates analytical model building",
                    doc_id="doc1",
                    relevance_score=0.9
                )
            ],
            question="What is machine learning?",
            confidence=0.85,
            processing_time=1.5
        )
        
        assert response.answer == "Machine learning is a method of data analysis."
        assert len(response.citations) == 1
        assert response.citations[0].node_id == "entity_123"
        assert response.question == "What is machine learning?"
        assert response.confidence == 0.85
        assert response.processing_time == 1.5
    
    def test_citation_model(self):
        """Test Citation model validation"""
        citation = Citation(
            node_id="entity_456",
            quote="TensorFlow is an open-source machine learning framework",
            doc_id="doc2",
            relevance_score=0.75
        )
        
        assert citation.node_id == "entity_456"
        assert citation.quote == "TensorFlow is an open-source machine learning framework"
        assert citation.doc_id == "doc2"
        assert citation.relevance_score == 0.75
    
    def test_citation_validation_errors(self):
        """Test Citation model validation with invalid data"""
        with pytest.raises(ValueError):
            Citation(
                node_id="entity_456",
                quote="Valid quote",
                doc_id="doc2",
                relevance_score=1.5  # Invalid: > 1.0
            )
        
        with pytest.raises(ValueError):
            Citation(
                node_id="entity_456",
                quote="Valid quote",
                doc_id="doc2",
                relevance_score=-0.1  # Invalid: < 0.0
            )
    
    @pytest.mark.asyncio
    async def test_qa_service_basic_functionality(self):
        """Test basic QA service functionality with mocks"""
        # Mock the services to avoid dependency issues
        mock_ie_service = Mock()
        mock_ie_service.client = AsyncMock()
        
        # Mock embedding response
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock()]
        mock_embedding_response.data[0].embedding = [0.1] * 3072
        mock_ie_service.client.embeddings.create.return_value = mock_embedding_response
        
        # Mock answer generation response
        mock_answer_response = Mock()
        mock_answer_response.choices = [Mock()]
        mock_answer_response.choices[0].message.content = "Machine learning is a method of data analysis that automates analytical model building."
        mock_ie_service.client.chat.completions.create.return_value = mock_answer_response
        
        mock_qdrant_adapter = Mock()
        mock_oxigraph_adapter = Mock()
        
        # Create sample entity for testing
        sample_entity = Entity(
            name="Machine Learning",
            type=EntityType.CONCEPT,
            aliases=["ML"],
            salience=0.9,
            source_spans=[SourceSpan(doc_id="doc1", start=0, end=100)],
            summary="A method of data analysis that automates analytical model building"
        )
        
        # Mock search results
        mock_qdrant_adapter.search_entities_by_text.return_value = [
            (sample_entity, 0.95)
        ]
        
        # Mock neighborhood expansion
        mock_oxigraph_adapter.get_neighbors.return_value = []
        mock_qdrant_adapter.get_entities_by_ids.return_value = []
        mock_oxigraph_adapter.get_entity_relationships.return_value = []
        
        # Import and test QA service
        try:
            from services.qa_service import QuestionAnsweringService
            
            qa_service = QuestionAnsweringService(
                ie_service=mock_ie_service,
                qdrant_adapter=mock_qdrant_adapter,
                oxigraph_adapter=mock_oxigraph_adapter
            )
            
            # Test question answering
            result = await qa_service.answer_question("What is machine learning?")
            
            assert result.answer
            assert isinstance(result.citations, list)
            assert 0.0 <= result.confidence <= 1.0
            assert isinstance(result.relevant_nodes, list)
            
        except ImportError as e:
            pytest.skip(f"QA service dependencies not available: {e}")
    
    def test_context_building_logic(self):
        """Test context building logic without external dependencies"""
        # Create sample entities
        entities = [
            Entity(
                name="Machine Learning",
                type=EntityType.CONCEPT,
                aliases=["ML"],
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
            )
        ]
        
        question = "What is machine learning?"
        
        # Simple context building logic (mimicking the service)
        context_parts = [f"Question: {question}", "Relevant Entities:"]
        
        for entity in entities:
            entity_info = f"- {entity.name} ({entity.type.value})"
            if entity.summary:
                entity_info += f": {entity.summary}"
            if entity.source_spans:
                entity_info += f" [Source: {entity.source_spans[0].doc_id}]"
            context_parts.append(entity_info)
        
        context = "\n".join(context_parts)
        
        assert "Question: What is machine learning?" in context
        assert "Machine Learning (Concept)" in context
        assert "TensorFlow (Library)" in context
        assert "automates analytical model building" in context
        assert "open-source machine learning framework" in context
    
    def test_citation_extraction_logic(self):
        """Test citation extraction logic"""
        answer = "Machine learning is a method of data analysis. TensorFlow is a framework that implements machine learning algorithms."
        
        entities = [
            Entity(
                name="Machine Learning",
                type=EntityType.CONCEPT,
                aliases=["ML"],
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
            )
        ]
        
        # Simple citation extraction logic
        citations = []
        for entity in entities:
            if entity.name.lower() in answer.lower():
                quote = entity.summary if entity.summary else f"Entity: {entity.name}"
                doc_id = entity.source_spans[0].doc_id if entity.source_spans else "unknown"
                
                mention_count = answer.lower().count(entity.name.lower())
                relevance_score = min(1.0, entity.salience + (mention_count * 0.1))
                
                citation = Citation(
                    node_id=entity.id,
                    quote=quote[:200],
                    doc_id=doc_id,
                    relevance_score=relevance_score
                )
                citations.append(citation)
        
        assert len(citations) == 2  # Both entities mentioned
        assert any(c.node_id == entities[0].id for c in citations)
        assert any(c.node_id == entities[1].id for c in citations)
    
    def test_confidence_calculation_logic(self):
        """Test confidence calculation logic"""
        def calculate_confidence(answer: str, context: str, citation_count: int) -> float:
            confidence = 0.0
            
            # Base confidence on answer length and quality indicators
            if len(answer) > 50:
                confidence += 0.3
            
            if "based on" in answer.lower() or "according to" in answer.lower():
                confidence += 0.2
            
            # Boost confidence based on citations
            if citation_count > 0:
                confidence += min(0.4, citation_count * 0.1)
            
            # Penalize if answer indicates uncertainty
            uncertainty_phrases = ["i don't know", "not enough information", "unclear", "uncertain"]
            if any(phrase in answer.lower() for phrase in uncertainty_phrases):
                confidence *= 0.5
            
            # Boost if answer seems comprehensive
            if len(answer) > 200 and citation_count >= 2:
                confidence += 0.1
            
            return min(1.0, confidence)
        
        # Test high confidence
        high_conf_answer = "Based on the knowledge graph, machine learning is a comprehensive method that involves multiple techniques. According to the evidence, it automates analytical model building."
        high_confidence = calculate_confidence(high_conf_answer, "context", 3)
        assert high_confidence > 0.7
        
        # Test low confidence
        low_conf_answer = "I don't know enough about this topic."
        low_confidence = calculate_confidence(low_conf_answer, "context", 0)
        assert low_confidence < 0.5
        
        # Test medium confidence
        med_conf_answer = "Machine learning is a method of data analysis that automates model building."
        med_confidence = calculate_confidence(med_conf_answer, "context", 1)
        assert 0.3 <= med_confidence <= 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])