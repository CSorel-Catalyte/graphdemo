"""
Unit tests for text chunking utilities.

Tests various text formats and edge cases to ensure proper chunking behavior
with paragraph boundary preservation and token limit compliance.
"""

import pytest
from services.text_chunking import TextChunker, chunk_text


class TestTextChunker:
    """Test cases for the TextChunker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.chunker = TextChunker(max_tokens=100)  # Small limit for testing
    
    def test_count_tokens(self):
        """Test token counting functionality."""
        # Test empty string
        assert self.chunker.count_tokens("") == 0
        
        # Test simple text
        text = "Hello world"
        tokens = self.chunker.count_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)
        
        # Test longer text has more tokens
        longer_text = "Hello world, this is a longer piece of text"
        longer_tokens = self.chunker.count_tokens(longer_text)
        assert longer_tokens > tokens
    
    def test_split_into_paragraphs(self):
        """Test paragraph splitting functionality."""
        # Test single paragraph
        single_para = "This is a single paragraph."
        result = self.chunker.split_into_paragraphs(single_para)
        assert len(result) == 1
        assert result[0] == single_para
        
        # Test multiple paragraphs
        multi_para = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = self.chunker.split_into_paragraphs(multi_para)
        assert len(result) == 3
        assert result[0] == "First paragraph."
        assert result[1] == "Second paragraph."
        assert result[2] == "Third paragraph."
        
        # Test paragraphs with extra whitespace
        messy_para = "  First paragraph.  \n\n  \n  Second paragraph.  \n\n  "
        result = self.chunker.split_into_paragraphs(messy_para)
        assert len(result) == 2
        assert result[0] == "First paragraph."
        assert result[1] == "Second paragraph."
        
        # Test empty input
        assert self.chunker.split_into_paragraphs("") == []
        assert self.chunker.split_into_paragraphs("   ") == []
    
    def test_chunk_text_empty_input(self):
        """Test chunking with empty or whitespace-only input."""
        assert self.chunker.chunk_text("") == []
        assert self.chunker.chunk_text("   ") == []
        assert self.chunker.chunk_text("\n\n\n") == []
    
    def test_chunk_text_single_small_paragraph(self):
        """Test chunking with a single paragraph that fits in one chunk."""
        text = "This is a short paragraph that should fit in one chunk."
        result = self.chunker.chunk_text(text)
        assert len(result) == 1
        assert result[0] == text
        assert self.chunker.count_tokens(result[0]) <= self.chunker.max_tokens
    
    def test_chunk_text_multiple_small_paragraphs(self):
        """Test chunking with multiple small paragraphs that fit together."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = self.chunker.chunk_text(text)
        
        # Should combine into fewer chunks than paragraphs
        assert len(result) >= 1
        
        # Each chunk should be within token limit
        for chunk in result:
            assert self.chunker.count_tokens(chunk) <= self.chunker.max_tokens
        
        # Should preserve paragraph structure
        combined = "\n\n".join(result)
        # The content should be preserved (though formatting might differ slightly)
        assert "First paragraph." in combined
        assert "Second paragraph." in combined
        assert "Third paragraph." in combined
    
    def test_chunk_text_large_paragraph(self):
        """Test chunking with a paragraph that exceeds token limits."""
        # Create a large paragraph
        large_para = " ".join(["This is a sentence in a very long paragraph."] * 20)
        
        result = self.chunker.chunk_text(large_para)
        
        # Should split into multiple chunks
        assert len(result) > 1
        
        # Each chunk should be within token limit
        for chunk in result:
            assert self.chunker.count_tokens(chunk) <= self.chunker.max_tokens
        
        # Content should be preserved
        combined = " ".join(result)
        assert "This is a sentence in a very long paragraph." in combined
    
    def test_chunk_text_mixed_sizes(self):
        """Test chunking with mix of small and large paragraphs."""
        small_para = "Short paragraph."
        large_para = " ".join(["Long sentence in a big paragraph."] * 15)
        text = f"{small_para}\n\n{large_para}\n\n{small_para}"
        
        result = self.chunker.chunk_text(text)
        
        # Should produce multiple chunks
        assert len(result) >= 2
        
        # Each chunk should be within token limit
        for chunk in result:
            assert self.chunker.count_tokens(chunk) <= self.chunker.max_tokens
        
        # Content should be preserved
        combined = " ".join(result)
        assert "Short paragraph." in combined
        assert "Long sentence in a big paragraph." in combined
    
    def test_chunk_text_preserves_content(self):
        """Test that chunking preserves all original content."""
        text = """First paragraph with some content.

Second paragraph with different content.

Third paragraph with more content here.

Fourth paragraph to test preservation."""
        
        result = self.chunker.chunk_text(text)
        
        # Combine all chunks
        combined = " ".join(result)
        
        # Check that key phrases are preserved
        assert "First paragraph with some content." in combined
        assert "Second paragraph with different content." in combined
        assert "Third paragraph with more content here." in combined
        assert "Fourth paragraph to test preservation." in combined
    
    def test_chunk_text_token_limits(self):
        """Test that all chunks respect token limits."""
        # Create text with various paragraph sizes
        paragraphs = [
            "Short.",
            "Medium length paragraph with several words.",
            " ".join(["Very long paragraph with many repeated sentences."] * 10),
            "Another short one.",
            " ".join(["Another very long paragraph with lots of content."] * 12)
        ]
        text = "\n\n".join(paragraphs)
        
        result = self.chunker.chunk_text(text)
        
        # Every chunk must be within token limit
        for i, chunk in enumerate(result):
            tokens = self.chunker.count_tokens(chunk)
            assert tokens <= self.chunker.max_tokens, f"Chunk {i} has {tokens} tokens, exceeds limit of {self.chunker.max_tokens}"
    
    def test_different_max_tokens(self):
        """Test chunking with different token limits."""
        text = "This is a test paragraph. " * 50  # Repeat to make it long
        
        # Test with small limit
        small_chunker = TextChunker(max_tokens=50)
        small_result = small_chunker.chunk_text(text)
        
        # Test with large limit
        large_chunker = TextChunker(max_tokens=500)
        large_result = large_chunker.chunk_text(text)
        
        # Small limit should produce more chunks
        assert len(small_result) > len(large_result)
        
        # All chunks should respect their limits
        for chunk in small_result:
            assert small_chunker.count_tokens(chunk) <= 50
        
        for chunk in large_result:
            assert large_chunker.count_tokens(chunk) <= 500


