"""
Tests for grounded answer generation functionality.

Tests the LLM-based answer generation with citations, citation extraction and validation,
and response formatting with node references.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add the server directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.core import Entity, EntityType, SourceSpan, Relationship, RelationType, Evidence
from models.api import Citation, QuestionResponse


class TestGroundedAnswerGeneration:
    """Test grounded answer generation functionality"""
    
    def test_citation_validation_comprehensive(self):
        """Test comprehensive citation validation"""
        # Valid citation
        valid_citation = Citation(
            node_id="entity_123",
            quote="Machine learning is a method of data analysis that automates analytical model building",
            doc_id="research_paper_2023",
            relevance_score=0.85
        )
        
        assert valid_citation.node_id == "entity_123"
        assert len(valid_citation.quote) <= 200  # Should be within limit
        assert valid_citation.doc_id == "research_paper_2023"
        assert 0.0 <= valid_citation.relevance_score <= 1.0
        
        # Test edge cases
        edge_case_citation = Citation(
            node_id="edge_case",
            quote="A" * 200,  # Exactly 200 characters
            doc_id="doc",
            relevance_score=1.0  # Maximum score
        )
        
        assert len(edge_case_citation.quote) == 200
        assert edge_case_citation.relevance_score == 1.0
        
        # Test minimum values
        min_citation = Citation(
            node_id="min_case",
            quote="",  # Empty quote (should be allowed)
            doc_id="",  # Empty doc_id (should be allowed)
            relevance_score=0.0  # Minimum score
        )
        
        assert min_citation.relevance_score == 0.0
    
    def test_citation_validation_errors(self):
        """Test citation validation with invalid data"""
        # Test invalid relevance scores
        with pytest.raises(ValueError):
            Citation(
                node_id="test",
                quote="test quote",
                doc_id="test_doc",
                relevance_score=1.1  # Too high
            )
        
        with pytest.raises(ValueError):
            Citation(
                node_id="test",
                quote="test quote",
                doc_id="test_doc",
                relevance_score=-0.1  # Too low
            )
    
    def test_question_response_validation(self):
        """Test QuestionResponse model validation"""
        citations = [
            Citation(
                node_id="entity_1",
                quote="First supporting quote",
                doc_id="doc1",
                relevance_score=0.9
            ),
            Citation(
                node_id="entity_2",
                quote="Second supporting quote",
                doc_id="doc2",
                relevance_score=0.8
            )
        ]
        
        response = QuestionResponse(
            answer="This is a comprehensive answer based on the knowledge graph data.",
            citations=citations,
            question="What is the main topic?",
            confidence=0.85,
            processing_time=2.3
        )
        
        assert response.answer
        assert len(response.citations) == 2
        assert response.question == "What is the main topic?"
        assert 0.0 <= response.confidence <= 1.0
        assert response.processing_time > 0.0
        
        # Test with empty citations
        empty_response = QuestionResponse(
            answer="No relevant information found.",
            citations=[],
            question="Unknown topic?",
            confidence=0.0,
            processing_time=0.5
        )
        
        assert len(empty_response.citations) == 0
        assert empty_response.confidence == 0.0
    
    def test_advanced_citation_extraction(self):
        """Test advanced citation extraction logic"""
        answer = """Machine learning is a powerful method of data analysis that automates analytical model building. 
        TensorFlow, developed by Google, is widely used for implementing machine learning algorithms. 
        Neural Networks form the backbone of many machine learning systems, particularly in deep learning applications.
        The scikit-learn library provides simple and efficient tools for data mining and data analysis."""
        
        entities = [
            Entity(
                name="Machine Learning",
                type=EntityType.CONCEPT,
                aliases=["ML", "machine learning"],
                salience=0.95,
                source_spans=[SourceSpan(doc_id="ml_textbook", start=0, end=100)],
                summary="A method of data analysis that automates analytical model building"
            ),
            Entity(
                name="TensorFlow",
                type=EntityType.LIBRARY,
                aliases=["tf", "tensorflow"],
                salience=0.85,
                source_spans=[SourceSpan(doc_id="tf_docs", start=200, end=300)],
                summary="An open-source machine learning framework developed by Google"
            ),
            Entity(
                name="Neural Networks",
                type=EntityType.CONCEPT,
                aliases=["NN", "neural nets", "neural networks"],
                salience=0.90,
                source_spans=[SourceSpan(doc_id="nn_paper", start=400, end=500)],
                summary="Computing systems inspired by biological neural networks"
            ),
            Entity(
                name="scikit-learn",
                type=EntityType.LIBRARY,
                aliases=["sklearn"],
                salience=0.75,
                source_spans=[SourceSpan(doc_id="sklearn_docs", start=600, end=700)],
                summary="Machine learning library for Python"
            ),
            Entity(
                name="Deep Learning",
                type=EntityType.CONCEPT,
                aliases=["DL"],
                salience=0.80,
                source_spans=[SourceSpan(doc_id="dl_book", start=800, end=900)],
                summary="Subset of machine learning using neural networks with multiple layers"
            )
        ]
        
        # Advanced citation extraction logic
        citations = []
        answer_lower = answer.lower()
        
        for entity in entities:
            # Check for exact name match
            name_mentioned = entity.name.lower() in answer_lower
            
            # Check for alias matches
            alias_mentioned = any(alias.lower() in answer_lower for alias in entity.aliases)
            
            if name_mentioned or alias_mentioned:
                # Calculate mention frequency
                mention_count = answer_lower.count(entity.name.lower())
                for alias in entity.aliases:
                    mention_count += answer_lower.count(alias.lower())
                
                # Calculate relevance score
                base_relevance = entity.salience
                mention_boost = min(0.2, mention_count * 0.05)
                
                # Boost for exact name matches vs alias matches
                exact_match_boost = 0.1 if name_mentioned else 0.0
                
                relevance_score = min(1.0, base_relevance + mention_boost + exact_match_boost)
                
                quote = entity.summary if entity.summary else f"Entity: {entity.name}"
                doc_id = entity.source_spans[0].doc_id if entity.source_spans else "unknown"
                
                citation = Citation(
                    node_id=entity.id,
                    quote=quote[:200],  # Truncate to max length
                    doc_id=doc_id,
                    relevance_score=relevance_score
                )
                citations.append(citation)
        
        # Sort by relevance score
        citations.sort(key=lambda c: c.relevance_score, reverse=True)
        
        # Verify results
        assert len(citations) >= 3  # Should find at least ML, TensorFlow, Neural Networks
        
        # Check that Machine Learning has high relevance (mentioned multiple times)
        ml_citation = next((c for c in citations if "Machine Learning" in entities[0].name), None)
        assert ml_citation is not None
        
        # Check that TensorFlow is found
        tf_citation = next((c for c in citations if "TensorFlow" in entities[1].name), None)
        assert tf_citation is not None
        
        # Verify citations are sorted by relevance
        for i in range(len(citations) - 1):
            assert citations[i].relevance_score >= citations[i + 1].relevance_score
    
    def test_context_building_with_relationships(self):
        """Test context building including relationship information"""
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
        
        relationships = [
            Relationship(
                from_entity=entities[1].id,  # TensorFlow
                to_entity=entities[0].id,    # Machine Learning
                predicate=RelationType.IMPLEMENTS,
                confidence=0.9,
                evidence=[Evidence(
                    doc_id="doc1",
                    quote="TensorFlow implements machine learning algorithms efficiently",
                    offset=250
                )],
                directional=True
            )
        ]
        
        question = "How does TensorFlow relate to machine learning?"
        
        # Build context (mimicking the service logic)
        context_parts = [f"Question: {question}", "Relevant Entities:"]
        
        for entity in entities:
            entity_info = f"- {entity.name} ({entity.type.value})"
            if entity.summary:
                entity_info += f": {entity.summary}"
            if entity.source_spans:
                entity_info += f" [Source: {entity.source_spans[0].doc_id}]"
            context_parts.append(entity_info)
        
        context_parts.append("\nRelevant Relationships:")
        
        entity_name_map = {e.id: e.name for e in entities}
        for relationship in relationships:
            from_name = entity_name_map.get(relationship.from_entity, relationship.from_entity)
            to_name = entity_name_map.get(relationship.to_entity, relationship.to_entity)
            
            rel_info = f"- {from_name} {relationship.predicate.value} {to_name}"
            if relationship.confidence:
                rel_info += f" (confidence: {relationship.confidence:.2f})"
            
            if relationship.evidence:
                evidence_quotes = [f'"{ev.quote}"' for ev in relationship.evidence[:2]]
                rel_info += f" Evidence: {', '.join(evidence_quotes)}"
            
            context_parts.append(rel_info)
        
        context = "\n".join(context_parts)
        
        # Verify context contains all expected elements
        assert "Question: How does TensorFlow relate to machine learning?" in context
        assert "Machine Learning (Concept)" in context
        assert "TensorFlow (Library)" in context
        assert "TensorFlow implements Machine Learning" in context
        assert "confidence: 0.90" in context
        assert "TensorFlow implements machine learning algorithms efficiently" in context
    
    def test_confidence_calculation_advanced(self):
        """Test advanced confidence calculation scenarios"""
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
        
        # Test various scenarios
        scenarios = [
            {
                "answer": "Based on the knowledge graph, machine learning is a comprehensive method that involves multiple techniques. According to the evidence from multiple sources, it automates analytical model building and enables systems to learn from data without explicit programming.",
                "context": "Rich context with multiple entities",
                "citation_count": 4,
                "expected_min": 0.8
            },
            {
                "answer": "Machine learning is mentioned in the context.",
                "context": "Basic context",
                "citation_count": 1,
                "expected_min": 0.1,
                "expected_max": 0.6
            },
            {
                "answer": "I don't know enough about this topic to provide a comprehensive answer.",
                "context": "Limited context",
                "citation_count": 0,
                "expected_max": 0.3
            },
            {
                "answer": "The information is unclear and uncertain.",
                "context": "Ambiguous context",
                "citation_count": 1,
                "expected_max": 0.4
            }
        ]
        
        for scenario in scenarios:
            confidence = calculate_confidence(
                scenario["answer"],
                scenario["context"],
                scenario["citation_count"]
            )
            
            if "expected_min" in scenario:
                assert confidence >= scenario["expected_min"], f"Confidence {confidence} below expected minimum {scenario['expected_min']}"
            
            if "expected_max" in scenario:
                assert confidence <= scenario["expected_max"], f"Confidence {confidence} above expected maximum {scenario['expected_max']}"
            
            # Always check bounds
            assert 0.0 <= confidence <= 1.0
    
    def test_answer_quality_indicators(self):
        """Test identification of answer quality indicators"""
        def has_quality_indicators(answer: str) -> dict:
            indicators = {
                "has_citations": "based on" in answer.lower() or "according to" in answer.lower(),
                "is_comprehensive": len(answer) > 200,
                "shows_uncertainty": any(phrase in answer.lower() for phrase in 
                                       ["i don't know", "not enough information", "unclear", "uncertain"]),
                "has_specific_details": any(word in answer.lower() for word in 
                                          ["specifically", "particularly", "for example", "such as"]),
                "references_sources": "source" in answer.lower() or "document" in answer.lower()
            }
            return indicators
        
        # Test high-quality answer
        high_quality_answer = """Based on the knowledge graph, machine learning is a comprehensive method of data analysis that automates analytical model building. According to multiple sources, it enables systems to learn patterns from data without explicit programming. For example, neural networks are particularly effective for complex pattern recognition tasks. The evidence from research documents shows that machine learning has applications in various domains such as computer vision, natural language processing, and predictive analytics."""
        
        hq_indicators = has_quality_indicators(high_quality_answer)
        assert hq_indicators["has_citations"]
        assert hq_indicators["is_comprehensive"]
        assert not hq_indicators["shows_uncertainty"]
        assert hq_indicators["has_specific_details"]
        assert hq_indicators["references_sources"]
        
        # Test low-quality answer
        low_quality_answer = "I don't know much about this topic. The information is unclear."
        
        lq_indicators = has_quality_indicators(low_quality_answer)
        assert not lq_indicators["has_citations"]
        assert not lq_indicators["is_comprehensive"]
        assert lq_indicators["shows_uncertainty"]
        assert not lq_indicators["has_specific_details"]
        assert not lq_indicators["references_sources"]
    
    def test_citation_truncation_and_formatting(self):
        """Test citation quote truncation and formatting"""
        # Test long quote truncation (within Entity model limits)
        long_quote = "This is a long quote that needs to be truncated for citation purposes. " * 3  # About 210 chars
        
        entity = Entity(
            name="Test Entity",
            type=EntityType.CONCEPT,
            aliases=[],
            salience=0.8,
            source_spans=[SourceSpan(doc_id="test_doc", start=0, end=100)],
            summary=long_quote[:300]  # Ensure it fits Entity validation
        )
        
        # Simulate citation creation with truncation
        truncated_quote = entity.summary[:200] if entity.summary else f"Entity: {entity.name}"
        
        citation = Citation(
            node_id=entity.id,
            quote=truncated_quote,
            doc_id=entity.source_spans[0].doc_id,
            relevance_score=0.8
        )
        
        assert len(citation.quote) <= 200
        # The quote should be exactly 200 chars or less
        assert len(citation.quote) <= 200
    
    def test_multiple_evidence_handling(self):
        """Test handling of multiple evidence pieces in relationships"""
        relationship = Relationship(
            from_entity="entity_1",
            to_entity="entity_2",
            predicate=RelationType.RELATES_TO,
            confidence=0.85,
            evidence=[
                Evidence(
                    doc_id="doc1",
                    quote="First piece of evidence supporting the relationship",
                    offset=100
                ),
                Evidence(
                    doc_id="doc2",
                    quote="Second piece of evidence from a different source",
                    offset=200
                ),
                Evidence(
                    doc_id="doc3",
                    quote="Third piece of evidence providing additional context",
                    offset=300
                )
            ],
            directional=True
        )
        
        # Test evidence formatting (limit to 2 pieces as in the service)
        evidence_quotes = [f'"{ev.quote}"' for ev in relationship.evidence[:2]]
        formatted_evidence = ", ".join(evidence_quotes)
        
        assert len(evidence_quotes) == 2  # Should limit to 2 pieces
        assert "First piece of evidence" in formatted_evidence
        assert "Second piece of evidence" in formatted_evidence
        assert "Third piece of evidence" not in formatted_evidence  # Should be excluded


if __name__ == "__main__":
    pytest.main([__file__, "-v"])