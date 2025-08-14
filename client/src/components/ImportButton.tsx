/**
 * Import button component for loading cached graph data.
 * Provides functionality to import graph data from JSON files for offline mode.
 */

import React, { useRef, useState } from 'react';
import { useStore } from '../store/useStore';
import { Entity, Relationship } from '../types/core';

interface ImportButtonProps {
  className?: string;
}

const ImportButton: React.FC<ImportButtonProps> = ({ className = '' }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const { importGraphData } = useStore();

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsImporting(true);
    setImportStatus(null);

    try {
      // Read file content
      const fileContent = await readFileAsText(file);
      
      // Parse JSON
      const graphData = JSON.parse(fileContent);
      
      // Validate the structure
      if (!isValidGraphData(graphData)) {
        throw new Error('Invalid graph data format');
      }
      
      // Import the data
      importGraphData({
        nodes: graphData.nodes || [],
        edges: graphData.edges || [],
        metadata: graphData.metadata || {}
      });
      
      setImportStatus(`Imported ${graphData.nodes?.length || 0} nodes and ${graphData.edges?.length || 0} edges`);
      
      // Clear status after 3 seconds
      setTimeout(() => setImportStatus(null), 3000);
      
    } catch (error) {
      console.error('Import failed:', error);
      setImportStatus('Import failed. Please check the file format.');
      
      // Clear error status after 5 seconds
      setTimeout(() => setImportStatus(null), 5000);
    } finally {
      setIsImporting(false);
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

  const isValidGraphData = (data: any): boolean => {
    try {
      // Check if it has the expected structure
      if (typeof data !== 'object' || data === null) return false;
      
      // Check for nodes array
      if (!Array.isArray(data.nodes)) return false;
      
      // Check for edges array
      if (!Array.isArray(data.edges)) return false;
      
      // Validate node structure (basic check)
      for (const node of data.nodes) {
        if (!node.id || !node.name || !node.type) return false;
      }
      
      // Validate edge structure (basic check)
      for (const edge of data.edges) {
        if (!edge.from_entity || !edge.to_entity || !edge.predicate) return false;
      }
      
      return true;
    } catch {
      return false;
    }
  };

  return (
    <div className={`relative ${className}`}>
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        onChange={handleFileChange}
        className="hidden"
      />
      
      <button
        onClick={handleImportClick}
        disabled={isImporting}
        className={`
          px-4 py-2 rounded-lg font-medium transition-all duration-200
          ${isImporting 
            ? 'bg-gray-600 text-gray-300 cursor-not-allowed' 
            : 'bg-green-600 hover:bg-green-700 text-white hover:shadow-lg'
          }
          flex items-center space-x-2
        `}
        title="Import knowledge graph from JSON file"
      >
        {isImporting ? (
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
            <span>Importing...</span>
          </>
        ) : (
          <>
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" 
              />
            </svg>
            <span>Import</span>
          </>
        )}
      </button>
      
      {/* Status message */}
      {importStatus && (
        <div className={`
          absolute top-full left-0 mt-2 px-3 py-2 rounded-lg text-sm whitespace-nowrap z-10
          ${importStatus.includes('failed') 
            ? 'bg-red-600 text-white' 
            : 'bg-green-600 text-white'
          }
        `}>
          {importStatus}
        </div>
      )}
    </div>
  );
};

export default ImportButton;