class TestConvenienceFunction:
    """Test cases for the convenience function."""
    
    def test_chunk_text_function(self):
        """Test the convenience chunk_text function."""
        text = "First paragraph.\n\nSecond paragraph."
        result = chunk_text(text, max_tokens=100)
        
        assert isinstance(result, list)
        assert len(result) >= 1
        
        # Test with custom parameters
        result_custom = chunk_text(text, max_tokens=50, model_name="gpt-3.5-turbo")
        assert isinstance(result_custom, list)


class TestEdgeCases:
    """Test edge cases and special text formats."""
    
    def test_single_very_long_word(self):
        """Test handling of extremely long words that exceed token limits."""
        chunker = TextChunker(max_tokens=10)
        
        # Create a very long "word" (like a URL or hash)
        long_word = "verylongwordthatexceedstokenlimitsbutmustbehandled"
        result = chunker.chunk_text(long_word)
        
        # Should still return the word, even if it exceeds limits
        assert len(result) == 1
        assert long_word in result[0]
    
    def test_special_characters(self):
        """Test handling of text with special characters."""
        chunker = TextChunker(max_tokens=100)
        
        text = """Paragraph with special chars: @#$%^&*()!

Second paragraph with unicode: café, naïve, résumé.

Third paragraph with numbers: 123, 456.789, $1,000."""
        
        result = chunker.chunk_text(text)
        
        # Should handle special characters without errors
        assert len(result) >= 1
        combined = " ".join(result)
        assert "@#$%^&*()" in combined
        assert "café" in combined
        assert "$1,000" in combined
    
    def test_code_like_text(self):
        """Test handling of code-like text with different formatting."""
        chunker = TextChunker(max_tokens=200)
        
        text = """def example_function():
    return "Hello World"

class ExampleClass:
    def __init__(self):
        self.value = 42
        
    def method(self):
        return self.value * 2"""
        
        result = chunker.chunk_text(text)
        
        # Should handle code formatting
        assert len(result) >= 1
        combined = " ".join(result)
        assert "def example_function" in combined
        assert "class ExampleClass" in combined
    
    def test_markdown_like_text(self):
        """Test handling of markdown-formatted text."""
        chunker = TextChunker(max_tokens=150)
        
        text = """# Main Title

This is a paragraph under the main title.

## Subsection

- List item 1
- List item 2
- List item 3

Another paragraph with **bold** and *italic* text."""
        
        result = chunker.chunk_text(text)
        
        # Should handle markdown formatting
        assert len(result) >= 1
        combined = " ".join(result)
        assert "# Main Title" in combined
        assert "**bold**" in combined
        assert "- List item" in combined


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])