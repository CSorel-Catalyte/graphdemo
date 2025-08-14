"""
Conflict Detection Service for the AI Knowledge Mapper.

This module provides conflict detection and comparison relationship creation for:
- Detecting conflicting information between documents
- Creating "compares_with" relationships between entities
- Analyzing cross-document relationship patterns
"""

import logging
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime
from difflib import SequenceMatcher

from models.core import Entity, Relationship, RelationType, Evidence, SourceSpan

logger = logging.getLogger(__name__)


class ConflictDetectionError(Exception):
    """Base exception for conflict detection errors"""
    pass


class ConflictDetector:
    """Service for detecting conflicts and creating comparison relationships"""
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        Initialize the conflict detector.
        
        Args:
            similarity_threshold: Minimum similarity for considering entities as potentially conflicting
        """
        self.similarity_threshold = similarity_threshold
    
    def _extract_conflicting_attributes(self, entity1: Entity, entity2: Entity) -> List[str]:
        """
        Extract attributes that might be conflicting between two entities.
        
        Args:
            entity1: First entity
            entity2: Second entity
            
        Returns:
            List of conflicting attribute descriptions
        """
        conflicts = []
        
        # Check for different names with similar meanings (potential conflicts)
        if entity1.name.lower() != entity2.name.lower():
            name_similarity = SequenceMatcher(None, entity1.name.lower(), entity2.name.lower()).ratio()
            if name_similarity > self.similarity_threshold:
                conflicts.append(f"Name variation: '{entity1.name}' vs '{entity2.name}'")
        
        # Check for significantly different salience scores (might indicate conflicting importance)
        salience_diff = abs(entity1.salience - entity2.salience)
        if salience_diff > 0.3:  # Significant difference threshold
            conflicts.append(f"Salience difference: {entity1.salience:.2f} vs {entity2.salience:.2f}")
        
        # Check for different summary content (potential semantic conflicts)
        if entity1.summary and entity2.summary:
            summary_similarity = SequenceMatcher(None, entity1.summary.lower(), entity2.summary.lower()).ratio()
            if summary_similarity < 0.5 and len(entity1.summary) > 10 and len(entity2.summary) > 10:
                conflicts.append(f"Summary difference: different descriptions")
        
        return conflicts
    
    def _get_document_sources(self, entity: Entity) -> Set[str]:
        """
        Get all document sources for an entity.
        
        Args:
            entity: Entity to analyze
            
        Returns:
            Set of document IDs
        """
        return {span.doc_id for span in entity.source_spans}
    
    def _should_create_comparison_relationship(self, entity1: Entity, entity2: Entity) -> Tuple[bool, str, List[str]]:
        """
        Determine if a comparison relationship should be created between two entities.
        
        Args:
            entity1: First entity
            entity2: Second entity
            
        Returns:
            Tuple of (should_create: bool, reason: str, conflicts: List[str])
        """
        # Entities must be of the same type to compare
        if entity1.type != entity2.type:
            return False, "Different entity types", []
        
        # Get document sources
        docs1 = self._get_document_sources(entity1)
        docs2 = self._get_document_sources(entity2)
        
        # Must appear in different documents to be considered for comparison
        if not docs1 or not docs2 or docs1 == docs2:
            return False, "Same document sources", []
        
        # Check if they have overlapping documents (cross-document entity)
        if docs1 & docs2:
            return False, "Overlapping document sources", []
        
        # Look for conflicting attributes
        conflicts = self._extract_conflicting_attributes(entity1, entity2)
        
        if not conflicts:
            return False, "No conflicting attributes found", []
        
        # Check name similarity (potential for confusion/comparison)
        name_similarity = SequenceMatcher(None, entity1.name.lower(), entity2.name.lower()).ratio()
        
        # Create comparison if:
        # 1. Names are similar enough to be confusing (0.5-1.0 range) AND have conflicts
        # 2. Or if they have conflicting attributes and some name overlap
        if name_similarity >= 0.5 and len(conflicts) >= 1:
            reason = f"Similar names with conflicts (similarity: {name_similarity:.2f})"
            return True, reason, conflicts
        elif name_similarity > 0.3 and len(conflicts) >= 2:
            reason = f"Multiple conflicts with name overlap (similarity: {name_similarity:.2f})"
            return True, reason, conflicts
        
        return False, "Insufficient similarity for comparison", conflicts
    
    def detect_conflicts_in_entities(self, entities: List[Entity]) -> List[Tuple[Entity, Entity, str, List[str]]]:
        """
        Detect potential conflicts between entities.
        
        Args:
            entities: List of entities to analyze
            
        Returns:
            List of (entity1, entity2, reason, conflicts) tuples
        """
        conflicts = []
        
        # Group entities by type for efficient comparison
        entities_by_type = {}
        for entity in entities:
            if entity.type not in entities_by_type:
                entities_by_type[entity.type] = []
            entities_by_type[entity.type].append(entity)
        
        # Compare entities within each type
        for entity_type, type_entities in entities_by_type.items():
            logger.debug(f"Analyzing conflicts for {len(type_entities)} entities of type {entity_type}")
            
            for i, entity1 in enumerate(type_entities):
                for entity2 in type_entities[i+1:]:
                    should_compare, reason, conflict_list = self._should_create_comparison_relationship(entity1, entity2)
                    
                    if should_compare:
                        conflicts.append((entity1, entity2, reason, conflict_list))
                        logger.info(f"Detected conflict: '{entity1.name}' vs '{entity2.name}' - {reason}")
        
        return conflicts
    
    def create_comparison_relationships(self, conflict_pairs: List[Tuple[Entity, Entity, str, List[str]]]) -> List[Relationship]:
        """
        Create comparison relationships from detected conflicts.
        
        Args:
            conflict_pairs: List of conflict tuples from detect_conflicts_in_entities
            
        Returns:
            List of comparison relationships
        """
        relationships = []
        
        for entity1, entity2, reason, conflicts in conflict_pairs:
            # Create evidence from conflict descriptions
            evidence = []
            
            # Add evidence from source spans of both entities
            for entity, label in [(entity1, "Entity 1"), (entity2, "Entity 2")]:
                if entity.source_spans:
                    # Use the first source span as evidence
                    span = entity.source_spans[0]
                    evidence.append(Evidence(
                        doc_id=span.doc_id,
                        quote=f"{label}: {entity.name} - {entity.summary[:100]}",
                        offset=span.start
                    ))
            
            # Create bidirectional comparison relationships
            # Entity1 compares_with Entity2
            rel1 = Relationship(
                from_entity=entity1.id,
                to_entity=entity2.id,
                predicate=RelationType.COMPARES_WITH,
                confidence=0.8,  # High confidence for detected conflicts
                evidence=evidence,
                directional=False,  # Comparison is bidirectional
                created_at=datetime.utcnow()
            )
            
            # Entity2 compares_with Entity1 (bidirectional)
            rel2 = Relationship(
                from_entity=entity2.id,
                to_entity=entity1.id,
                predicate=RelationType.COMPARES_WITH,
                confidence=0.8,
                evidence=evidence,
                directional=False,
                created_at=datetime.utcnow()
            )
            
            relationships.extend([rel1, rel2])
            
            logger.info(
                f"Created comparison relationship: '{entity1.name}' <-> '{entity2.name}' "
                f"({len(conflicts)} conflicts: {', '.join(conflicts[:2])})"
            )
        
        return relationships
    
    def analyze_cross_document_patterns(self, entities: List[Entity], relationships: List[Relationship]) -> Dict[str, any]:
        """
        Analyze patterns in cross-document relationships.
        
        Args:
            entities: List of entities
            relationships: List of relationships
            
        Returns:
            Dictionary with cross-document analysis
        """
        analysis = {
            "total_entities": len(entities),
            "cross_document_entities": 0,
            "comparison_relationships": 0,
            "document_pairs": set(),
            "entity_conflicts_by_type": {},
            "most_conflicted_entities": []
        }
        
        # Analyze entities
        cross_doc_entities = []
        for entity in entities:
            docs = self._get_document_sources(entity)
            if len(docs) > 1:
                analysis["cross_document_entities"] += 1
                cross_doc_entities.append(entity)
        
        # Analyze relationships
        comparison_rels = []
        for rel in relationships:
            if rel.predicate == RelationType.COMPARES_WITH:
                comparison_rels.append(rel)
                analysis["comparison_relationships"] += 1
                
                # Track document pairs involved in comparisons
                from_entity = next((e for e in entities if e.id == rel.from_entity), None)
                to_entity = next((e for e in entities if e.id == rel.to_entity), None)
                
                if from_entity and to_entity:
                    from_docs = self._get_document_sources(from_entity)
                    to_docs = self._get_document_sources(to_entity)
                    
                    for from_doc in from_docs:
                        for to_doc in to_docs:
                            if from_doc != to_doc:
                                doc_pair = tuple(sorted([from_doc, to_doc]))
                                analysis["document_pairs"].add(doc_pair)
                    
                    # Track conflicts by entity type
                    entity_type = from_entity.type.value
                    if entity_type not in analysis["entity_conflicts_by_type"]:
                        analysis["entity_conflicts_by_type"][entity_type] = 0
                    analysis["entity_conflicts_by_type"][entity_type] += 1
        
        # Find most conflicted entities (entities with most comparison relationships)
        entity_conflict_counts = {}
        for rel in comparison_rels:
            entity_conflict_counts[rel.from_entity] = entity_conflict_counts.get(rel.from_entity, 0) + 1
            entity_conflict_counts[rel.to_entity] = entity_conflict_counts.get(rel.to_entity, 0) + 1
        
        # Sort by conflict count and get top entities
        sorted_conflicts = sorted(entity_conflict_counts.items(), key=lambda x: x[1], reverse=True)
        for entity_id, conflict_count in sorted_conflicts[:5]:  # Top 5
            entity = next((e for e in entities if e.id == entity_id), None)
            if entity:
                analysis["most_conflicted_entities"].append({
                    "entity_id": entity_id,
                    "entity_name": entity.name,
                    "entity_type": entity.type.value,
                    "conflict_count": conflict_count
                })
        
        # Convert set to list for JSON serialization
        analysis["document_pairs"] = list(analysis["document_pairs"])
        analysis["total_document_pairs"] = len(analysis["document_pairs"])
        
        return analysis


# Convenience functions
def detect_and_create_comparisons(entities: List[Entity], similarity_threshold: float = 0.7) -> Tuple[List[Relationship], Dict[str, any]]:
    """
    Convenience function to detect conflicts and create comparison relationships.
    
    Args:
        entities: List of entities to analyze
        similarity_threshold: Minimum similarity threshold for conflict detection
        
    Returns:
        Tuple of (comparison_relationships, analysis_report)
    """
    detector = ConflictDetector(similarity_threshold)
    
    # Detect conflicts
    conflicts = detector.detect_conflicts_in_entities(entities)
    
    # Create comparison relationships
    relationships = detector.create_comparison_relationships(conflicts)
    
    # Analyze patterns
    analysis = detector.analyze_cross_document_patterns(entities, relationships)
    
    return relationships, analysis