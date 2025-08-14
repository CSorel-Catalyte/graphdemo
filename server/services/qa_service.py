"""
Question Answering Service for the AI Knowledge Mapper.

This service handles the complete question-answering pipeline:
1. Question embedding generation
2. Top-k relevant node retrieval via vector similarity
3. Neighborhood expansion using graph traversal
4. Context building from node summaries and evidence
5. Grounded answer generation with citations
"""

import logging
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from models.core import Entity, Relationship, Evidence
from models.api import Citation
from services.ie_service import InformationExtractionService
from storage.qdrant_adapter import QdrantAdapter
from storage.oxigraph_adapter import OxigraphAdapter

logger = logging.getLogger(__name__)


@dataclass
class QAResult:
    """Result of question answering process"""
    answer: str
    citations: List[Citation]
    confidence: float
    relevant_nodes: List[Entity]
    context_used: str


class QuestionAnsweringService:
    """Service for answering questions using the knowledge graph"""
    
    def __init__(
        self,
        ie_service: InformationExtractionService,
        qdrant_adapter: QdrantAdapter,
        oxigraph_adapter: OxigraphAdapter,
        top_k_nodes: int = 12,
        max_context_length: int = 8000
    ):
        """
        Initialize the Question Answering Service
        
        Args:
            ie_service: Information extraction service for embeddings and LLM calls
            qdrant_adapter: Vector database adapter for similarity search
            oxigraph_adapter: Graph database adapter for neighborhood expansion
            top_k_nodes: Number of top relevant nodes to retrieve
            max_context_length: Maximum context length for answer generation
        """
        self.ie_service = ie_service
        self.qdrant_adapter = qdrant_adapter
        self.oxigraph_adapter = oxigraph_adapter
        self.top_k_nodes = top_k_nodes
        self.max_context_length = max_context_length
    
    async def generate_question_embedding(self, question: str) -> List[float]:
        """
        Generate embedding for the question using OpenAI API
        
        Args:
            question: Natural language question
            
        Returns:
            Question embedding vector
        """
        try:
            if not self.ie_service.client:
                raise Exception("OpenAI client not available")
            
            # Use OpenAI's text-embedding-3-large model for consistency with entity embeddings
            response = await self.ie_service.client.embeddings.create(
                model="text-embedding-3-large",
                input=question,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding for question: '{question[:50]}...'")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating question embedding: {e}")
            raise
    
    async def retrieve_relevant_nodes(
        self, 
        question_embedding: List[float]
    ) -> List[Tuple[Entity, float]]:
        """
        Retrieve top-k most relevant nodes using vector similarity
        
        Args:
            question_embedding: Question embedding vector
            
        Returns:
            List of (Entity, similarity_score) tuples
        """
        try:
            # Search for similar entities
            similar_entities = await self.qdrant_adapter.search_entities_by_text(
                query_embedding=question_embedding,
                limit=self.top_k_nodes
            )
            
            logger.info(f"Retrieved {len(similar_entities)} relevant nodes")
            return similar_entities
            
        except Exception as e:
            logger.error(f"Error retrieving relevant nodes: {e}")
            return []
    
    async def expand_node_neighborhoods(
        self, 
        relevant_nodes: List[Entity]
    ) -> Tuple[List[Entity], List[Relationship]]:
        """
        Expand the neighborhood of relevant nodes to gather more context
        
        Args:
            relevant_nodes: List of relevant entities
            
        Returns:
            Tuple of (expanded_entities, relationships)
        """
        try:
            expanded_entities = list(relevant_nodes)  # Start with original nodes
            all_relationships = []
            
            # Get 1-hop neighbors for each relevant node
            for entity in relevant_nodes:
                try:
                    neighbor_info = await self.oxigraph_adapter.get_neighbors(
                        entity_id=entity.id,
                        hops=1,
                        limit=50  # Limit neighbors per node to control context size
                    )
                    
                    # Get full entity data for neighbors
                    neighbor_ids = [info["entity_id"] for info in neighbor_info]
                    neighbor_entities = await self.qdrant_adapter.get_entities_by_ids(neighbor_ids)
                    
                    # Add neighbors to expanded entities (avoid duplicates)
                    existing_ids = {e.id for e in expanded_entities}
                    for neighbor in neighbor_entities:
                        if neighbor.id not in existing_ids:
                            expanded_entities.append(neighbor)
                            existing_ids.add(neighbor.id)
                    
                    # Get relationships for this entity
                    relationships = await self.oxigraph_adapter.get_entity_relationships(entity.id)
                    
                    # Convert to Relationship objects
                    for rel_info in relationships:
                        try:
                            from models.core import RelationType
                            relationship = Relationship(
                                from_entity=rel_info["from_entity"],
                                to_entity=rel_info["to_entity"],
                                predicate=RelationType(rel_info["predicate"]),
                                confidence=rel_info["confidence"],
                                evidence=[Evidence(
                                    doc_id=ev["doc_id"],
                                    quote=ev["quote"],
                                    offset=0
                                ) for ev in rel_info.get("evidence", [])],
                                directional=rel_info["directional"]
                            )
                            all_relationships.append(relationship)
                        except Exception as e:
                            logger.warning(f"Error converting relationship: {e}")
                            continue
                            
                except Exception as e:
                    logger.warning(f"Error expanding neighborhood for entity {entity.id}: {e}")
                    continue
            
            logger.info(f"Expanded to {len(expanded_entities)} entities and {len(all_relationships)} relationships")
            return expanded_entities, all_relationships
            
        except Exception as e:
            logger.error(f"Error expanding node neighborhoods: {e}")
            return relevant_nodes, []
    
    def build_context(
        self, 
        entities: List[Entity], 
        relationships: List[Relationship],
        question: str
    ) -> str:
        """
        Build context string from entities and relationships for answer generation
        
        Args:
            entities: List of relevant entities
            relationships: List of relevant relationships
            question: Original question for context relevance
            
        Returns:
            Context string for LLM
        """
        try:
            context_parts = []
            
            # Add question for reference
            context_parts.append(f"Question: {question}\n")
            
            # Add entity information
            context_parts.append("Relevant Entities:")
            for entity in entities[:20]:  # Limit to top 20 entities to control context size
                entity_info = f"- {entity.name} ({entity.type.value})"
                if entity.summary:
                    entity_info += f": {entity.summary}"
                
                # Add evidence quotes if available
                if entity.source_spans:
                    # Get evidence from first source span (simplified)
                    entity_info += f" [Source: {entity.source_spans[0].doc_id}]"
                
                context_parts.append(entity_info)
            
            context_parts.append("\nRelevant Relationships:")
            
            # Add relationship information
            entity_name_map = {e.id: e.name for e in entities}
            for relationship in relationships[:30]:  # Limit relationships
                from_name = entity_name_map.get(relationship.from_entity, relationship.from_entity)
                to_name = entity_name_map.get(relationship.to_entity, relationship.to_entity)
                
                rel_info = f"- {from_name} {relationship.predicate.value} {to_name}"
                if relationship.confidence:
                    rel_info += f" (confidence: {relationship.confidence:.2f})"
                
                # Add evidence quotes
                if relationship.evidence:
                    evidence_quotes = [f'"{ev.quote}"' for ev in relationship.evidence[:2]]  # Max 2 quotes
                    rel_info += f" Evidence: {', '.join(evidence_quotes)}"
                
                context_parts.append(rel_info)
            
            # Join all parts and truncate if too long
            context = "\n".join(context_parts)
            
            if len(context) > self.max_context_length:
                context = context[:self.max_context_length] + "...[truncated]"
            
            logger.debug(f"Built context with {len(context)} characters")
            return context
            
        except Exception as e:
            logger.error(f"Error building context: {e}")
            return f"Question: {question}\n\nError building context from knowledge graph."
    
    async def generate_grounded_answer(
        self, 
        question: str, 
        context: str,
        relevant_entities: List[Entity]
    ) -> Tuple[str, List[Citation], float]:
        """
        Generate a grounded answer with citations using LLM
        
        Args:
            question: Original question
            context: Built context from knowledge graph
            relevant_entities: List of relevant entities for citation
            
        Returns:
            Tuple of (answer, citations, confidence_score)
        """
        try:
            if not self.ie_service.client:
                raise Exception("OpenAI client not available")
            
            # Create system prompt for grounded answer generation
            system_prompt = """You are an expert knowledge assistant. Answer the user's question based ONLY on the provided knowledge graph context. 

IMPORTANT RULES:
1. Base your answer ONLY on the information provided in the context
2. If the context doesn't contain enough information to answer the question, say so clearly
3. Include specific citations by referencing entity names from the context
4. Be precise and factual - do not make assumptions beyond what's stated
5. If there are conflicting pieces of information, mention both and cite sources
6. Keep your answer concise but comprehensive
7. Use quotes from the evidence when available

Format your response as a clear, well-structured answer that directly addresses the question."""
            
            user_prompt = f"""Context from Knowledge Graph:
{context}

Question: {question}

Please provide a grounded answer based on the context above. Include specific references to entities and evidence from the knowledge graph."""
            
            # Generate answer using OpenAI
            response = await self.ie_service.client.chat.completions.create(
                model=self.ie_service.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for factual responses
                max_tokens=1000,  # Reasonable limit for answers
                timeout=30.0
            )
            
            answer = response.choices[0].message.content
            if not answer:
                answer = "I couldn't generate an answer based on the available information."
            
            # Extract citations from the answer and relevant entities
            citations = self._extract_citations(answer, relevant_entities)
            
            # Calculate confidence based on context relevance and answer quality
            confidence = self._calculate_confidence(answer, context, len(citations))
            
            logger.info(f"Generated answer with {len(citations)} citations (confidence: {confidence:.2f})")
            return answer, citations, confidence
            
        except Exception as e:
            logger.error(f"Error generating grounded answer: {e}")
            return (
                "I encountered an error while generating an answer. Please try again.",
                [],
                0.0
            )
    
    def _extract_citations(self, answer: str, relevant_entities: List[Entity]) -> List[Citation]:
        """
        Extract citations from the generated answer
        
        Args:
            answer: Generated answer text
            relevant_entities: List of relevant entities
            
        Returns:
            List of citations
        """
        citations = []
        
        try:
            # Simple citation extraction based on entity name mentions
            for entity in relevant_entities[:10]:  # Limit citations
                if entity.name.lower() in answer.lower():
                    # Find evidence quote from entity
                    quote = entity.summary if entity.summary else f"Entity: {entity.name}"
                    
                    # Get document ID from source spans
                    doc_id = "unknown"
                    if entity.source_spans:
                        doc_id = entity.source_spans[0].doc_id
                    
                    # Calculate relevance based on entity salience and mention frequency
                    mention_count = answer.lower().count(entity.name.lower())
                    relevance_score = min(1.0, entity.salience + (mention_count * 0.1))
                    
                    citation = Citation(
                        node_id=entity.id,
                        quote=quote[:200],  # Truncate to max length
                        doc_id=doc_id,
                        relevance_score=relevance_score
                    )
                    citations.append(citation)
            
            # Sort citations by relevance score
            citations.sort(key=lambda c: c.relevance_score, reverse=True)
            
            return citations[:8]  # Return top 8 citations
            
        except Exception as e:
            logger.error(f"Error extracting citations: {e}")
            return []
    
    def _calculate_confidence(self, answer: str, context: str, citation_count: int) -> float:
        """
        Calculate confidence score for the generated answer
        
        Args:
            answer: Generated answer
            context: Context used for generation
            citation_count: Number of citations found
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
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
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5
    
    async def answer_question(self, question: str) -> QAResult:
        """
        Complete question answering pipeline
        
        Args:
            question: Natural language question
            
        Returns:
            QAResult with answer, citations, and metadata
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting QA pipeline for question: '{question[:100]}...'")
            
            # Step 1: Generate question embedding
            question_embedding = await self.generate_question_embedding(question)
            
            # Step 2: Retrieve top-k relevant nodes
            relevant_nodes_with_scores = await self.retrieve_relevant_nodes(question_embedding)
            relevant_nodes = [entity for entity, score in relevant_nodes_with_scores]
            
            if not relevant_nodes:
                return QAResult(
                    answer="I couldn't find any relevant information in the knowledge graph to answer your question.",
                    citations=[],
                    confidence=0.0,
                    relevant_nodes=[],
                    context_used=""
                )
            
            # Step 3: Expand neighborhoods for additional context
            expanded_entities, relationships = await self.expand_node_neighborhoods(relevant_nodes)
            
            # Step 4: Build context from entities and relationships
            context = self.build_context(expanded_entities, relationships, question)
            
            # Step 5: Generate grounded answer with citations
            answer, citations, confidence = await self.generate_grounded_answer(
                question, context, relevant_nodes
            )
            
            processing_time = time.time() - start_time
            logger.info(f"QA pipeline completed in {processing_time:.2f}s")
            
            return QAResult(
                answer=answer,
                citations=citations,
                confidence=confidence,
                relevant_nodes=relevant_nodes,
                context_used=context
            )
            
        except Exception as e:
            logger.error(f"Error in QA pipeline: {e}")
            return QAResult(
                answer="I encountered an error while processing your question. Please try again.",
                citations=[],
                confidence=0.0,
                relevant_nodes=[],
                context_used=""
            )