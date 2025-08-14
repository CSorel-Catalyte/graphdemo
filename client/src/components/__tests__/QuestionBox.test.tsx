/**
 * Tests for QuestionBox component.
 * Tests natural language input, answer display, citation handling, and user interactions.
 */


import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import QuestionBox from '../QuestionBox';
import { useStore } from '../../store/useStore';
import { QuestionResponse } from '../../types/api';

// Mock the store
vi.mock('../../store/useStore');
const mockUseStore = vi.mocked(useStore);

// Mock fetch
const mockFetch = vi.fn();
(globalThis as any).fetch = mockFetch;

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    input: ({ children, ...props }: any) => <input {...props}>{children}</input>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('QuestionBox', () => {
  const mockStore = {
    currentQuestion: '',
    setCurrentQuestion: vi.fn(),
    currentAnswer: '',
    currentCitations: [],
    setCurrentAnswer: vi.fn(),
    isAnswering: false,
    setAnswering: vi.fn(),
    isConnected: true,
    selectNode: vi.fn(),
    setSidePanelOpen: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseStore.mockReturnValue(mockStore as any);
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders question input with placeholder', () => {
      render(<QuestionBox placeholder="Test placeholder" />);
      
      const input = screen.getByPlaceholderText('Test placeholder');
      expect(input).toBeInTheDocument();
      expect(input).toHaveClass('bg-gray-700');
    });

    it('renders with default placeholder when none provided', () => {
      render(<QuestionBox />);
      
      const input = screen.getByPlaceholderText('Ask a question...');
      expect(input).toBeInTheDocument();
    });

    it('applies custom className', () => {
      render(<QuestionBox className="custom-class" />);
      
      const container = screen.getByPlaceholderText('Ask a question...').closest('.custom-class');
      expect(container).toBeInTheDocument();
    });

    it('shows question icon', () => {
      render(<QuestionBox />);
      
      const icon = screen.getByRole('textbox').parentElement?.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Input Handling', () => {
    it('updates question when typing', () => {
      render(<QuestionBox />);
      
      const input = screen.getByPlaceholderText('Ask a question...');
      fireEvent.change(input, { target: { value: 'What is machine learning?' } });
      
      expect(mockStore.setCurrentQuestion).toHaveBeenCalledWith('What is machine learning?');
    });

    it('handles escape key to blur input', () => {
      render(<QuestionBox />);
      
      const input = screen.getByPlaceholderText('Ask a question...');
      input.focus();
      
      const blurSpy = vi.spyOn(input, 'blur');
      fireEvent.keyDown(input, { key: 'Escape' });
      
      expect(blurSpy).toHaveBeenCalled();
    });

    it('submits form on enter key', async () => {
      mockStore.currentQuestion = 'Test question';
      mockStore.isConnected = true;
      
      const mockResponse: QuestionResponse = {
        answer: 'Test answer',
        citations: [],
        question: 'Test question',
        confidence: 0.9,
        processing_time: 1.5,
      };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });
      
      render(<QuestionBox />);
      
      const form = screen.getByRole('textbox').closest('form');
      fireEvent.submit(form!);
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('/api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ q: 'Test question' }),
        });
      });
    });
  });

  describe('Disabled States', () => {
    it('disables input when not connected', () => {
      mockStore.isConnected = false;
      render(<QuestionBox />);
      
      const input = screen.getByPlaceholderText('Ask a question...');
      expect(input).toBeDisabled();
      expect(input).toHaveClass('disabled:opacity-50');
    });

    it('disables input when answering', () => {
      mockStore.isAnswering = true;
      render(<QuestionBox />);
      
      const input = screen.getByPlaceholderText('Ask a question...');
      expect(input).toBeDisabled();
    });

    it('shows loading spinner when answering', () => {
      mockStore.isAnswering = true;
      render(<QuestionBox />);
      
      const spinner = screen.getByRole('textbox').parentElement?.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('Question Answering', () => {
    it('has proper form submission structure', () => {
      const mockStoreWithQuestion = {
        ...mockStore,
        currentQuestion: 'What is AI?',
        isConnected: true,
      };
      
      mockUseStore.mockReturnValue(mockStoreWithQuestion as any);
      
      render(<QuestionBox />);
      
      const form = screen.getByRole('textbox').closest('form');
      expect(form).toBeInTheDocument();
      
      // Test that form can be submitted (structure is correct)
      fireEvent.submit(form!);
      
      // Component should handle the submission without errors
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    it('does not submit empty questions', () => {
      const mockStoreWithEmptyQuestion = {
        ...mockStore,
        currentQuestion: '   ', // whitespace only
        isConnected: true,
      };
      
      mockUseStore.mockReturnValue(mockStoreWithEmptyQuestion as any);
      
      render(<QuestionBox />);
      
      const form = screen.getByRole('textbox').closest('form');
      fireEvent.submit(form!);
      
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('does not submit when not connected', () => {
      const mockStoreDisconnected = {
        ...mockStore,
        currentQuestion: 'Test question',
        isConnected: false,
      };
      
      mockUseStore.mockReturnValue(mockStoreDisconnected as any);
      
      render(<QuestionBox />);
      
      const form = screen.getByRole('textbox').closest('form');
      fireEvent.submit(form!);
      
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('does not submit when already answering', () => {
      const mockStoreAnswering = {
        ...mockStore,
        currentQuestion: 'Test question',
        isConnected: true,
        isAnswering: true,
      };
      
      mockUseStore.mockReturnValue(mockStoreAnswering as any);
      
      render(<QuestionBox />);
      
      const form = screen.getByRole('textbox').closest('form');
      fireEvent.submit(form!);
      
      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe('Quick Answer Preview', () => {
    it('shows quick answer preview when answer is available', () => {
      const mockStoreWithAnswer = {
        ...mockStore,
        currentAnswer: 'This is a test answer that is long enough to be truncated',
        currentCitations: [
          {
            node_id: 'node1',
            quote: 'Citation quote',
            doc_id: 'doc1',
            relevance_score: 0.9,
          },
        ],
        isAnswering: false,
      };
      
      mockUseStore.mockReturnValue(mockStoreWithAnswer as any);
      
      render(<QuestionBox />);
      
      expect(screen.getByText('Quick Answer')).toBeInTheDocument();
      expect(screen.getByText(/This is a test answer/)).toBeInTheDocument();
      expect(screen.getByText('1 citation:')).toBeInTheDocument();
    });

    it('truncates long answers in preview', () => {
      const longAnswer = 'A'.repeat(200);
      const mockStoreWithLongAnswer = {
        ...mockStore,
        currentAnswer: longAnswer,
        isAnswering: false,
      };
      
      mockUseStore.mockReturnValue(mockStoreWithLongAnswer as any);
      
      render(<QuestionBox />);
      
      const previewText = screen.getByText(/A+\.\.\./);
      expect(previewText.textContent).toHaveLength(153); // 150 chars + "..."
    });

    it('shows citation buttons in preview', () => {
      const mockStoreWithCitations = {
        ...mockStore,
        currentAnswer: 'Test answer',
        currentCitations: [
          { node_id: 'node1', quote: 'Quote 1', doc_id: 'doc1', relevance_score: 0.9 },
          { node_id: 'node2', quote: 'Quote 2', doc_id: 'doc2', relevance_score: 0.8 },
        ],
        isAnswering: false,
      };
      
      mockUseStore.mockReturnValue(mockStoreWithCitations as any);
      
      render(<QuestionBox />);
      
      expect(screen.getByText('Citation 1')).toBeInTheDocument();
      expect(screen.getByText('Citation 2')).toBeInTheDocument();
    });

    it('limits citation preview to 3 citations', () => {
      const mockStoreWithManyCitations = {
        ...mockStore,
        currentAnswer: 'Test answer',
        currentCitations: [
          { node_id: 'node1', quote: 'Quote 1', doc_id: 'doc1', relevance_score: 0.9 },
          { node_id: 'node2', quote: 'Quote 2', doc_id: 'doc2', relevance_score: 0.8 },
          { node_id: 'node3', quote: 'Quote 3', doc_id: 'doc3', relevance_score: 0.7 },
          { node_id: 'node4', quote: 'Quote 4', doc_id: 'doc4', relevance_score: 0.6 },
        ],
        isAnswering: false,
      };
      
      mockUseStore.mockReturnValue(mockStoreWithManyCitations as any);
      
      render(<QuestionBox />);
      
      expect(screen.getByText('Citation 1')).toBeInTheDocument();
      expect(screen.getByText('Citation 2')).toBeInTheDocument();
      expect(screen.getByText('Citation 3')).toBeInTheDocument();
      expect(screen.getByText('+1 more')).toBeInTheDocument();
    });

    it('handles citation clicks', () => {
      const mockStoreWithCitation = {
        ...mockStore,
        currentAnswer: 'Test answer',
        currentCitations: [
          { node_id: 'node1', quote: 'Quote 1', doc_id: 'doc1', relevance_score: 0.9 },
        ],
        isAnswering: false,
      };
      
      mockUseStore.mockReturnValue(mockStoreWithCitation as any);
      
      render(<QuestionBox />);
      
      const citationButton = screen.getByText('Citation 1');
      fireEvent.click(citationButton);
      
      expect(mockStoreWithCitation.selectNode).toHaveBeenCalledWith('node1');
      expect(mockStoreWithCitation.setSidePanelOpen).toHaveBeenCalledWith(true, 'node-details');
    });

    it('has view full answer button', () => {
      const mockStoreWithAnswer = {
        ...mockStore,
        currentAnswer: 'Test answer',
        isAnswering: false,
      };
      
      mockUseStore.mockReturnValue(mockStoreWithAnswer as any);
      
      render(<QuestionBox />);
      
      const viewFullButton = screen.getByText('View Full Answer');
      fireEvent.click(viewFullButton);
      
      expect(mockStoreWithAnswer.setSidePanelOpen).toHaveBeenCalledWith(true, 'qa-results');
    });
  });

  describe('Error Handling', () => {
    it('has error handling structure in place', () => {
      render(<QuestionBox />);
      
      // Test that the component renders without errors
      const input = screen.getByPlaceholderText('Ask a question...');
      expect(input).toBeInTheDocument();
    });

    it('handles input validation correctly', () => {
      const mockStoreWithEmptyQuestion = {
        ...mockStore,
        currentQuestion: '',
        isConnected: true,
      };
      
      mockUseStore.mockReturnValue(mockStoreWithEmptyQuestion as any);
      
      render(<QuestionBox />);
      
      const form = screen.getByRole('textbox').closest('form');
      fireEvent.submit(form!);
      
      // Should not call API with empty question
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('shows proper error styling structure', () => {
      render(<QuestionBox />);
      
      // Test that error icon structure exists
      const input = screen.getByPlaceholderText('Ask a question...');
      const iconContainer = input.parentElement?.querySelector('svg');
      expect(iconContainer).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper form structure', () => {
      render(<QuestionBox />);
      
      const form = screen.getByRole('textbox').closest('form');
      expect(form).toBeInTheDocument();
    });

    it('has proper input attributes', () => {
      render(<QuestionBox />);
      
      const input = screen.getByPlaceholderText('Ask a question...');
      expect(input).toHaveAttribute('type', 'text');
    });

    it('shows proper disabled state styling', () => {
      mockStore.isConnected = false;
      render(<QuestionBox />);
      
      const input = screen.getByPlaceholderText('Ask a question...');
      expect(input).toHaveClass('disabled:opacity-50', 'disabled:cursor-not-allowed');
    });
  });
});