/**
 * Main layout component for the AI Knowledge Mapper application.
 * Provides the overall structure with header, main content area, and side panel.
 */

import React from 'react';
import { useStore } from '../store/useStore';
import Header from './Header';
import StatusBar from './StatusBar';
import DebugPanel from './DebugPanel';
import SidePanel from './SidePanel';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { sidePanelOpen, setSidePanelOpen } = useStore();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white flex flex-col">
      {/* Header */}
      <Header />
      
      {/* Main content area */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* Main graph view */}
        <main 
          className={`flex-1 transition-all duration-500 ease-out ${
            sidePanelOpen ? 'mr-96' : 'mr-0'
          }`}
        >
          {children}
        </main>
        
        {/* Side panel */}
        <SidePanel 
          isOpen={sidePanelOpen} 
          onClose={() => setSidePanelOpen(false)} 
        />
      </div>
      
      {/* Status bar */}
      <StatusBar />
      
      {/* Debug panel (development only) */}
      <DebugPanel />
    </div>
  );
};

export default Layout;