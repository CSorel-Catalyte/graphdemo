/**
 * Load Text button component for processing text files through the ingestion pipeline.
 * Accepts text files and sends them to the backend for entity extraction and graph building.
 */

import React, { useRef, useState } from 'react';
import { ingestText } from '../utils/api';

interface LoadTextButtonProps {
  className?: string;
}

const LoadTextButton: React.FC<LoadTextButtonProps> = ({ className = '' }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadStatus, setLoadStatus] = useState<string | null>(null);

  const handleLoadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    setLoadStatus(null);

    try {
      // Read file content
      const fileContent = await readFileAsText(file);
      
      // Validate file has content
      if (!fileContent.trim()) {
        throw new Error('File is empty');
      }
      
      // Use filename (without extension) as doc_id
      const docId = file.name.replace(/\.[^/.]+$/, '');
      
      // Send to backend for processing
      const response = await ingestText({
        doc_id: docId,
        text: fileContent
      });
      
      setLoadStatus(`Processed ${response.chunks_processed} chunks, extracted ${response.entities_extracted} entities and ${response.relationships_extracted} relationships`);
      
      // Clear status after 5 seconds
      setTimeout(() => setLoadStatus(null), 5000);
      
    } catch (error) {
      console.error('Text loading failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setLoadStatus(`Loading failed: ${errorMessage}`);
      
      // Clear error status after 5 seconds
      setTimeout(() => setLoadStatus(null), 5000);
    } finally {
      setIsLoading(false);
      // Clear the file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const readFileAsText = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target?.result as string);
      reader.onerror = (e) => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  };

  return (
    <div className={`relative ${className}`}>
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.md,.text"
        onChange={handleFileChange}
        className="hidden"
      />
      
      <button
        onClick={handleLoadClick}
        disabled={isLoading}
        className={`
          px-4 py-2 rounded-lg font-medium transition-all duration-200
          ${isLoading 
            ? 'bg-gray-600 text-gray-300 cursor-not-allowed' 
            : 'bg-purple-600 hover:bg-purple-700 text-white hover:shadow-lg'
          }
          flex items-center space-x-2
        `}
        title="Load text file and extract knowledge graph"
      >
        {isLoading ? (
          <>
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle 
                className="opacity-25" 
                cx="12" 
                cy="12" 
                r="10" 
                stroke="currentColor" 
                strokeWidth="4"
              />
              <path 
                className="opacity-75" 
                fill="currentColor" 
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>Processing...</span>
          </>
        ) : (
          <>
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" 
              />
            </svg>
            <span>Load Text</span>
          </>
        )}
      </button>
      
      {/* Status message */}
      {loadStatus && (
        <div className={`
          absolute top-full left-0 mt-2 px-3 py-2 rounded-lg text-sm whitespace-nowrap z-10 max-w-xs
          ${loadStatus.includes('failed') 
            ? 'bg-red-600 text-white' 
            : 'bg-green-600 text-white'
          }
        `}>
          {loadStatus}
        </div>
      )}
    </div>
  );
};

export default LoadTextButton;