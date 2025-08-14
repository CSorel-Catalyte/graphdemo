import React, { useState, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { motion } from 'framer-motion';
import Layout from './components/Layout';
import Graph3D from './components/Graph3D';
import WebSocketProvider from './components/WebSocketProvider';
import { ErrorBoundary, GraphErrorBoundary } from './components/ErrorBoundary';
import { NotificationProvider } from './components/NotificationSystem';
import PerformanceMonitor from './components/PerformanceMonitor';
import GraphTransitions from './components/GraphTransitions';

function App() {
  const [showPerformanceMonitor, setShowPerformanceMonitor] = useState(false);
  const [showGraphTransitions, setShowGraphTransitions] = useState(true);

  // Toggle performance monitor with keyboard shortcut
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'P') {
        setShowPerformanceMonitor(prev => !prev);
      }
      if (e.ctrlKey && e.shiftKey && e.key === 'T') {
        setShowGraphTransitions(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  return (
    <ErrorBoundary>
      <NotificationProvider>
        <WebSocketProvider>
          {/* Background transitions and effects */}
          <GraphTransitions isVisible={showGraphTransitions} />
          
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8 }}
          >
            <Layout>
              <GraphErrorBoundary>
                <Graph3D />
              </GraphErrorBoundary>
            </Layout>
          </motion.div>

          {/* Performance monitoring overlay */}
          <PerformanceMonitor 
            isVisible={showPerformanceMonitor}
            position="bottom-right"
          />
        </WebSocketProvider>
        
        {/* Enhanced toast notifications */}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: 'rgba(31, 41, 55, 0.95)',
              backdropFilter: 'blur(10px)',
              color: '#fff',
              borderRadius: '12px',
              fontSize: '14px',
              maxWidth: '400px',
              border: '1px solid rgba(75, 85, 99, 0.5)',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
            },
            success: {
              iconTheme: {
                primary: '#10b981',
                secondary: '#fff',
              },
              style: {
                border: '1px solid rgba(16, 185, 129, 0.3)',
              },
            },
            error: {
              iconTheme: {
                primary: '#ef4444',
                secondary: '#fff',
              },
              duration: 6000,
              style: {
                border: '1px solid rgba(239, 68, 68, 0.3)',
              },
            },
            loading: {
              iconTheme: {
                primary: '#3b82f6',
                secondary: '#fff',
              },
              style: {
                border: '1px solid rgba(59, 130, 246, 0.3)',
              },
            },
          }}
        />
      </NotificationProvider>
    </ErrorBoundary>
  );
}

export default App;