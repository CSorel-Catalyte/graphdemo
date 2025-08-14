/**
 * Header component with application title and main controls.
 * Contains search box, question box, and connection status.
 */

import React from 'react';
import { motion } from 'framer-motion';
import ConnectionStatus from './ConnectionStatus';
import SearchBox from './SearchBox';
import QuestionBox from './QuestionBox';
import ExportButton from './ExportButton';
import ImportButton from './ImportButton';
import OfflineIndicator from './OfflineIndicator';

const Header: React.FC = () => {

  return (
    <motion.header 
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="bg-gray-800/95 backdrop-blur-sm border-b border-gray-700/50 p-4"
    >
      <div className="flex items-center justify-between">
        {/* Title and subtitle */}
        <motion.div 
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.1, duration: 0.5 }}
          className="flex-shrink-0"
        >
          <h1 className="text-2xl font-bold text-white">AI Knowledge Mapper</h1>
          <p className="text-gray-300 text-sm">Interactive knowledge graph visualization</p>
        </motion.div>
        
        {/* Controls */}
        <motion.div 
          initial={{ y: -10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="flex items-center space-x-4 flex-1 max-w-2xl mx-8"
        >
          {/* Search box */}
          <SearchBox className="flex-1" placeholder="Search entities..." />
          
          {/* Question box */}
          <QuestionBox className="flex-1" placeholder="Ask a question..." />
        </motion.div>
        
        {/* Import/Export, offline indicator, and connection status */}
        <motion.div 
          initial={{ x: 20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="flex-shrink-0 flex items-center space-x-3"
        >
          <ImportButton />
          <ExportButton />
          <OfflineIndicator />
          <ConnectionStatus />
        </motion.div>
      </div>
    </motion.header>
  );
};

export default Header;