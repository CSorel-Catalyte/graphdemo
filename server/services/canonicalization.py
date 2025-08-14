"""
Entity Canonicalization Service for the AI Knowledge Mapper.

This module provides entity deduplication and merging capabilities using:
- Vector similarity comparison (cosine ≥ 0.86)
- Alias matching and acronym detection
- Entity merging with salience score calculation
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime
from difflib import SequenceMatcher

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

from models.core import Entity, EntityType, SourceSpan

# Import QdrantAdapter only when needed to avoid import errors during testing
QdrantAdapter = None

logger = logging.getLogger(__name__)


class CanonicalizeError(Exception):
    """Base exception for canonicalization errors"""
    pass


class EntityCanonicalizer:
    """Service for entity canonicalization and deduplication"""
    
    def __init__(self, qdrant_adapter, similarity_threshold: float = 0.86):
        """
        Initialize the entity canonicalizer.
        
        Args:
            qdrant_adapter: Qdrant adapter for vector similarity search
            similarity_threshold: Minimum cosine similarity for entity merging (default: 0.86)
        """
        self.qdrant_adapter = qdrant_adapter
        self.similarity_threshold = similarity_threshold
        
        # Precompiled regex patterns for acronym detection
        self.acronym_pattern = re.compile(r'\b[A-Z]{2,}\b')
        self.parenthetical_pattern = re.compile(r'\(([^)]+)\)')
        
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score [0, 1]
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
            
        try:
            if NUMPY_AVAILABLE and np is not None:
                # Use numpy for efficient computation
                a = np.array(vec1, dtype=np.float32)
                b = np.array(vec2, dtype=np.float32)
                
                # Calculate cosine similarity
                dot_product = np.dot(a, b)
                norm_a = np.linalg.norm(a)
                norm_b = np.linalg.norm(b)
                
                if norm_a == 0 or norm_b == 0:
                    return 0.0
                    
                similarity = dot_product / (norm_a * norm_b)
            else:
                # Fallback to pure Python implementation
                dot_product = sum(a * b for a, b in zip(vec1, vec2))
                norm_a = sum(a * a for a in vec1) ** 0.5
                norm_b = sum(b * b for b in vec2) ** 0.5
                
                if norm_a == 0 or norm_b == 0:
                    return 0.0
                    
                similarity = dot_product / (norm_a * norm_b)
            
            # Ensure result is in [0, 1] range (cosine can be [-1, 1])
            return max(0.0, float(similarity))
            
        except Exception as e:
            logger.warning(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def _extract_acronyms(self, text: str) -> Set[str]:
        """
        Extract potential acronyms from text.
        
        Args:
            text: Input text
            
        Returns:
            Set of potential acronyms
        """
        acronyms = set()
        
        # Find standalone acronyms (2+ uppercase letters)
        matches = self.acronym_pattern.findall(text)
        acronyms.update(matches)
        
        # Find acronyms in parentheses
        parenthetical_matches = self.parenthetical_pattern.findall(text)
        for match in parenthetical_matches:
            if self.acronym_pattern.match(match.strip()):
                acronyms.add(match.strip())
        
        return acronyms
    
    def _generate_acronym_candidates(self, full_name: str) -> Set[str]:
        """
        Generate potential acronyms from a full name.
        
        Args:
            full_name: Full entity name
            
        Returns:
            Set of potential acronyms
        """
        candidates = set()
        
        # Split into words and take first letters
        words = re.findall(r'\b[A-Za-z]+\b', full_name)
        if len(words) >= 2:
            # Standard acronym (first letter of each word)
            acronym = ''.join(word[0].upper() for word in words)
            candidates.add(acronym)
            
            # Skip common words for better acronyms
            important_words = [w for w in words if w.lower() not in {'the', 'of', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'with', 'by'}]
            if len(important_words) >= 2 and len(important_words) != len(words):
                important_acronym = ''.join(word[0].upper() for word in important_words)
                candidates.add(important_acronym)
        
        return candidates
    
    def _is_alias_match(self, name1: str, name2: str, aliases1: List[str], aliases2: List[str]) -> bool:
        """
        Check if two entities match based on name and alias comparison.
        
        Args:
            name1: First entity name
            name2: Second entity name
            aliases1: First entity aliases
            aliases2: Second entity aliases
            
        Returns:
            True if entities match based on aliases
        """
        # Normalize names and aliases for comparison
        def normalize(text: str) -> str:
            return re.sub(r'[^\w\s]', '', text.lower().strip())
        
        # Collect all names and aliases for both entities
        all_names1 = {normalize(name1)} | {normalize(alias) for alias in aliases1}
        all_names2 = {normalize(name2)} | {normalize(alias) for alias in aliases2}
        
        # Remove empty strings
        all_names1 = {name for name in all_names1 if name}
        all_names2 = {name for name in all_names2 if name}
        
        # Check for exact matches
        if all_names1 & all_names2:
            return True
        
        # Check for acronym matches
        acronyms1 = set()
        acronyms2 = set()
        
        for name in [name1] + aliases1:
            acronyms1.update(self._extract_acronyms(name))
            acronyms1.update(self._generate_acronym_candidates(name))
        
        for name in [name2] + aliases2:
            acronyms2.update(self._extract_acronyms(name))
            acronyms2.update(self._generate_acronym_candidates(name))
        
        # Check if any acronym from one entity matches a name/alias from the other
        normalized_acronyms1 = {normalize(acr) for acr in acronyms1}
        normalized_acronyms2 = {normalize(acr) for acr in acronyms2}
        
        if (normalized_acronyms1 & all_names2) or (normalized_acronyms2 & all_names1):
            return True
        
        # Also check if acronyms match each other
        if normalized_acronyms1 & normalized_acronyms2:
            return True
        
        # Check for high string similarity (for typos, variations)
        for n1 in all_names1:
            for n2 in all_names2:
                if len(n1) >= 3 and len(n2) >= 3:  # Only for reasonably long names
                    similarity = SequenceMatcher(None, n1, n2).ratio()
                    if similarity >= 0.9:  # Very high similarity threshold
                        return True
        
        return False
    
    def _should_merge_entities(self, entity1: Entity, entity2: Entity) -> Tuple[bool, str]:
        """
        Determine if two entities should be merged.
        
        Args:
            entity1: First entity
            entity2: Second entity
            
        Returns:
            Tuple of (should_merge: bool, reason: str)
        """
        # Entities must be of the same type to merge
        if entity1.type != entity2.type:
            return False, "Different entity types"
        
        # Check vector similarity if both have embeddings
        if entity1.embedding and entity2.embedding:
            similarity = self._calculate_cosine_similarity(entity1.embedding, entity2.embedding)
            if similarity >= self.similarity_threshold:
                return True, f"Vector similarity: {similarity:.3f}"
        
        # Check alias matching
        if self._is_alias_match(entity1.name, entity2.name, entity1.aliases, entity2.aliases):
            return True, "Alias/acronym match"
        
        return False, "No match criteria met"
    
    def _merge_entities(self, entities: List[Entity]) -> Entity:
        """
        Merge multiple entities into a single canonical entity.
        Enhanced for multi-document processing with improved source span tracking.
        
        Args:
            entities: List of entities to merge
            
        Returns:
            Merged canonical entity
        """
        if not entities:
            raise CanonicalizeError("Cannot merge empty entity list")
        
        if len(entities) == 1:
            return entities[0]
        
        # Sort entities by salience (highest first) to prioritize canonical name
        sorted_entities = sorted(entities, key=lambda e: e.salience, reverse=True)
        primary_entity = sorted_entities[0]
        
        # Merge attributes with enhanced cross-document tracking
        merged_aliases = set(primary_entity.aliases)
        merged_source_spans = list(primary_entity.source_spans)
        merged_salience_scores = [primary_entity.salience]
        
        # Track document sources for cross-document analysis
        document_sources = set()
        for span in primary_entity.source_spans:
            document_sources.add(span.doc_id)
        
        # Add names and aliases from other entities
        for entity in sorted_entities[1:]:
            # Add the entity name as an alias if it's different from primary
            if entity.name.lower() != primary_entity.name.lower():
                merged_aliases.add(entity.name)
            
            # Add all aliases with deduplication
            merged_aliases.update(entity.aliases)
            
            # Add source spans with cross-document tracking
            for span in entity.source_spans:
                merged_source_spans.append(span)
                document_sources.add(span.doc_id)
            
            # Collect salience scores for averaging
            merged_salience_scores.append(entity.salience)
        
        # Enhanced salience calculation for multi-document entities
        # Give higher weight to entities that appear in multiple documents
        document_count = len(document_sources)
        cross_document_bonus = min(0.1, (document_count - 1) * 0.05)  # Up to 10% bonus
        
        # Calculate combined salience (weighted average based on number of source spans)
        total_spans = len(merged_source_spans)
        if total_spans > 0:
            # Weight by number of source spans per entity
            weighted_salience = 0.0
            total_weight = 0
            
            for entity in sorted_entities:
                weight = len(entity.source_spans) if entity.source_spans else 1
                weighted_salience += entity.salience * weight
                total_weight += weight
            
            base_salience = weighted_salience / total_weight if total_weight > 0 else primary_entity.salience
            final_salience = min(1.0, base_salience + cross_document_bonus)
        else:
            # Fallback to simple average with cross-document bonus
            base_salience = sum(merged_salience_scores) / len(merged_salience_scores)
            final_salience = min(1.0, base_salience + cross_document_bonus)
        
        # Enhanced summary generation for multi-document entities
        enhanced_summary = primary_entity.summary
        if document_count > 1:
            enhanced_summary = f"{primary_entity.summary} (appears in {document_count} documents)"
        
        # Create merged entity
        merged_entity = Entity(
            id=primary_entity.id,  # Keep primary entity's ID
            name=primary_entity.name,  # Keep primary entity's name
            type=primary_entity.type,
            aliases=sorted(list(merged_aliases)),  # Remove duplicates and sort
            embedding=primary_entity.embedding,  # Keep primary entity's embedding
            salience=final_salience,
            source_spans=merged_source_spans,
            summary=enhanced_summary,
            created_at=min(entity.created_at for entity in sorted_entities),  # Earliest creation
            updated_at=datetime.utcnow()  # Current time for update
        )
        
        logger.info(
            f"Merged {len(entities)} entities into '{merged_entity.name}' "
            f"(salience: {final_salience:.3f}, aliases: {len(merged_aliases)}, "
            f"documents: {document_count}, spans: {total_spans})"
        )
        
        return merged_entity
    
    async def find_similar_entities(self, entity: Entity) -> List[Tuple[Entity, float, str]]:
        """
        Find entities similar to the given entity.
        
        Args:
            entity: Entity to find similarities for
            
        Returns:
            List of (similar_entity, similarity_score, match_reason) tuples
        """
        similar_entities = []
        
        try:
            # Vector similarity search if entity has embedding
            if entity.embedding:
                vector_results = await self.qdrant_adapter.find_similar_entities(
                    query_vector=entity.embedding,
                    limit=20,  # Get more candidates for thorough checking
                    score_threshold=0.7,  # Lower threshold for initial filtering
                    entity_type=entity.type
                )
                
                for similar_entity, score in vector_results:
                    # Skip self-comparison
                    if similar_entity.id == entity.id:
                        continue
                    
                    # Check if entities should merge
                    should_merge, reason = self._should_merge_entities(entity, similar_entity)
                    if should_merge:
                        similar_entities.append((similar_entity, score, reason))
            
            # TODO: Add text-based similarity search for entities without embeddings
            # This would involve searching by name/aliases in the database
            
        except Exception as e:
            logger.error(f"Error finding similar entities for {entity.id}: {e}")
        
        return similar_entities
    
    async def canonicalize_entity(self, entity: Entity) -> Entity:
        """
        Canonicalize a single entity by finding and merging with similar entities.
        
        Args:
            entity: Entity to canonicalize
            
        Returns:
            Canonicalized entity (may be the same if no merging occurred)
        """
        try:
            # Find similar entities
            similar_entities = await self.find_similar_entities(entity)
            
            if not similar_entities:
                logger.debug(f"No similar entities found for '{entity.name}'")
                return entity
            
            # Collect entities to merge
            entities_to_merge = [entity]
            merge_reasons = []
            
            for similar_entity, score, reason in similar_entities:
                entities_to_merge.append(similar_entity)
                merge_reasons.append(f"{similar_entity.name} ({reason})")
            
            logger.info(
                f"Canonicalizing '{entity.name}' with {len(similar_entities)} similar entities: "
                f"{', '.join(merge_reasons)}"
            )
            
            # Merge entities
            canonical_entity = self._merge_entities(entities_to_merge)
            
            return canonical_entity
            
        except Exception as e:
            logger.error(f"Error canonicalizing entity {entity.id}: {e}")
            return entity
    
    async def canonicalize_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Canonicalize a list of entities, handling cross-entity merging.
        
        Args:
            entities: List of entities to canonicalize
            
        Returns:
            List of canonicalized entities (may be shorter due to merging)
        """
        if not entities:
            return []
        
        logger.info(f"Starting canonicalization of {len(entities)} entities")
        
        try:
            # Group entities by type for more efficient processing
            entities_by_type = {}
            for entity in entities:
                if entity.type not in entities_by_type:
                    entities_by_type[entity.type] = []
                entities_by_type[entity.type].append(entity)
            
            canonical_entities = []
            processed_ids = set()
            
            # Process each type separately
            for entity_type, type_entities in entities_by_type.items():
                logger.debug(f"Processing {len(type_entities)} entities of type {entity_type}")
                
                # Build similarity matrix for entities of this type
                merge_groups = []
                
                for i, entity in enumerate(type_entities):
                    if entity.id in processed_ids:
                        continue
                    
                    # Start a new merge group with this entity
                    current_group = [entity]
                    processed_ids.add(entity.id)
                    
                    # Check similarity with remaining entities
                    for j, other_entity in enumerate(type_entities[i+1:], i+1):
                        if other_entity.id in processed_ids:
                            continue
                        
                        should_merge, reason = self._should_merge_entities(entity, other_entity)
                        if should_merge:
                            current_group.append(other_entity)
                            processed_ids.add(other_entity.id)
                            logger.debug(f"Grouping '{entity.name}' with '{other_entity.name}': {reason}")
                    
                    merge_groups.append(current_group)
                
                # Merge each group
                for group in merge_groups:
                    if len(group) == 1:
                        canonical_entities.append(group[0])
                    else:
                        merged_entity = self._merge_entities(group)
                        canonical_entities.append(merged_entity)
            
            logger.info(
                f"Canonicalization complete: {len(entities)} entities -> {len(canonical_entities)} canonical entities "
                f"({len(entities) - len(canonical_entities)} merges)"
            )
            
            return canonical_entities
            
        except Exception as e:
            logger.error(f"Error during entity canonicalization: {e}")
            return entities  # Return original entities on error
    
    def get_merge_statistics(self, original_entities: List[Entity], canonical_entities: List[Entity]) -> Dict[str, any]:
        """
        Calculate statistics about the canonicalization process.
        Enhanced with cross-document analysis.
        
        Args:
            original_entities: Original entity list
            canonical_entities: Canonicalized entity list
            
        Returns:
            Dictionary with merge statistics including cross-document metrics
        """
        stats = {
            "original_count": len(original_entities),
            "canonical_count": len(canonical_entities),
            "entities_merged": len(original_entities) - len(canonical_entities),
            "merge_rate": (len(original_entities) - len(canonical_entities)) / len(original_entities) if original_entities else 0,
            "by_type": {},
            "cross_document": {
                "entities_spanning_multiple_docs": 0,
                "total_document_sources": set(),
                "average_docs_per_entity": 0.0,
                "max_docs_per_entity": 0
            }
        }
        
        # Count by entity type
        for entities, label in [(original_entities, "original"), (canonical_entities, "canonical")]:
            type_counts = {}
            for entity in entities:
                type_name = entity.type.value
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            for type_name, count in type_counts.items():
                if type_name not in stats["by_type"]:
                    stats["by_type"][type_name] = {}
                stats["by_type"][type_name][label] = count
        
        # Calculate merge rates by type
        for type_name, type_stats in stats["by_type"].items():
            original = type_stats.get("original", 0)
            canonical = type_stats.get("canonical", 0)
            type_stats["merged"] = original - canonical
            type_stats["merge_rate"] = (original - canonical) / original if original > 0 else 0
        
        # Analyze cross-document statistics for canonical entities
        total_doc_count = 0
        max_docs = 0
        
        for entity in canonical_entities:
            # Count unique documents for this entity
            entity_docs = set()
            for span in entity.source_spans:
                entity_docs.add(span.doc_id)
                stats["cross_document"]["total_document_sources"].add(span.doc_id)
            
            doc_count = len(entity_docs)
            total_doc_count += doc_count
            max_docs = max(max_docs, doc_count)
            
            if doc_count > 1:
                stats["cross_document"]["entities_spanning_multiple_docs"] += 1
        
        # Calculate averages
        if canonical_entities:
            stats["cross_document"]["average_docs_per_entity"] = total_doc_count / len(canonical_entities)
        
        stats["cross_document"]["max_docs_per_entity"] = max_docs
        stats["cross_document"]["total_unique_documents"] = len(stats["cross_document"]["total_document_sources"])
        
        # Convert set to list for JSON serialization
        stats["cross_document"]["total_document_sources"] = list(stats["cross_document"]["total_document_sources"])
        
        return stats
    
    def get_cross_document_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Get entities that span multiple documents.
        
        Args:
            entities: List of entities to analyze
            
        Returns:
            List of entities that appear in multiple documents
        """
        cross_document_entities = []
        
        for entity in entities:
            # Count unique documents for this entity
            entity_docs = set()
            for span in entity.source_spans:
                entity_docs.add(span.doc_id)
            
            if len(entity_docs) > 1:
                cross_document_entities.append(entity)
        
        return cross_document_entities


# Convenience functions for direct usage
async def canonicalize_entity(entity: Entity, qdrant_adapter, similarity_threshold: float = 0.86) -> Entity:
    """
    Convenience function to canonicalize a single entity.
    
    Args:
        entity: Entity to canonicalize
        qdrant_adapter: Qdrant adapter for similarity search
        similarity_threshold: Minimum similarity threshold for merging
        
    Returns:
        Canonicalized entity
    """
    canonicalizer = EntityCanonicalizer(qdrant_adapter, similarity_threshold)
    return await canonicalizer.canonicalize_entity(entity)


async def canonicalize_entities(entities: List[Entity], qdrant_adapter, similarity_threshold: float = 0.86) -> List[Entity]:
    """
    Convenience function to canonicalize a list of entities.
    
    Args:
        entities: List of entities to canonicalize
        qdrant_adapter: Qdrant adapter for similarity search
        similarity_threshold: Minimum similarity threshold for merging
        
    Returns:
        List of canonicalized entities
    """
    canonicalizer = EntityCanonicalizer(qdrant_adapter, similarity_threshold)
    return await canonicalizer.canonicalize_entities(entities)