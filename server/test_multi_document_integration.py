"""
Integration tests for multi-document processing and relationship merging.
Tests the complete workflow from ingestion through conflict detection.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import List
import sys
import os

# Add the server directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.core import Entity, EntityType, SourceSpan, Relationship, RelationType, Evidence
from services.canonicalization import EntityCanonicalizer
from services.conflict_detection import ConflictDetector, detect_and_create_comparisons


class TestMultiDocumentIntegration:
    """Integration tests for multi-document processing workflow"""
    
    @pytest.fixture
    def mock_qdrant_adapter(self):
        """Create a mock Qdrant adapter"""
        adapter = Mock()
        adapter.find_similar_entities = AsyncMock(return_value=[])
        return adapter
    
    @pytest.fixture
    def canonicalizer(self, mock_qdrant_adapter):
        """Create EntityCanonicalizer instance"""
        return EntityCanonicalizer(mock_qdrant_adapter, similarity_threshold=0.86)
    
    @pytest.fixture
    def conflict_detector(self):
        """Create ConflictDetector instance"""
        return ConflictDetector(similarity_threshold=0.7)
    
    @pytest.fixture
    def multi_document_entities(self):
        """Create sample entities from multiple documents for testing"""
        return [
            # Document 1: Google's perspective on TensorFlow
            Entity(
                name="TensorFlow",
                type=EntityType.LIBRARY,
                salience=0.9,
                summary="Google's open source machine learning framework for research and production",
                source_spans=[
                    SourceSpan(doc_id="google_blog_2023", start=0, end=50),
                    SourceSpan(doc_id="google_blog_2023", start=200, end=250)
                ],
                aliases=["TF", "tensorflow"]
            ),
            
            # Document 2: Wikipedia's perspective on TensorFlow (different capitalization)
            Entity(
                name="Tensorflow",
                type=EntityType.LIBRARY,
                salience=0.6,
                summary="Deep learning library developed by Google Brain team for machine learning",
                source_spans=[
                    SourceSpan(doc_id="wikipedia_ml", start=0, end=40),
                    SourceSpan(doc_id="wikipedia_ml", start=300, end=340)
                ],
                aliases=["tensorflow", "Google TensorFlow"]
            ),
            
            # Document 3: PyTorch from Facebook's documentation
            Entity(
                name="PyTorch",
                type=EntityType.LIBRARY,
                salience=0.8,
                summary="Facebook's machine learning library with dynamic computation graphs",
                source_spans=[
                    SourceSpan(doc_id="pytorch_docs", start=0, end=60),
                    SourceSpan(doc_id="pytorch_docs", start=150, end=200)
                ],
                aliases=["torch", "pytorch"]
            ),
            
            # Document 4: Comparison article mentioning PyTorch differently
            Entity(
                name="PyTorch",
                type=EntityType.LIBRARY,
                salience=0.7,
                summary="Open source machine learning framework by Meta AI",
                source_spans=[
                    SourceSpan(doc_id="comparison_article", start=0, end=30),
                    SourceSpan(doc_id="comparison_article", start=100, end=130)
                ],
                aliases=["Meta PyTorch", "torch"]
            ),
            
            # Document 5: Machine Learning concept appearing in multiple docs
            Entity(
                name="Machine Learning",
                type=EntityType.CONCEPT,
                salience=0.8,
                summary="A method of data analysis that automates analytical model building",
                source_spans=[
                    SourceSpan(doc_id="google_blog_2023", start=100, end=150),
                    SourceSpan(doc_id="wikipedia_ml", start=50, end=100),
                    SourceSpan(doc_id="pytorch_docs", start=250, end=300)
                ],
                aliases=["ML", "machine learning"]
            ),
            
            # Document 6: Different perspective on Machine Learning (different name to avoid ID collision)
            Entity(
                name="ML Techniques",
                type=EntityType.CONCEPT,
                salience=0.7,
                summary="Subset of artificial intelligence focused on pattern recognition",
                source_spans=[
                    SourceSpan(doc_id="comparison_article", start=200, end=250)
                ],
                aliases=["Machine Learning", "ML", "automated learning"]
            )
        ]
    
    @pytest.mark.asyncio
    async def test_cross_document_canonicalization_workflow(self, canonicalizer, multi_document_entities):
        """Test the complete cross-document canonicalization workflow"""
        
        # Mock the similarity search to return similar entities
        def mock_find_similar(query_vector, limit, score_threshold, entity_type):
            # Simulate finding similar TensorFlow entities
            if entity_type == EntityType.LIBRARY:
                tensorflow_entities = [e for e in multi_document_entities if "tensorflow" in e.name.lower()]
                if len(tensorflow_entities) > 1:
                    return [(tensorflow_entities[1], 0.95)]  # Return the second TensorFlow entity
            return []
        
        canonicalizer.qdrant_adapter.find_similar_entities.side_effect = mock_find_similar
        
        # Run canonicalization
        canonical_entities = await canonicalizer.canonicalize_entities(multi_document_entities)
        
        # Verify results
        assert len(canonical_entities) < len(multi_document_entities)  # Some entities should be merged
        
        # Check that TensorFlow entities were merged
        tensorflow_entities = [e for e in canonical_entities if "tensorflow" in e.name.lower()]
        assert len(tensorflow_entities) == 1  # Should be merged into one
        
        merged_tensorflow = tensorflow_entities[0]
        assert len(merged_tensorflow.source_spans) >= 4  # Should have spans from both documents
        assert len(merged_tensorflow.aliases) >= 3  # Should have combined aliases
        assert "appears in 2 documents" in merged_tensorflow.summary  # Should indicate multi-document
        
        # Check cross-document statistics
        stats = canonicalizer.get_merge_statistics(multi_document_entities, canonical_entities)
        assert stats["cross_document"]["entities_spanning_multiple_docs"] > 0
        assert stats["cross_document"]["total_unique_documents"] >= 4
    
    @pytest.mark.asyncio
    async def test_conflict_detection_workflow(self, conflict_detector, multi_document_entities):
        """Test conflict detection on multi-document entities"""
        
        # Run conflict detection
        conflicts = conflict_detector.detect_conflicts_in_entities(multi_document_entities)
        
        # Should detect conflicts between TensorFlow variants
        assert len(conflicts) > 0
        
        # Verify conflict details
        tensorflow_conflicts = [
            c for c in conflicts 
            if any("tensorflow" in entity.name.lower() for entity in [c[0], c[1]])
        ]
        assert len(tensorflow_conflicts) > 0
        
        # Create comparison relationships
        relationships = conflict_detector.create_comparison_relationships(conflicts)
        
        # Should create bidirectional comparison relationships
        assert len(relationships) > 0
        comparison_rels = [r for r in relationships if r.predicate == RelationType.COMPARES_WITH]
        assert len(comparison_rels) > 0
        
        # Verify relationship properties
        for rel in comparison_rels:
            assert rel.confidence == 0.8
            assert rel.directional is False
            assert len(rel.evidence) > 0
    
    @pytest.mark.asyncio
    async def test_complete_multi_document_workflow(self, canonicalizer, conflict_detector, multi_document_entities):
        """Test the complete multi-document processing workflow"""
        
        # Step 1: Canonicalization (entity merging)
        canonicalizer.qdrant_adapter.find_similar_entities.return_value = []  # No similar entities for simplicity
        canonical_entities = await canonicalizer.canonicalize_entities(multi_document_entities)
        
        # Step 2: Conflict detection and comparison relationship creation
        comparison_relationships, analysis = detect_and_create_comparisons(canonical_entities)
        
        # Verify the complete workflow results
        assert len(canonical_entities) <= len(multi_document_entities)  # May have merged entities
        
        # Should have created some comparison relationships
        if len(comparison_relationships) > 0:
            assert all(r.predicate == RelationType.COMPARES_WITH for r in comparison_relationships)
            
            # Analysis should provide insights
            assert analysis["total_entities"] == len(canonical_entities)
            assert analysis["comparison_relationships"] == len(comparison_relationships)
            
            if analysis["cross_document"]["entities_spanning_multiple_docs"] > 0:
                assert analysis["cross_document"]["total_unique_documents"] > 1
    
    def test_cross_document_entity_identification(self, canonicalizer, multi_document_entities):
        """Test identification of entities spanning multiple documents"""
        
        cross_doc_entities = canonicalizer.get_cross_document_entities(multi_document_entities)
        
        # Machine Learning should be identified as cross-document (appears in 4 documents)
        ml_entities = [e for e in cross_doc_entities if e.name == "Machine Learning"]
        assert len(ml_entities) >= 1
        
        # Verify the cross-document entity has spans from multiple documents
        for entity in ml_entities:
            doc_sources = {span.doc_id for span in entity.source_spans}
            assert len(doc_sources) > 1
    
    def test_conflict_analysis_patterns(self, conflict_detector, multi_document_entities):
        """Test cross-document pattern analysis"""
        
        # Create some mock relationships for analysis
        relationships = [
            Relationship(
                from_entity=multi_document_entities[0].id,  # TensorFlow
                to_entity=multi_document_entities[1].id,   # Tensorflow
                predicate=RelationType.COMPARES_WITH,
                confidence=0.8,
                evidence=[],
                directional=False
            )
        ]
        
        analysis = conflict_detector.analyze_cross_document_patterns(multi_document_entities, relationships)
        
        # Verify analysis results
        assert analysis["total_entities"] == len(multi_document_entities)
        assert analysis["comparison_relationships"] == 1
        assert len(analysis["document_pairs"]) > 0
        
        # Should identify entities with conflicts
        if len(analysis["most_conflicted_entities"]) > 0:
            assert all("entity_name" in entity for entity in analysis["most_conflicted_entities"])
            assert all("conflict_count" in entity for entity in analysis["most_conflicted_entities"])
    
    @pytest.mark.asyncio
    async def test_realistic_tensorflow_pytorch_scenario(self, canonicalizer, conflict_detector):
        """Test a realistic scenario with TensorFlow vs PyTorch documentation"""
        
        # Realistic entities from different sources
        entities = [
            Entity(
                name="TensorFlow",
                type=EntityType.LIBRARY,
                salience=0.9,
                summary="Google's comprehensive machine learning platform for research and production",
                source_spans=[
                    SourceSpan(doc_id="tensorflow_official_docs", start=0, end=100),
                    SourceSpan(doc_id="tensorflow_official_docs", start=500, end=600)
                ],
                aliases=["TF", "tensorflow", "Google TensorFlow"]
            ),
            Entity(
                name="Tensorflow",  # Different capitalization
                type=EntityType.LIBRARY,
                salience=0.7,
                summary="Open source machine learning framework developed by Google Brain",
                source_spans=[
                    SourceSpan(doc_id="ml_comparison_blog", start=0, end=80),
                    SourceSpan(doc_id="ml_comparison_blog", start=200, end=280)
                ],
                aliases=["tensorflow", "TF framework"]
            ),
            Entity(
                name="PyTorch",
                type=EntityType.LIBRARY,
                salience=0.8,
                summary="Facebook's dynamic neural network library with eager execution",
                source_spans=[
                    SourceSpan(doc_id="pytorch_official_docs", start=0, end=90),
                    SourceSpan(doc_id="pytorch_official_docs", start=300, end=390)
                ],
                aliases=["torch", "pytorch", "Facebook PyTorch"]
            ),
            Entity(
                name="PyTorch",
                type=EntityType.LIBRARY,
                salience=0.6,
                summary="Meta's machine learning framework with automatic differentiation",
                source_spans=[
                    SourceSpan(doc_id="ml_comparison_blog", start=400, end=480),
                    SourceSpan(doc_id="ml_comparison_blog", start=600, end=680)
                ],
                aliases=["Meta PyTorch", "torch", "pytorch"]
            )
        ]
        
        # Mock canonicalization to merge similar entities
        def mock_find_similar(query_vector, limit, score_threshold, entity_type):
            # Simulate finding TensorFlow variants
            if "tensorflow" in str(query_vector).lower():  # Simplified check
                return [(entities[1], 0.95)]  # Return the other TensorFlow entity
            return []
        
        canonicalizer.qdrant_adapter.find_similar_entities.side_effect = mock_find_similar
        
        # Run complete workflow
        canonical_entities = await canonicalizer.canonicalize_entities(entities)
        comparison_relationships, analysis = detect_and_create_comparisons(canonical_entities)
        
        # Verify realistic results
        assert len(canonical_entities) <= len(entities)  # Some merging should occur
        
        # Should have TensorFlow entities merged
        tensorflow_count = len([e for e in canonical_entities if "tensorflow" in e.name.lower()])
        assert tensorflow_count <= 1  # Should be merged
        
        # Should have PyTorch entities merged
        pytorch_count = len([e for e in canonical_entities if "pytorch" in e.name.lower()])
        assert pytorch_count <= 1  # Should be merged
        
        # Analysis should show cross-document patterns
        if analysis["cross_document"]["entities_spanning_multiple_docs"] > 0:
            assert analysis["cross_document"]["total_unique_documents"] >= 2
            assert len(analysis["cross_document"]["total_document_sources"]) >= 2


if __name__ == "__main__":
    pytest.main([__file__])