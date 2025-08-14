"""
Unit tests for the conflict detection service.
Tests conflict detection, comparison relationship creation, and cross-document analysis.
"""

import pytest
from datetime import datetime
from typing import List
import sys
import os

# Add the server directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.core import Entity, EntityType, SourceSpan, Relationship, RelationType, Evidence
from services.conflict_detection import ConflictDetector, ConflictDetectionError, detect_and_create_comparisons


class TestConflictDetector:
    """Test cases for ConflictDetector class"""
    
    @pytest.fixture
    def detector(self):
        """Create ConflictDetector instance"""
        return ConflictDetector(similarity_threshold=0.7)
    
    @pytest.fixture
    def sample_entities(self):
        """Create sample entities for testing"""
        return [
            Entity(
                name="TensorFlow",
                type=EntityType.LIBRARY,
                salience=0.9,
                summary="Google's machine learning framework",
                source_spans=[SourceSpan(doc_id="doc1", start=0, end=10)]
            ),
            Entity(
                name="Tensorflow",
                type=EntityType.LIBRARY,
                salience=0.6,
                summary="Open source deep learning library",
                source_spans=[SourceSpan(doc_id="doc2", start=0, end=10)]
            ),
            Entity(
                name="PyTorch",
                type=EntityType.LIBRARY,
                salience=0.8,
                summary="Facebook's machine learning framework",
                source_spans=[SourceSpan(doc_id="doc3", start=0, end=10)]
            )
        ]
    
    def test_extract_conflicting_attributes_name_variation(self, detector):
        """Test conflict detection for name variations"""
        entity1 = Entity(
            name="TensorFlow",
            type=EntityType.LIBRARY,
            salience=0.8,
            summary="Machine learning framework"
        )
        
        entity2 = Entity(
            name="Tensorflow",
            type=EntityType.LIBRARY,
            salience=0.7,
            summary="Deep learning library"
        )
        
        conflicts = detector._extract_conflicting_attributes(entity1, entity2)
        
        # Should detect name variation
        assert len(conflicts) > 0
        assert any("Name variation" in conflict for conflict in conflicts)
    
    def test_extract_conflicting_attributes_salience_difference(self, detector):
        """Test conflict detection for salience differences"""
        entity1 = Entity(
            name="Python",
            type=EntityType.LIBRARY,
            salience=0.9,
            summary="Programming language"
        )
        
        entity2 = Entity(
            name="Python",
            type=EntityType.LIBRARY,
            salience=0.5,  # Significant difference
            summary="Programming language"
        )
        
        conflicts = detector._extract_conflicting_attributes(entity1, entity2)
        
        # Should detect salience difference
        assert len(conflicts) > 0
        assert any("Salience difference" in conflict for conflict in conflicts)
    
    def test_extract_conflicting_attributes_summary_difference(self, detector):
        """Test conflict detection for summary differences"""
        entity1 = Entity(
            name="Machine Learning",
            type=EntityType.CONCEPT,
            salience=0.8,
            summary="A method of data analysis that automates analytical model building"
        )
        
        entity2 = Entity(
            name="Machine Learning",
            type=EntityType.CONCEPT,
            salience=0.8,
            summary="A subset of artificial intelligence focused on pattern recognition"
        )
        
        conflicts = detector._extract_conflicting_attributes(entity1, entity2)
        
        # Should detect summary difference
        assert len(conflicts) > 0
        assert any("Summary difference" in conflict for conflict in conflicts)
    
    def test_get_document_sources(self, detector):
        """Test document source extraction"""
        entity = Entity(
            name="Test Entity",
            type=EntityType.CONCEPT,
            source_spans=[
                SourceSpan(doc_id="doc1", start=0, end=10),
                SourceSpan(doc_id="doc2", start=5, end=15),
                SourceSpan(doc_id="doc1", start=20, end=30)  # Duplicate doc
            ]
        )
        
        docs = detector._get_document_sources(entity)
        
        assert docs == {"doc1", "doc2"}
        assert len(docs) == 2
    
    def test_should_create_comparison_relationship_different_types(self, detector):
        """Test comparison decision with different entity types"""
        entity1 = Entity(name="Python", type=EntityType.LIBRARY, source_spans=[
            SourceSpan(doc_id="doc1", start=0, end=5)
        ])
        entity2 = Entity(name="Python", type=EntityType.CONCEPT, source_spans=[
            SourceSpan(doc_id="doc2", start=0, end=5)
        ])
        
        should_create, reason, conflicts = detector._should_create_comparison_relationship(entity1, entity2)
        
        assert should_create is False
        assert "Different entity types" in reason
    
    def test_should_create_comparison_relationship_same_documents(self, detector):
        """Test comparison decision with same document sources"""
        entity1 = Entity(name="TensorFlow", type=EntityType.LIBRARY, source_spans=[
            SourceSpan(doc_id="doc1", start=0, end=5)
        ])
        entity2 = Entity(name="Tensorflow", type=EntityType.LIBRARY, source_spans=[
            SourceSpan(doc_id="doc1", start=10, end=15)
        ])
        
        should_create, reason, conflicts = detector._should_create_comparison_relationship(entity1, entity2)
        
        assert should_create is False
        assert "Same document sources" in reason
    
    def test_should_create_comparison_relationship_overlapping_documents(self, detector):
        """Test comparison decision with overlapping document sources"""
        entity1 = Entity(name="TensorFlow", type=EntityType.LIBRARY, source_spans=[
            SourceSpan(doc_id="doc1", start=0, end=5),
            SourceSpan(doc_id="doc2", start=0, end=5)
        ])
        entity2 = Entity(name="Tensorflow", type=EntityType.LIBRARY, source_spans=[
            SourceSpan(doc_id="doc2", start=10, end=15),
            SourceSpan(doc_id="doc3", start=0, end=5)
        ])
        
        should_create, reason, conflicts = detector._should_create_comparison_relationship(entity1, entity2)
        
        assert should_create is False
        assert "Overlapping document sources" in reason
    
    def test_should_create_comparison_relationship_valid_conflict(self, detector):
        """Test comparison decision with valid conflict scenario"""
        entity1 = Entity(
            name="TensorFlow",
            type=EntityType.LIBRARY,
            salience=0.9,
            summary="Google's machine learning framework",
            source_spans=[SourceSpan(doc_id="doc1", start=0, end=10)]
        )
        
        entity2 = Entity(
            name="Tensorflow",
            type=EntityType.LIBRARY,
            salience=0.5,  # Significant salience difference
            summary="Open source deep learning library",
            source_spans=[SourceSpan(doc_id="doc2", start=0, end=10)]
        )
        
        should_create, reason, conflicts = detector._should_create_comparison_relationship(entity1, entity2)
        
        assert should_create is True
        assert "Similar names with conflicts" in reason
        assert len(conflicts) > 0
    
    def test_detect_conflicts_in_entities_no_conflicts(self, detector):
        """Test conflict detection with no conflicts"""
        entities = [
            Entity(name="Python", type=EntityType.LIBRARY, source_spans=[
                SourceSpan(doc_id="doc1", start=0, end=5)
            ]),
            Entity(name="Java", type=EntityType.LIBRARY, source_spans=[
                SourceSpan(doc_id="doc2", start=0, end=5)
            ])
        ]
        
        conflicts = detector.detect_conflicts_in_entities(entities)
        
        assert len(conflicts) == 0
    
    def test_detect_conflicts_in_entities_with_conflicts(self, detector, sample_entities):
        """Test conflict detection with actual conflicts"""
        conflicts = detector.detect_conflicts_in_entities(sample_entities)
        
        # Should detect conflict between TensorFlow and Tensorflow
        assert len(conflicts) > 0
        
        # Check that the conflict involves the similar entities
        conflict_names = []
        for entity1, entity2, reason, conflict_list in conflicts:
            conflict_names.extend([entity1.name, entity2.name])
        
        assert "TensorFlow" in conflict_names
        assert "Tensorflow" in conflict_names
    
    def test_create_comparison_relationships(self, detector):
        """Test creation of comparison relationships"""
        entity1 = Entity(
            name="TensorFlow",
            type=EntityType.LIBRARY,
            salience=0.9,
            summary="Google's framework",
            source_spans=[SourceSpan(doc_id="doc1", start=0, end=10)]
        )
        
        entity2 = Entity(
            name="Tensorflow",
            type=EntityType.LIBRARY,
            salience=0.6,
            summary="Open source library",
            source_spans=[SourceSpan(doc_id="doc2", start=0, end=10)]
        )
        
        conflict_pairs = [(entity1, entity2, "Test conflict", ["Name variation", "Salience difference"])]
        
        relationships = detector.create_comparison_relationships(conflict_pairs)
        
        # Should create bidirectional relationships
        assert len(relationships) == 2
        
        # Check relationship properties
        for rel in relationships:
            assert rel.predicate == RelationType.COMPARES_WITH
            assert rel.confidence == 0.8
            assert rel.directional is False
            assert len(rel.evidence) > 0
        
        # Check bidirectionality
        from_entities = {rel.from_entity for rel in relationships}
        to_entities = {rel.to_entity for rel in relationships}
        assert entity1.id in from_entities and entity1.id in to_entities
        assert entity2.id in from_entities and entity2.id in to_entities
    
    def test_analyze_cross_document_patterns(self, detector):
        """Test cross-document pattern analysis"""
        entities = [
            Entity(
                name="TensorFlow",
                type=EntityType.LIBRARY,
                source_spans=[
                    SourceSpan(doc_id="doc1", start=0, end=10),
                    SourceSpan(doc_id="doc2", start=0, end=10)  # Cross-document
                ]
            ),
            Entity(
                name="PyTorch",
                type=EntityType.LIBRARY,
                source_spans=[SourceSpan(doc_id="doc3", start=0, end=10)]
            )
        ]
        
        relationships = [
            Relationship(
                from_entity=entities[0].id,
                to_entity=entities[1].id,
                predicate=RelationType.COMPARES_WITH,
                confidence=0.8,
                evidence=[],
                directional=False
            ),
            Relationship(
                from_entity=entities[1].id,
                to_entity=entities[0].id,
                predicate=RelationType.COMPARES_WITH,
                confidence=0.8,
                evidence=[],
                directional=False
            )
        ]
        
        analysis = detector.analyze_cross_document_patterns(entities, relationships)
        
        assert analysis["total_entities"] == 2
        assert analysis["cross_document_entities"] == 1  # TensorFlow appears in 2 docs
        assert analysis["comparison_relationships"] == 2
        assert len(analysis["most_conflicted_entities"]) > 0
        assert analysis["entity_conflicts_by_type"]["Library"] == 2
    
    def test_analyze_cross_document_patterns_empty(self, detector):
        """Test cross-document pattern analysis with empty inputs"""
        analysis = detector.analyze_cross_document_patterns([], [])
        
        assert analysis["total_entities"] == 0
        assert analysis["cross_document_entities"] == 0
        assert analysis["comparison_relationships"] == 0
        assert len(analysis["most_conflicted_entities"]) == 0
        assert len(analysis["document_pairs"]) == 0


