"""
Unit tests for the entity canonicalization service.
Tests vector similarity, alias matching, acronym detection, and entity merging logic.
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

# Mock external dependencies that might not be available
try:
    import numpy as np
except ImportError:
    # Mock numpy if not available
    np = Mock()
    np.array = lambda x, dtype=None: x
    np.dot = lambda a, b: sum(x * y for x, y in zip(a, b))
    np.linalg = Mock()
    np.linalg.norm = lambda x: (sum(xi ** 2 for xi in x)) ** 0.5
    sys.modules['numpy'] = np

from models.core import Entity, EntityType, SourceSpan
from services.canonicalization import EntityCanonicalizer, CanonicalizeError


class TestEntityCanonicalizer:
    """Test cases for EntityCanonicalizer class"""
    
    @pytest.fixture
    def mock_qdrant_adapter(self):
        """Create a mock Qdrant adapter"""
        adapter = Mock()
        adapter.find_similar_entities = AsyncMock(return_value=[])
        return adapter
    
    @pytest.fixture
    def canonicalizer(self, mock_qdrant_adapter):
        """Create EntityCanonicalizer instance with mock adapter"""
        return EntityCanonicalizer(mock_qdrant_adapter, similarity_threshold=0.86)
    
    @pytest.fixture
    def sample_entity(self):
        """Create a sample entity for testing"""
        return Entity(
            name="Machine Learning",
            type=EntityType.CONCEPT,
            aliases=["ML", "machine learning"],
            embedding=[0.1] * 3072,  # Mock embedding
            salience=0.8,
            source_spans=[SourceSpan(doc_id="doc1", start=0, end=10)],
            summary="A method of data analysis"
        )
    
    def test_calculate_cosine_similarity_identical_vectors(self, canonicalizer):
        """Test cosine similarity with identical vectors"""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]
        
        similarity = canonicalizer._calculate_cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0, rel=1e-6)
    
    def test_calculate_cosine_similarity_orthogonal_vectors(self, canonicalizer):
        """Test cosine similarity with orthogonal vectors"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        
        similarity = canonicalizer._calculate_cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0, abs=1e-6)
    
    def test_calculate_cosine_similarity_opposite_vectors(self, canonicalizer):
        """Test cosine similarity with opposite vectors"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        
        similarity = canonicalizer._calculate_cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0, abs=1e-6)  # Clipped to 0
    
    def test_calculate_cosine_similarity_empty_vectors(self, canonicalizer):
        """Test cosine similarity with empty vectors"""
        similarity = canonicalizer._calculate_cosine_similarity([], [])
        assert similarity == 0.0
    
    def test_calculate_cosine_similarity_different_lengths(self, canonicalizer):
        """Test cosine similarity with different length vectors"""
        vec1 = [1.0, 2.0]
        vec2 = [1.0, 2.0, 3.0]
        
        similarity = canonicalizer._calculate_cosine_similarity(vec1, vec2)
        assert similarity == 0.0
    
    def test_extract_acronyms_standalone(self, canonicalizer):
        """Test acronym extraction from standalone acronyms"""
        text = "The ML algorithm uses AI and NLP techniques."
        acronyms = canonicalizer._extract_acronyms(text)
        
        expected = {"ML", "AI", "NLP"}
        assert acronyms == expected
    
    def test_extract_acronyms_parenthetical(self, canonicalizer):
        """Test acronym extraction from parenthetical expressions"""
        text = "Machine Learning (ML) and Artificial Intelligence (AI) are related."
        acronyms = canonicalizer._extract_acronyms(text)
        
        expected = {"ML", "AI"}
        assert acronyms == expected
    
    def test_extract_acronyms_mixed(self, canonicalizer):
        """Test acronym extraction from mixed text"""
        text = "The API uses REST and GraphQL (GQL) protocols."
        acronyms = canonicalizer._extract_acronyms(text)
        
        expected = {"API", "REST", "GQL"}
        assert acronyms == expected
    
    def test_extract_acronyms_no_acronyms(self, canonicalizer):
        """Test acronym extraction with no acronyms"""
        text = "This is a simple sentence with no acronyms."
        acronyms = canonicalizer._extract_acronyms(text)
        
        assert acronyms == set()
    
    def test_generate_acronym_candidates_simple(self, canonicalizer):
        """Test acronym generation from simple phrase"""
        candidates = canonicalizer._generate_acronym_candidates("Machine Learning")
        assert "ML" in candidates
    
    def test_generate_acronym_candidates_multiple_words(self, canonicalizer):
        """Test acronym generation from multiple words"""
        candidates = canonicalizer._generate_acronym_candidates("Natural Language Processing")
        assert "NLP" in candidates
    
    def test_generate_acronym_candidates_with_common_words(self, canonicalizer):
        """Test acronym generation filtering common words"""
        candidates = canonicalizer._generate_acronym_candidates("Association for Computing Machinery")
        
        # Should generate both full acronym and filtered version
        assert "ACM" in candidates or "AFCM" in candidates
    
    def test_generate_acronym_candidates_single_word(self, canonicalizer):
        """Test acronym generation from single word"""
        candidates = canonicalizer._generate_acronym_candidates("Python")
        assert len(candidates) == 0  # No acronym for single word
    
    def test_is_alias_match_exact_name(self, canonicalizer):
        """Test alias matching with exact name match"""
        result = canonicalizer._is_alias_match(
            "Machine Learning", "machine learning", [], []
        )
        assert result is True
    
    def test_is_alias_match_alias_to_name(self, canonicalizer):
        """Test alias matching where alias matches name"""
        result = canonicalizer._is_alias_match(
            "Machine Learning", "Deep Learning", ["ML"], ["Machine Learning"]
        )
        assert result is True
    
    def test_is_alias_match_acronym(self, canonicalizer):
        """Test alias matching with acronym"""
        result = canonicalizer._is_alias_match(
            "Machine Learning", "ML System", [], []
        )
        assert result is True
    
    def test_is_alias_match_no_match(self, canonicalizer):
        """Test alias matching with no match"""
        result = canonicalizer._is_alias_match(
            "Machine Learning", "Deep Learning", ["ML"], ["DL"]
        )
        assert result is False
    
    def test_is_alias_match_high_similarity(self, canonicalizer):
        """Test alias matching with high string similarity"""
        result = canonicalizer._is_alias_match(
            "TensorFlow", "Tensorflow", [], []
        )
        assert result is True
    
    def test_should_merge_entities_different_types(self, canonicalizer):
        """Test merge decision with different entity types"""
        entity1 = Entity(name="Python", type=EntityType.LIBRARY, embedding=[1.0] * 3072)
        entity2 = Entity(name="Python", type=EntityType.CONCEPT, embedding=[1.0] * 3072)
        
        should_merge, reason = canonicalizer._should_merge_entities(entity1, entity2)
        assert should_merge is False
        assert "Different entity types" in reason
    
    def test_should_merge_entities_high_similarity(self, canonicalizer):
        """Test merge decision with high vector similarity"""
        # Create very similar vectors
        vec1 = [1.0, 0.0, 0.0] + [0.0] * 3069
        vec2 = [0.99, 0.1, 0.0] + [0.0] * 3069  # Very similar
        
        entity1 = Entity(name="TensorFlow", type=EntityType.LIBRARY, embedding=vec1)
        entity2 = Entity(name="Tensorflow", type=EntityType.LIBRARY, embedding=vec2)
        
        should_merge, reason = canonicalizer._should_merge_entities(entity1, entity2)
        assert should_merge is True
        assert "Vector similarity" in reason
    
    def test_should_merge_entities_alias_match(self, canonicalizer):
        """Test merge decision with alias match"""
        entity1 = Entity(name="Machine Learning", type=EntityType.CONCEPT, aliases=["ML"])
        entity2 = Entity(name="ML Algorithm", type=EntityType.CONCEPT)
        
        should_merge, reason = canonicalizer._should_merge_entities(entity1, entity2)
        assert should_merge is True
        assert "Alias/acronym match" in reason
    
    def test_should_merge_entities_no_match(self, canonicalizer):
        """Test merge decision with no matching criteria"""
        entity1 = Entity(name="Python", type=EntityType.LIBRARY)
        entity2 = Entity(name="Java", type=EntityType.LIBRARY)
        
        should_merge, reason = canonicalizer._should_merge_entities(entity1, entity2)
        assert should_merge is False
        assert "No match criteria met" in reason
    
    def test_merge_entities_single_entity(self, canonicalizer):
        """Test merging with single entity"""
        entity = Entity(name="Python", type=EntityType.LIBRARY, salience=0.8)
        
        result = canonicalizer._merge_entities([entity])
        assert result == entity
    
    def test_merge_entities_empty_list(self, canonicalizer):
        """Test merging with empty list"""
        with pytest.raises(CanonicalizeError):
            canonicalizer._merge_entities([])
    
    def test_merge_entities_multiple(self, canonicalizer):
        """Test merging multiple entities"""
        entity1 = Entity(
            name="Machine Learning",
            type=EntityType.CONCEPT,
            aliases=["ML"],
            salience=0.9,
            source_spans=[SourceSpan(doc_id="doc1", start=0, end=10)],
            summary="Primary entity"
        )
        
        entity2 = Entity(
            name="ML",
            type=EntityType.CONCEPT,
            aliases=["machine learning"],
            salience=0.7,
            source_spans=[SourceSpan(doc_id="doc2", start=5, end=15)],
            summary="Secondary entity"
        )
        
        result = canonicalizer._merge_entities([entity1, entity2])
        
        # Should keep primary entity's name and ID
        assert result.name == "Machine Learning"
        assert result.id == entity1.id
        
        # Should merge aliases
        assert "ML" in result.aliases
        assert "machine learning" in result.aliases
        
        # Should combine source spans
        assert len(result.source_spans) == 2
        
        # Should calculate weighted salience
        assert result.salience > 0.7  # Should be between the two values
    
    def test_merge_entities_salience_calculation(self, canonicalizer):
        """Test salience calculation in entity merging"""
        # Entity with more source spans should have higher weight
        entity1 = Entity(
            name="Python",
            type=EntityType.LIBRARY,
            salience=0.6,
            source_spans=[SourceSpan(doc_id="doc1", start=0, end=5)]
        )
        
        entity2 = Entity(
            name="Python Library",
            type=EntityType.LIBRARY,
            salience=0.8,
            source_spans=[
                SourceSpan(doc_id="doc2", start=0, end=5),
                SourceSpan(doc_id="doc3", start=0, end=5),
                SourceSpan(doc_id="doc4", start=0, end=5)
            ]
        )
        
        result = canonicalizer._merge_entities([entity1, entity2])
        
        # Salience should be weighted toward entity2 (more source spans)
        assert result.salience > 0.7
    
    def test_merge_entities_cross_document_bonus(self, canonicalizer):
        """Test cross-document salience bonus in entity merging"""
        # Entity appearing in multiple documents should get salience bonus
        entity1 = Entity(
            name="Machine Learning",
            type=EntityType.CONCEPT,
            salience=0.7,
            source_spans=[
                SourceSpan(doc_id="doc1", start=0, end=10),
                SourceSpan(doc_id="doc2", start=5, end=15),
                SourceSpan(doc_id="doc3", start=10, end=20)
            ]
        )
        
        entity2 = Entity(
            name="ML",
            type=EntityType.CONCEPT,
            salience=0.6,
            source_spans=[SourceSpan(doc_id="doc1", start=20, end=25)]
        )
        
        result = canonicalizer._merge_entities([entity1, entity2])
        
        # Should get cross-document bonus (appears in 3 documents)
        assert result.salience > 0.7  # Base salience + cross-document bonus
        assert "appears in 3 documents" in result.summary
    
    def test_merge_entities_enhanced_summary(self, canonicalizer):
        """Test enhanced summary generation for multi-document entities"""
        entity1 = Entity(
            name="TensorFlow",
            type=EntityType.LIBRARY,
            salience=0.8,
            summary="Machine learning framework",
            source_spans=[
                SourceSpan(doc_id="doc1", start=0, end=10),
                SourceSpan(doc_id="doc2", start=0, end=10)
            ]
        )
        
        entity2 = Entity(
            name="Tensorflow",
            type=EntityType.LIBRARY,
            salience=0.7,
            summary="Deep learning library",
            source_spans=[SourceSpan(doc_id="doc3", start=0, end=10)]
        )
        
        result = canonicalizer._merge_entities([entity1, entity2])
        
        # Summary should indicate multi-document presence
        assert "appears in 3 documents" in result.summary
        assert result.summary.startswith("Machine learning framework")
    
    def test_get_cross_document_entities(self, canonicalizer):
        """Test identification of cross-document entities"""
        entities = [
            Entity(
                name="Python",
                type=EntityType.LIBRARY,
                source_spans=[
                    SourceSpan(doc_id="doc1", start=0, end=5),
                    SourceSpan(doc_id="doc2", start=0, end=5)
                ]
            ),
            Entity(
                name="Java",
                type=EntityType.LIBRARY,
                source_spans=[SourceSpan(doc_id="doc1", start=10, end=15)]
            ),
            Entity(
                name="Machine Learning",
                type=EntityType.CONCEPT,
                source_spans=[
                    SourceSpan(doc_id="doc1", start=20, end=30),
                    SourceSpan(doc_id="doc2", start=20, end=30),
                    SourceSpan(doc_id="doc3", start=20, end=30)
                ]
            )
        ]
        
        cross_doc_entities = canonicalizer.get_cross_document_entities(entities)
        
        # Should return Python and Machine Learning (both appear in multiple docs)
        assert len(cross_doc_entities) == 2
        names = [entity.name for entity in cross_doc_entities]
        assert "Python" in names
        assert "Machine Learning" in names
        assert "Java" not in names
    
    def test_get_merge_statistics_cross_document(self, canonicalizer):
        """Test enhanced merge statistics with cross-document analysis"""
        original_entities = [
            Entity(name="Python", type=EntityType.LIBRARY, source_spans=[
                SourceSpan(doc_id="doc1", start=0, end=5)
            ]),
            Entity(name="Python Lib", type=EntityType.LIBRARY, source_spans=[
                SourceSpan(doc_id="doc2", start=0, end=5)
            ]),
            Entity(name="Java", type=EntityType.LIBRARY, source_spans=[
                SourceSpan(doc_id="doc1", start=10, end=15)
            ])
        ]
        
        # Simulate merged entities (Python entities merged)
        canonical_entities = [
            Entity(
                name="Python",
                type=EntityType.LIBRARY,
                source_spans=[
                    SourceSpan(doc_id="doc1", start=0, end=5),
                    SourceSpan(doc_id="doc2", start=0, end=5)
                ]
            ),
            Entity(name="Java", type=EntityType.LIBRARY, source_spans=[
                SourceSpan(doc_id="doc1", start=10, end=15)
            ])
        ]
        
        stats = canonicalizer.get_merge_statistics(original_entities, canonical_entities)
        
        # Basic merge statistics
        assert stats["original_count"] == 3
        assert stats["canonical_count"] == 2
        assert stats["entities_merged"] == 1
        
        # Cross-document statistics
        assert stats["cross_document"]["entities_spanning_multiple_docs"] == 1  # Python
        assert stats["cross_document"]["total_unique_documents"] == 2
        assert stats["cross_document"]["max_docs_per_entity"] == 2
        assert stats["cross_document"]["average_docs_per_entity"] == 1.5  # (2 + 1) / 2
        assert "doc1" in stats["cross_document"]["total_document_sources"]
        assert "doc2" in stats["cross_document"]["total_document_sources"]
    
    @pytest.mark.asyncio
    async def test_find_similar_entities_with_vector(self, canonicalizer, mock_qdrant_adapter):
        """Test finding similar entities with vector similarity"""
        entity = Entity(
            name="Python",
            type=EntityType.LIBRARY,
            embedding=[1.0] * 3072
        )
        
        similar_entity = Entity(
            name="Python Library",
            type=EntityType.LIBRARY,
            embedding=[0.9] * 3072
        )
        
        # Mock Qdrant response
        mock_qdrant_adapter.find_similar_entities.return_value = [
            (similar_entity, 0.95)
        ]
        
        # Mock the merge decision
        with patch.object(canonicalizer, '_should_merge_entities', return_value=(True, "Vector similarity")):
            results = await canonicalizer.find_similar_entities(entity)
        
        assert len(results) == 1
        assert results[0][0] == similar_entity
        assert results[0][1] == 0.95
        assert results[0][2] == "Vector similarity"
    
    @pytest.mark.asyncio
    async def test_find_similar_entities_no_embedding(self, canonicalizer, mock_qdrant_adapter):
        """Test finding similar entities without embedding"""
        entity = Entity(
            name="Python",
            type=EntityType.LIBRARY,
            embedding=[]  # No embedding
        )
        
        results = await canonicalizer.find_similar_entities(entity)
        
        # Should return empty list when no embedding
        assert results == []
        mock_qdrant_adapter.find_similar_entities.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_canonicalize_entity_no_similar(self, canonicalizer, mock_qdrant_adapter):
        """Test canonicalizing entity with no similar entities"""
        entity = Entity(name="Unique Entity", type=EntityType.CONCEPT, embedding=[1.0] * 3072)
        
        # Mock no similar entities found
        mock_qdrant_adapter.find_similar_entities.return_value = []
        
        result = await canonicalizer.canonicalize_entity(entity)
        
        # Should return the same entity
        assert result == entity
    
    @pytest.mark.asyncio
    async def test_canonicalize_entity_with_similar(self, canonicalizer, mock_qdrant_adapter):
        """Test canonicalizing entity with similar entities"""
        entity = Entity(
            name="Machine Learning",
            type=EntityType.CONCEPT,
            embedding=[1.0] * 3072,
            salience=0.8
        )
        
        similar_entity = Entity(
            name="ML",
            type=EntityType.CONCEPT,
            embedding=[0.9] * 3072,
            salience=0.6
        )
        
        # Mock similar entity found
        mock_qdrant_adapter.find_similar_entities.return_value = [
            (similar_entity, 0.9)
        ]
        
        # Mock merge decision
        with patch.object(canonicalizer, '_should_merge_entities', return_value=(True, "Vector similarity")):
            result = await canonicalizer.canonicalize_entity(entity)
        
        # Should return merged entity (primary entity's name should be kept)
        assert result.name == "Machine Learning"
        assert "ML" in result.aliases
    
    @pytest.mark.asyncio
    async def test_canonicalize_entities_empty_list(self, canonicalizer):
        """Test canonicalizing empty entity list"""
        result = await canonicalizer.canonicalize_entities([])
        assert result == []
    
    @pytest.mark.asyncio
    async def test_canonicalize_entities_no_merging(self, canonicalizer):
        """Test canonicalizing entities with no merging needed"""
        entities = [
            Entity(name="Python", type=EntityType.LIBRARY),
            Entity(name="Java", type=EntityType.LIBRARY),
            Entity(name="JavaScript", type=EntityType.LIBRARY)
        ]
        
        # Mock no merging needed
        with patch.object(canonicalizer, '_should_merge_entities', return_value=(False, "No match")):
            result = await canonicalizer.canonicalize_entities(entities)
        
        assert len(result) == 3
        assert result == entities
    
    @pytest.mark.asyncio
    async def test_canonicalize_entities_with_merging(self, canonicalizer):
        """Test canonicalizing entities with merging"""
        entity1 = Entity(name="Machine Learning", type=EntityType.CONCEPT, salience=0.9)
        entity2 = Entity(name="ML", type=EntityType.CONCEPT, salience=0.7)
        entity3 = Entity(name="Deep Learning", type=EntityType.CONCEPT, salience=0.8)
        
        entities = [entity1, entity2, entity3]
        
        # Mock merge decision: entity1 and entity2 should merge
        def mock_should_merge(e1, e2):
            if (e1.name == "Machine Learning" and e2.name == "ML") or \
               (e1.name == "ML" and e2.name == "Machine Learning"):
                return True, "Alias match"
            return False, "No match"
        
        with patch.object(canonicalizer, '_should_merge_entities', side_effect=mock_should_merge):
            result = await canonicalizer.canonicalize_entities(entities)
        
        # Should have 2 entities (entity1 and entity2 merged, entity3 separate)
        assert len(result) == 2
        
        # Find the merged entity
        merged_entity = next((e for e in result if e.name == "Machine Learning"), None)
        assert merged_entity is not None
        assert "ML" in merged_entity.aliases
    
    def test_get_merge_statistics(self, canonicalizer):
        """Test merge statistics calculation"""
        original_entities = [
            Entity(name="Python", type=EntityType.LIBRARY),
            Entity(name="Python Lib", type=EntityType.LIBRARY),
            Entity(name="Java", type=EntityType.LIBRARY),
            Entity(name="ML", type=EntityType.CONCEPT),
            Entity(name="Machine Learning", type=EntityType.CONCEPT)
        ]
        
        canonical_entities = [
            Entity(name="Python", type=EntityType.LIBRARY),  # Merged Python entities
            Entity(name="Java", type=EntityType.LIBRARY),
            Entity(name="Machine Learning", type=EntityType.CONCEPT)  # Merged ML entities
        ]
        
        stats = canonicalizer.get_merge_statistics(original_entities, canonical_entities)
        
        assert stats["original_count"] == 5
        assert stats["canonical_count"] == 3
        assert stats["entities_merged"] == 2
        assert stats["merge_rate"] == 0.4
        
        # Check by-type statistics
        assert stats["by_type"]["Library"]["original"] == 3
        assert stats["by_type"]["Library"]["canonical"] == 2
        assert stats["by_type"]["Library"]["merged"] == 1
        
        assert stats["by_type"]["Concept"]["original"] == 2
        assert stats["by_type"]["Concept"]["canonical"] == 1
        assert stats["by_type"]["Concept"]["merged"] == 1


class TestCanonicalizeConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.mark.asyncio
    async def test_canonicalize_entity_function(self):
        """Test the convenience canonicalize_entity function"""
        from services.canonicalization import canonicalize_entity
        
        entity = Entity(name="Test Entity", type=EntityType.CONCEPT)
        mock_adapter = Mock()
        mock_adapter.find_similar_entities = AsyncMock(return_value=[])
        
        result = await canonicalize_entity(entity, mock_adapter)
        
        # Should return the same entity when no similar entities found
        assert result.name == entity.name
    
    @pytest.mark.asyncio
    async def test_canonicalize_entities_function(self):
        """Test the convenience canonicalize_entities function"""
        from services.canonicalization import canonicalize_entities
        
        entities = [
            Entity(name="Entity 1", type=EntityType.CONCEPT),
            Entity(name="Entity 2", type=EntityType.CONCEPT)
        ]
        mock_adapter = Mock()
        
        result = await canonicalize_entities(entities, mock_adapter)
        
        # Should return the same entities when no merging occurs
        assert len(result) == 2


if __name__ == "__main__":
    pytest.main([__file__])