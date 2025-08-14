"""
Integration tests for the entity canonicalization service.
Tests the canonicalization service with realistic entity data.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from models.core import Entity, EntityType, SourceSpan
from services.canonicalization import EntityCanonicalizer


class TestCanonicalizeIntegration:
    """Integration tests for entity canonicalization"""
    
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
    
    def test_realistic_entity_merging_scenario(self, canonicalizer):
        """Test a realistic entity merging scenario with ML entities"""
        # Create entities that should be merged
        ml_entity = Entity(
            name="Machine Learning",
            type=EntityType.CONCEPT,
            aliases=["ML", "machine learning"],
            salience=0.9,
            source_spans=[SourceSpan(doc_id="paper1", start=0, end=16)],
            summary="A method of data analysis that automates analytical model building"
        )
        
        ml_acronym_entity = Entity(
            name="ML",
            type=EntityType.CONCEPT,
            aliases=["Machine Learning"],
            salience=0.7,
            source_spans=[SourceSpan(doc_id="paper2", start=50, end=52)],
            summary="Machine Learning abbreviation"
        )
        
        # Create entity that should NOT be merged
        deep_learning_entity = Entity(
            name="Deep Learning",
            type=EntityType.CONCEPT,
            aliases=["DL", "deep learning"],
            salience=0.8,
            source_spans=[SourceSpan(doc_id="paper3", start=100, end=113)],
            summary="A subset of machine learning with neural networks"
        )
        
        entities = [ml_entity, ml_acronym_entity, deep_learning_entity]
        
        # Test merge decision logic
        should_merge_ml, reason_ml = canonicalizer._should_merge_entities(ml_entity, ml_acronym_entity)
        assert should_merge_ml is True
        assert "Alias/acronym match" in reason_ml
        
        should_merge_dl, reason_dl = canonicalizer._should_merge_entities(ml_entity, deep_learning_entity)
        assert should_merge_dl is False
        
        # Test entity merging
        merged_entity = canonicalizer._merge_entities([ml_entity, ml_acronym_entity])
        
        # Verify merged entity properties
        assert merged_entity.name == "Machine Learning"  # Higher salience entity's name
        assert "ML" in merged_entity.aliases
        assert "Machine Learning" in merged_entity.aliases
        assert len(merged_entity.source_spans) == 2
        assert merged_entity.salience > 0.7  # Should be weighted average
    
    def test_acronym_detection_comprehensive(self, canonicalizer):
        """Test comprehensive acronym detection scenarios"""
        test_cases = [
            ("Natural Language Processing (NLP)", {"NLP"}),
            ("The API uses REST and GraphQL", {"API", "REST"}),
            ("Machine Learning and AI systems", {"AI"}),
            ("TensorFlow is a ML framework", {"ML"}),
            ("No acronyms here", set()),
            ("Multiple (API) and (REST) acronyms", {"API", "REST"}),
        ]
        
        for text, expected_acronyms in test_cases:
            found_acronyms = canonicalizer._extract_acronyms(text)
            assert found_acronyms == expected_acronyms, f"Failed for text: {text}"
    
    def test_acronym_generation_comprehensive(self, canonicalizer):
        """Test comprehensive acronym generation scenarios"""
        test_cases = [
            ("Machine Learning", "ML"),
            ("Natural Language Processing", "NLP"),
            ("Artificial Intelligence", "AI"),
            ("Application Programming Interface", "API"),
            ("Association for Computing Machinery", "ACM"),  # Should filter common words
            ("Python", set()),  # Single word, no acronym
        ]
        
        for full_name, expected in test_cases:
            candidates = canonicalizer._generate_acronym_candidates(full_name)
            if isinstance(expected, str):
                assert expected in candidates, f"Expected '{expected}' in candidates for '{full_name}'"
            else:
                assert candidates == expected, f"Failed for: {full_name}"
    
    def test_vector_similarity_edge_cases(self, canonicalizer):
        """Test vector similarity calculation edge cases"""
        # Test with realistic embedding dimensions (3072)
        vec1 = [0.1] * 3072
        vec2 = [0.1] * 3072
        similarity = canonicalizer._calculate_cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0, rel=1e-6)
        
        # Test with zero vectors
        zero_vec = [0.0] * 3072
        similarity = canonicalizer._calculate_cosine_similarity(vec1, zero_vec)
        assert similarity == 0.0
        
        # Test with very small differences
        vec2_similar = [0.1001] * 3072
        similarity = canonicalizer._calculate_cosine_similarity(vec1, vec2_similar)
        assert similarity > 0.99
    
    def test_merge_statistics_calculation(self, canonicalizer):
        """Test merge statistics with realistic data"""
        # Original entities (before canonicalization)
        original_entities = [
            Entity(name="Python", type=EntityType.LIBRARY, salience=0.9),
            Entity(name="Python Programming Language", type=EntityType.LIBRARY, salience=0.7),
            Entity(name="Java", type=EntityType.LIBRARY, salience=0.8),
            Entity(name="Machine Learning", type=EntityType.CONCEPT, salience=0.9),
            Entity(name="ML", type=EntityType.CONCEPT, salience=0.6),
            Entity(name="Deep Learning", type=EntityType.CONCEPT, salience=0.8),
        ]
        
        # Canonical entities (after merging)
        canonical_entities = [
            Entity(name="Python", type=EntityType.LIBRARY, salience=0.85),  # Merged Python entities
            Entity(name="Java", type=EntityType.LIBRARY, salience=0.8),
            Entity(name="Machine Learning", type=EntityType.CONCEPT, salience=0.8),  # Merged ML entities
            Entity(name="Deep Learning", type=EntityType.CONCEPT, salience=0.8),
        ]
        
        stats = canonicalizer.get_merge_statistics(original_entities, canonical_entities)
        
        # Verify overall statistics
        assert stats["original_count"] == 6
        assert stats["canonical_count"] == 4
        assert stats["entities_merged"] == 2
        assert stats["merge_rate"] == pytest.approx(2/6, rel=1e-6)
        
        # Verify by-type statistics
        library_stats = stats["by_type"]["Library"]
        assert library_stats["original"] == 3
        assert library_stats["canonical"] == 2
        assert library_stats["merged"] == 1
        assert library_stats["merge_rate"] == pytest.approx(1/3, rel=1e-6)
        
        concept_stats = stats["by_type"]["Concept"]
        assert concept_stats["original"] == 3
        assert concept_stats["canonical"] == 2
        assert concept_stats["merged"] == 1
        assert concept_stats["merge_rate"] == pytest.approx(1/3, rel=1e-6)
    
    @pytest.mark.asyncio
    async def test_canonicalize_entities_realistic_workflow(self, canonicalizer):
        """Test the complete canonicalization workflow with realistic entities"""
        # Create a realistic set of entities that might come from IE extraction
        entities = [
            Entity(
                name="TensorFlow",
                type=EntityType.LIBRARY,
                aliases=["tensorflow"],
                salience=0.9,
                source_spans=[SourceSpan(doc_id="doc1", start=0, end=10)],
                summary="Open source machine learning framework"
            ),
            Entity(
                name="Tensorflow",  # Different capitalization
                type=EntityType.LIBRARY,
                aliases=["TF"],
                salience=0.7,
                source_spans=[SourceSpan(doc_id="doc2", start=20, end=30)],
                summary="Google's ML library"
            ),
            Entity(
                name="PyTorch",
                type=EntityType.LIBRARY,
                aliases=["pytorch"],
                salience=0.8,
                source_spans=[SourceSpan(doc_id="doc3", start=40, end=47)],
                summary="Facebook's deep learning framework"
            ),
            Entity(
                name="Machine Learning",
                type=EntityType.CONCEPT,
                aliases=["ML"],
                salience=0.9,
                source_spans=[SourceSpan(doc_id="doc4", start=60, end=76)],
                summary="Field of AI focused on learning from data"
            ),
            Entity(
                name="ML",
                type=EntityType.CONCEPT,
                aliases=["machine learning"],
                salience=0.6,
                source_spans=[SourceSpan(doc_id="doc5", start=80, end=82)],
                summary="Machine Learning abbreviation"
            ),
        ]
        
        # Run canonicalization
        canonical_entities = await canonicalizer.canonicalize_entities(entities)
        
        # Should have fewer entities due to merging
        assert len(canonical_entities) < len(entities)
        
        # Find the merged TensorFlow entity
        tensorflow_entities = [e for e in canonical_entities if "tensorflow" in e.name.lower()]
        assert len(tensorflow_entities) == 1
        tensorflow_entity = tensorflow_entities[0]
        
        # Should have combined aliases
        all_aliases = set(tensorflow_entity.aliases)
        assert "tensorflow" in all_aliases or "TF" in all_aliases
        
        # Should have combined source spans
        assert len(tensorflow_entity.source_spans) >= 2
        
        # Find the merged ML entity
        ml_entities = [e for e in canonical_entities if e.type == EntityType.CONCEPT and ("machine learning" in e.name.lower() or e.name == "ML")]
        assert len(ml_entities) == 1
        ml_entity = ml_entities[0]
        
        # Should have combined aliases
        ml_aliases = set(ml_entity.aliases)
        assert "ML" in ml_aliases or "machine learning" in ml_aliases
        
        # PyTorch should remain separate
        pytorch_entities = [e for e in canonical_entities if "pytorch" in e.name.lower()]
        assert len(pytorch_entities) == 1


if __name__ == "__main__":
    pytest.main([__file__])