class TestConflictDetectionConvenienceFunctions:
    """Test convenience functions"""
    
    def test_detect_and_create_comparisons(self):
        """Test the convenience function for complete conflict detection workflow"""
        entities = [
            Entity(
                name="TensorFlow",
                type=EntityType.LIBRARY,
                salience=0.9,
                summary="Google's machine learning framework",
                source_spans=[SourceSpan(doc_id="doc1", start=0, end=10)]
            ),
            Entity(
                name="Tensorflow",
                type=EntityType.LIBRARY,
                salience=0.5,
                summary="Open source deep learning library",
                source_spans=[SourceSpan(doc_id="doc2", start=0, end=10)]
            )
        ]
        
        relationships, analysis = detect_and_create_comparisons(entities)
        
        # Should create comparison relationships
        assert len(relationships) > 0
        assert all(rel.predicate == RelationType.COMPARES_WITH for rel in relationships)
        
        # Should provide analysis
        assert analysis["total_entities"] == 2
        assert analysis["comparison_relationships"] > 0
    
    def test_detect_and_create_comparisons_no_conflicts(self):
        """Test convenience function with no conflicts"""
        entities = [
            Entity(
                name="Python",
                type=EntityType.LIBRARY,
                source_spans=[SourceSpan(doc_id="doc1", start=0, end=5)]
            ),
            Entity(
                name="Java",
                type=EntityType.LIBRARY,
                source_spans=[SourceSpan(doc_id="doc2", start=0, end=5)]
            )
        ]
        
        relationships, analysis = detect_and_create_comparisons(entities)
        
        # Should not create any relationships
        assert len(relationships) == 0
        assert analysis["comparison_relationships"] == 0


