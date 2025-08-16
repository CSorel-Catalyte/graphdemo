/**
 * QuestionBox component with natural language input for question-answering.
 * Provides question input, answer display with formatted citations, and clickable citations.
 */

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store/useStore';
import { QuestionRequest, QuestionResponse } from '../types/api';
import { askQuestion } from '../utils/api';

interface QuestionBoxProps {
  className?: string;
  placeholder?: string;
}

const QuestionBox: React.FC<QuestionBoxProps> = ({ 
  className = '', 
  placeholder = 'Ask a question...' 
}) => {
  const {
    currentQuestion,
    setCurrentQuestion,
    currentAnswer,
    currentCitations,
    setCurrentAnswer,
    isAnswering,
    setAnswering,
    isConnected,
    selectNode,
    setSidePanelOpen,
  } = useStore();

  const [error, setError] = useState<string | null>(null);
  const questionInputRef = useRef<HTMLInputElement>(null);

  // Clear error when question changes
  useEffect(() => {
    if (error && currentQuestion.trim()) {
      setError(null);
    }
  }, [currentQuestion, error]);

  const performQuestionAnswering = async (question: string) => {
    if (!question.trim()) return;

    setAnswering(true);
    setError(null);
    
    try {
      const request: QuestionRequest = {
        q: question.trim(),
      };

      const data = await askQuestion(request);
      
      // Update store with answer and citations
      setCurrentAnswer(data.answer, data.citations);
      
      // Open side panel to show results
      setSidePanelOpen(true, 'qa-results');
      
    } catch (error) {
      console.error('Question answering error:', error);
      setError(error instanceof Error ? error.message : 'Failed to answer question');
    } finally {
      setAnswering(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (currentQuestion.trim() && !isAnswering && isConnected) {
      performQuestionAnswering(currentQuestion);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentQuestion(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      questionInputRef.current?.blur();
    }
  };

  const handleCitationClick = (nodeId: string) => {
    // Navigate to the cited node in the graph
    selectNode(nodeId);
    setSidePanelOpen(true, 'node-details');
  };

  return (
    <div className={`relative ${className}`}>
      <form onSubmit={handleSubmit}>
        <div className="relative">
          <input
            ref={questionInputRef}
            type="text"
            value={currentQuestion}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={!isConnected || isAnswering}
            className="w-full px-4 py-2 pl-10 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          />
          
          {/* Question icon */}
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          
          {/* Loading spinner */}
          {isAnswering && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
              <div className="animate-spin h-4 w-4 border-2 border-green-500 border-t-transparent rounded-full"></div>
            </div>
          )}
        </div>
      </form>

      {/* Error message */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full left-0 right-0 mt-1 bg-red-900 bg-opacity-50 border border-red-700 rounded-lg shadow-xl z-50 px-4 py-3"
          >
            <div className="flex items-center space-x-2">
              <svg className="h-4 w-4 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-red-200">{error}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Quick answer preview (optional - shows when not in side panel) */}
      <AnimatePresence>
        {currentAnswer && !isAnswering && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-40 max-w-md"
          >
            <div className="p-4">
              <div className="flex items-start justify-between mb-2">
                <h4 className="text-sm font-semibold text-green-400">Quick Answer</h4>
                <button
                  onClick={() => setSidePanelOpen(true, 'qa-results')}
                  className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                >
                  View Full Answer
                </button>
              </div>
              
              <p className="text-sm text-gray-200 line-clamp-3 mb-3">
                {currentAnswer.length > 150 ? currentAnswer.substring(0, 150) + '...' : currentAnswer}
              </p>
              
              {/* Citations preview */}
              {currentCitations && currentCitations.length > 0 && (
                <div>
                  <p className="text-xs text-gray-400 mb-2">
                    {currentCitations.length} citation{currentCitations.length !== 1 ? 's' : ''}:
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {currentCitations.slice(0, 3).map((citation, index) => (
                      <button
                        key={`${citation.node_id}-${index}`}
                        onClick={() => handleCitationClick(citation.node_id)}
                        className="text-xs bg-blue-600 hover:bg-blue-700 text-blue-100 px-2 py-1 rounded transition-colors"
                      >
                        Citation {index + 1}
                      </button>
                    ))}
                    {currentCitations.length > 3 && (
                      <span className="text-xs text-gray-500 px-2 py-1">
                        +{currentCitations.length - 3} more
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default QuestionBox;