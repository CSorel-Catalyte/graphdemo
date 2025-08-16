/**
 * SearchBox component with autocomplete functionality.
 * Provides entity search with result display and graph navigation.
 */

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store/useStore';
import { SearchRequest, SearchResponse } from '../types/api';
import { searchEntities } from '../utils/api';

interface SearchBoxProps {
  className?: string;
  placeholder?: string;
}

const SearchBox: React.FC<SearchBoxProps> = ({ 
  className = '', 
  placeholder = 'Search entities...' 
}) => {
  const {
    searchQuery,
    setSearchQuery,
    searchResults,
    setSearchResults,
    isSearching,
    setSearching,
    isConnected,
    isOfflineMode,
    selectNode,
    setCameraTarget,
    nodes,
  } = useStore();

  const [showResults, setShowResults] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Debounced search effect
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    const timeoutId = setTimeout(() => {
      if (isOfflineMode || !isConnected) {
        performOfflineSearch(searchQuery);
      } else {
        performSearch(searchQuery);
      }
    }, 300); // 300ms debounce

    return () => clearTimeout(timeoutId);
  }, [searchQuery, isConnected, isOfflineMode]);

  // Handle click outside to close results
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        resultsRef.current &&
        !resultsRef.current.contains(event.target as Node) &&
        !searchInputRef.current?.contains(event.target as Node)
      ) {
        setShowResults(false);
        setSelectedIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const performSearch = async (query: string) => {
    if (!query.trim()) return;

    setSearching(true);
    try {
      const request: SearchRequest = {
        q: query,
        k: 8, // Limit to 8 results as per requirements
      };

      const data = await searchEntities(request);
      setSearchResults(data.results);
      setShowResults(data.results.length > 0);
      setSelectedIndex(-1);
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults([]);
      setShowResults(false);
    } finally {
      setSearching(false);
    }
  };

  const performOfflineSearch = (query: string) => {
    if (!query.trim()) return;

    setSearching(true);
    
    try {
      const queryLower = query.toLowerCase();
      const nodeArray = Array.from(nodes.values());
      
      // Simple text-based search through node names, aliases, and summaries
      const matches = nodeArray
        .map(node => {
          let score = 0;
          const nameMatch = node.name.toLowerCase().includes(queryLower);
          const aliasMatch = node.aliases.some(alias => alias.toLowerCase().includes(queryLower));
          const summaryMatch = node.summary.toLowerCase().includes(queryLower);
          
          // Calculate basic relevance score
          if (nameMatch) score += 1.0;
          if (aliasMatch) score += 0.8;
          if (summaryMatch) score += 0.6;
          
          // Boost score by salience
          score *= (0.5 + node.salience);
          
          return score > 0 ? {
            entity: {
              id: node.id,
              name: node.name,
              type: node.type,
              salience: node.salience,
              summary: node.summary,
              aliases: node.aliases,
              embedding: [],
              source_spans: [],
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
            score: Math.min(score, 1.0), // Cap at 1.0
          } : null;
        })
        .filter(Boolean)
        .sort((a, b) => b!.score - a!.score)
        .slice(0, 8); // Limit to 8 results

      setSearchResults(matches as any[]);
      setShowResults(matches.length > 0);
      setSelectedIndex(-1);
    } catch (error) {
      console.error('Offline search error:', error);
      setSearchResults([]);
      setShowResults(false);
    } finally {
      setSearching(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    
    if (!value.trim()) {
      setShowResults(false);
      setSelectedIndex(-1);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showResults || searchResults.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < searchResults.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev > 0 ? prev - 1 : searchResults.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < searchResults.length) {
          selectSearchResult(searchResults[selectedIndex]);
        }
        break;
      case 'Escape':
        setShowResults(false);
        setSelectedIndex(-1);
        searchInputRef.current?.blur();
        break;
    }
  };

  const selectSearchResult = (result: any) => {
    const { entity } = result;
    
    // Select the node in the graph
    selectNode(entity.id);
    
    // Center camera on the selected node if it exists in the graph
    const node = nodes.get(entity.id);
    if (node && node.x !== undefined && node.y !== undefined && node.z !== undefined) {
      setCameraTarget({ x: node.x, y: node.y, z: node.z });
    }
    
    // Close search results
    setShowResults(false);
    setSelectedIndex(-1);
    setSearchQuery('');
    
    // Blur the input
    searchInputRef.current?.blur();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchResults.length > 0) {
      selectSearchResult(searchResults[selectedIndex >= 0 ? selectedIndex : 0]);
    }
  };

  const highlightMatch = (text: string, query: string) => {
    if (!query.trim()) return text;
    
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, index) => 
      regex.test(part) ? (
        <mark key={index} className="bg-blue-500 bg-opacity-30 text-blue-200">
          {part}
        </mark>
      ) : part
    );
  };

  return (
    <div className={`relative ${className}`}>
      <form onSubmit={handleSubmit}>
        <div className="relative">
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onFocus={() => {
              if (searchResults.length > 0) {
                setShowResults(true);
              }
            }}
            placeholder={placeholder}
            disabled={!isConnected && !isOfflineMode}
            className="w-full px-4 py-2 pl-10 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          />
          
          {/* Search icon */}
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          
          {/* Loading spinner */}
          {isSearching && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
              <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
            </div>
          )}
        </div>
      </form>

      {/* Search results dropdown */}
      <AnimatePresence>
        {showResults && searchResults.length > 0 && (
          <motion.div
            ref={resultsRef}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-50 max-h-96 overflow-y-auto"
          >
            {searchResults.map((result, index) => (
              <motion.div
                key={result.entity.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.05 }}
                className={`px-4 py-3 cursor-pointer border-b border-gray-700 last:border-b-0 transition-colors ${
                  index === selectedIndex 
                    ? 'bg-blue-600 bg-opacity-50' 
                    : 'hover:bg-gray-700'
                }`}
                onClick={() => selectSearchResult(result)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <h4 className="text-sm font-medium text-white truncate">
                        {highlightMatch(result.entity.name, searchQuery)}
                      </h4>
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-600 text-gray-200">
                        {result.entity.type}
                      </span>
                    </div>
                    
                    {result.entity.summary && (
                      <p className="mt-1 text-xs text-gray-400 line-clamp-2">
                        {highlightMatch(result.entity.summary, searchQuery)}
                      </p>
                    )}
                    
                    {result.entity.aliases.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {result.entity.aliases.slice(0, 3).map((alias, aliasIndex) => (
                          <span key={aliasIndex} className="text-xs text-blue-300">
                            {highlightMatch(alias, searchQuery)}
                          </span>
                        ))}
                        {result.entity.aliases.length > 3 && (
                          <span className="text-xs text-gray-500">
                            +{result.entity.aliases.length - 3} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex-shrink-0 ml-2 text-right">
                    <div className="text-xs text-gray-400">
                      Score: {(result.score * 100).toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500">
                      Salience: {(result.entity.salience * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
            
            {/* Results footer */}
            <div className="px-4 py-2 bg-gray-750 text-xs text-gray-400 border-t border-gray-700">
              {searchResults.length} result{searchResults.length !== 1 ? 's' : ''} found
              <span className="float-right">
                Use ↑↓ to navigate, Enter to select
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* No results message */}
      <AnimatePresence>
        {showResults && searchResults.length === 0 && searchQuery.trim() && !isSearching && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-50 px-4 py-3"
          >
            <div className="text-center text-gray-400">
              <svg className="mx-auto h-8 w-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0112 15c-2.34 0-4.467-.881-6.08-2.33" />
              </svg>
              <p className="text-sm">No entities found for "{searchQuery}"</p>
              <p className="text-xs text-gray-500 mt-1">Try a different search term</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default SearchBox;