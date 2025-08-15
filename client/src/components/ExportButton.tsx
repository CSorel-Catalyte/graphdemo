/**
 * Export button component for downloading the knowledge graph data.
 * Provides functionality to export the complete graph as a JSON file.
 */

import React, { useState } from 'react';
import { exportGraph, downloadAsJson, generateExportFilename } from '../utils/api';

interface ExportButtonProps {
  className?: string;
}

const ExportButton: React.FC<ExportButtonProps> = ({ className = '' }) => {
  const [isExporting, setIsExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState<string | null>(null);

  const handleExport = async () => {
    if (isExporting) return;

    setIsExporting(true);
    setExportStatus(null);

    try {
      // Call the export API
      const graphData = await exportGraph();

      // Generate filename with timestamp
      const filename = generateExportFilename();

      // Download the file
      downloadAsJson(graphData, filename);

      setExportStatus(`Exported ${graphData.total_nodes} nodes and ${graphData.total_edges} edges`);

      // Clear status after 3 seconds
      setTimeout(() => setExportStatus(null), 3000);

    } catch (error) {
      console.error('Export failed:', error);
      setExportStatus('Export failed. Please try again.');

      // Clear error status after 5 seconds
      setTimeout(() => setExportStatus(null), 5000);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={handleExport}
        disabled={isExporting}
        className={`
          px-4 py-2 rounded-lg font-medium transition-all duration-200
          ${isExporting
            ? 'bg-gray-600 text-gray-300 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700 text-white hover:shadow-lg'
          }
          flex items-center space-x-2
        `}
        title="Export knowledge graph as JSON file"
      >
        {isExporting ? (
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
            <span>Exporting...</span>
          </>
        ) : (
          <>
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <span>Export</span>
          </>
        )}
      </button>

      {/* Status message */}
      {exportStatus && (
        <div className={`
          absolute top-full left-0 mt-2 px-3 py-2 rounded-lg text-sm whitespace-nowrap z-10
          ${exportStatus.includes('failed')
            ? 'bg-red-600 text-white'
            : 'bg-green-600 text-white'
          }
        `}>
          {exportStatus}
        </div>
      )}
    </div>
  );
};

export default ExportButton;