class TestConflictDetectionIntegration:
    """Integration tests for conflict detection with realistic scenarios"""
    
    def test_multi_document_tensorflow_pytorch_conflict(self):
        """Test realistic conflict scenario between ML frameworks"""
        entities = [
            Entity(
                name="TensorFlow",
                type=EntityType.LIBRARY,
                salience=0.9,
                summary="Google's open source machine learning framework for research and production",
                source_spans=[
                    SourceSpan(doc_id="google_blog", start=0, end=50),
                    SourceSpan(doc_id="google_blog", start=100, end=150)
                ]
            ),
            Entity(
                name="Tensorflow",
                type=EntityType.LIBRARY,
                salience=0.6,
                summary="Deep learning library developed by Google Brain team",
                source_spans=[
                    SourceSpan(doc_id="wikipedia", start=0, end=40),
                    SourceSpan(doc_id="wikipedia", start=200, end=240)
                ]
            ),
            Entity(
                name="PyTorch",
                type=EntityType.LIBRARY,
                salience=0.8,
                summary="Facebook's machine learning library with dynamic computation graphs",
                source_spans=[
                    SourceSpan(doc_id="pytorch_docs", start=0, end=60),
                    SourceSpan(doc_id="comparison_article", start=0, end=30)
                ]
            )
        ]
        
        detector = ConflictDetector(similarity_threshold=0.7)
        conflicts = detector.detect_conflicts_in_entities(entities)
        
        # Should detect conflict between TensorFlow variants
        assert len(conflicts) > 0
        
        # Create relationships
        relationships = detector.create_comparison_relationships(conflicts)
        assert len(relationships) > 0
        
        # Analyze patterns
        analysis = detector.analyze_cross_document_patterns(entities, relationships)
        assert analysis["comparison_relationships"] > 0
        assert len(analysis["document_pairs"]) > 0
    
    def test_cross_document_entity_no_conflict(self):
        """Test entity appearing in multiple documents without conflicts"""
        entities = [
            Entity(
                name="Machine Learning",
                type=EntityType.CONCEPT,
                salience=0.8,
                summary="A method of data analysis that automates analytical model building",
                source_spans=[
                    SourceSpan(doc_id="doc1", start=0, end=20),
                    SourceSpan(doc_id="doc2", start=0, end=20),
                    SourceSpan(doc_id="doc3", start=0, end=20)
                ]
            ),
            Entity(
                name="Deep Learning",
                type=EntityType.CONCEPT,
                salience=0.7,
                summary="A subset of machine learning using neural networks",
                source_spans=[SourceSpan(doc_id="doc4", start=0, end=20)]
            )
        ]
        
        detector = ConflictDetector()
        conflicts = detector.detect_conflicts_in_entities(entities)
        
        # Should not detect conflicts (different names, no similarity)
        assert len(conflicts) == 0
        
        # But should recognize cross-document entity
        analysis = detector.analyze_cross_document_patterns(entities, [])
        assert analysis["cross_document_entities"] == 1  # Machine Learning spans 3 docs


if __name__ == "__main__":
    pytest.main([__file__])