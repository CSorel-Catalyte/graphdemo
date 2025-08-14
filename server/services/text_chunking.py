"""
Text chunking utilities for processing documents into manageable segments.

This module provides functionality to split text into chunks while preserving
paragraph boundaries and ensuring token limits are respected.
"""

import re
from typing import List, Optional

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


class TextChunker:
    """Handles text chunking with paragraph boundary preservation and token counting."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", max_tokens: int = 1800):
        """
        Initialize the text chunker.
        
        Args:
            model_name: The model name for token encoding (default: gpt-3.5-turbo)
            max_tokens: Maximum tokens per chunk (default: 1800)
        """
        self.max_tokens = max_tokens
        self.model_name = model_name
        
        if TIKTOKEN_AVAILABLE:
            try:
                self.encoding = tiktoken.encoding_for_model(model_name)
                self.use_tiktoken = True
            except KeyError:
                # Fallback to cl100k_base encoding if model not found
                self.encoding = tiktoken.get_encoding("cl100k_base")
                self.use_tiktoken = True
        else:
            self.use_tiktoken = False
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Uses tiktoken if available, otherwise falls back to a simple approximation
        based on word count (roughly 1.3 tokens per word for English text).
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens in the text
        """
        if self.use_tiktoken:
            return len(self.encoding.encode(text))
        else:
            # Simple approximation: ~1.3 tokens per word for English text
            # This is a rough estimate but should work for basic chunking
            words = len(text.split())
            return int(words * 1.3)
    
    def split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs, preserving paragraph boundaries.
        
        Args:
            text: The input text to split
            
        Returns:
            List of paragraph strings
        """
        # Split on double newlines (paragraph breaks) and clean up
        paragraphs = re.split(r'\n\s*\n', text.strip())
        
        # Clean up each paragraph - remove extra whitespace but preserve single newlines
        cleaned_paragraphs = []
        for para in paragraphs:
            cleaned = re.sub(r'\s+', ' ', para.strip())
            if cleaned:  # Only add non-empty paragraphs
                cleaned_paragraphs.append(cleaned)
        
        return cleaned_paragraphs
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk text into segments that respect paragraph boundaries and token limits.
        
        This function splits text into chunks of at most max_tokens tokens while
        trying to preserve paragraph boundaries. If a single paragraph exceeds
        the token limit, it will be split at sentence boundaries.
        
        Args:
            text: The input text to chunk
            
        Returns:
            List of text chunks, each containing ≤ max_tokens tokens
        """
        if not text or not text.strip():
            return []
        
        paragraphs = self.split_into_paragraphs(text)
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for paragraph in paragraphs:
            paragraph_tokens = self.count_tokens(paragraph)
            
            # If paragraph alone exceeds limit, split it further
            if paragraph_tokens > self.max_tokens:
                # First, add current chunk if it has content
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                    current_tokens = 0
                
                # Split the large paragraph into smaller pieces
                sub_chunks = self._split_large_paragraph(paragraph)
                chunks.extend(sub_chunks)
                continue
            
            # Check if adding this paragraph would exceed the limit
            potential_tokens = current_tokens + paragraph_tokens
            if current_chunk:  # Account for separator if chunk already has content
                potential_tokens += self.count_tokens("\n\n")
            
            if potential_tokens <= self.max_tokens:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                    current_tokens += self.count_tokens("\n\n") + paragraph_tokens
                else:
                    current_chunk = paragraph
                    current_tokens = paragraph_tokens
            else:
                # Current chunk is full, start a new one
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
                current_tokens = paragraph_tokens
        
        # Add the final chunk if it has content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_large_paragraph(self, paragraph: str) -> List[str]:
        """
        Split a large paragraph that exceeds token limits into smaller chunks.
        
        This method attempts to split at sentence boundaries first, then at
        word boundaries if necessary.
        
        Args:
            paragraph: The paragraph to split
            
        Returns:
            List of smaller text chunks
        """
        # Try splitting by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            # If a single sentence exceeds the limit, split it by words
            if sentence_tokens > self.max_tokens:
                # Add current chunk if it has content
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                    current_tokens = 0
                
                # Split sentence by words
                word_chunks = self._split_by_words(sentence)
                chunks.extend(word_chunks)
                continue
            
            # Check if adding this sentence would exceed the limit
            potential_tokens = current_tokens + sentence_tokens
            if current_chunk:  # Account for space separator
                potential_tokens += 1
            
            if potential_tokens <= self.max_tokens:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                    current_tokens += 1 + sentence_tokens
                else:
                    current_chunk = sentence
                    current_tokens = sentence_tokens
            else:
                # Current chunk is full, start a new one
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
                current_tokens = sentence_tokens
        
        # Add the final chunk if it has content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_by_words(self, text: str) -> List[str]:
        """
        Split text by words when sentence-level splitting isn't sufficient.
        
        Args:
            text: The text to split by words
            
        Returns:
            List of word-based chunks
        """
        words = text.split()
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for word in words:
            word_tokens = self.count_tokens(word)
            
            # If a single word exceeds the limit, we have to include it anyway
            if word_tokens > self.max_tokens:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                chunks.append(word)
                current_chunk = ""
                current_tokens = 0
                continue
            
            # Check if adding this word would exceed the limit
            potential_tokens = current_tokens + word_tokens
            if current_chunk:  # Account for space separator
                potential_tokens += 1
            
            if potential_tokens <= self.max_tokens:
                # Add word to current chunk
                if current_chunk:
                    current_chunk += " " + word
                    current_tokens += 1 + word_tokens
                else:
                    current_chunk = word
                    current_tokens = word_tokens
            else:
                # Current chunk is full, start a new one
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = word
                current_tokens = word_tokens
        
        # Add the final chunk if it has content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks


def chunk_text(text: str, max_tokens: int = 1800, model_name: str = "gpt-3.5-turbo") -> List[str]:
    """
    Convenience function to chunk text with default parameters.
    
    Args:
        text: The input text to chunk
        max_tokens: Maximum tokens per chunk (default: 1800)
        model_name: The model name for token encoding (default: gpt-3.5-turbo)
        
    Returns:
        List of text chunks, each containing ≤ max_tokens tokens
    """
    chunker = TextChunker(model_name=model_name, max_tokens=max_tokens)
    return chunker.chunk_text(text)