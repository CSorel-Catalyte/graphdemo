/**
 * Performance monitoring component for the AI Knowledge Mapper.
 * Provides real-time performance metrics and optimization hints for demo presentation.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store/useStore';

interface PerformanceMetrics {
  fps: number;
  nodeCount: number;
  edgeCount: number;
  renderTime: number;
  memoryUsage: number;
  networkLatency: number;
}

interface PerformanceMonitorProps {
  isVisible?: boolean;
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
  className?: string;
}

const PerformanceMonitor: React.FC<PerformanceMonitorProps> = ({
  isVisible = false,
  position = 'bottom-right',
  className = ''
}) => {
  const { nodes, edges, isConnected } = useStore();
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    fps: 60,
    nodeCount: 0,
    edgeCount: 0,
    renderTime: 0,
    memoryUsage: 0,
    networkLatency: 0
  });
  const [isExpanded, setIsExpanded] = useState(false);

  // FPS monitoring
  useEffect(() => {
    let frameCount = 0;
    let lastTime = performance.now();
    let animationId: number;

    const measureFPS = () => {
      frameCount++;
      const currentTime = performance.now();
      
      if (currentTime - lastTime >= 1000) {
        const fps = Math.round((frameCount * 1000) / (currentTime - lastTime));
        setMetrics(prev => ({ ...prev, fps }));
        frameCount = 0;
        lastTime = currentTime;
      }
      
      animationId = requestAnimationFrame(measureFPS);
    };

    if (isVisible) {
      animationId = requestAnimationFrame(measureFPS);
    }

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, [isVisible]);

  // Memory usage monitoring
  useEffect(() => {
    const measureMemory = () => {
      if ('memory' in performance) {
        const memory = (performance as any).memory;
        const memoryUsage = Math.round(memory.usedJSHeapSize / 1024 / 1024);
        setMetrics(prev => ({ ...prev, memoryUsage }));
      }
    };

    const interval = setInterval(measureMemory, 2000);
    return () => clearInterval(interval);
  }, []);

  // Network latency monitoring
  const measureNetworkLatency = useCallback(async () => {
    if (!isConnected) return;

    const startTime = performance.now();
    try {
      const { checkHealth } = await import('../utils/api');
      await checkHealth();
      const latency = Math.round(performance.now() - startTime);
      setMetrics(prev => ({ ...prev, networkLatency: latency }));
    } catch (error) {
      setMetrics(prev => ({ ...prev, networkLatency: -1 }));
    }
  }, [isConnected]);

  useEffect(() => {
    if (isConnected) {
      measureNetworkLatency();
      const interval = setInterval(measureNetworkLatency, 5000);
      return () => clearInterval(interval);
    }
  }, [isConnected, measureNetworkLatency]);

  // Update node and edge counts
  useEffect(() => {
    setMetrics(prev => ({
      ...prev,
      nodeCount: nodes.size,
      edgeCount: edges.size
    }));
  }, [nodes.size, edges.size]);

  // Performance status indicators
  const getPerformanceStatus = () => {
    const { fps, memoryUsage, networkLatency } = metrics;
    
    if (fps < 30 || memoryUsage > 100 || networkLatency > 1000) {
      return { status: 'poor', color: 'red', message: 'Performance issues detected' };
    } else if (fps < 45 || memoryUsage > 50 || networkLatency > 500) {
      return { status: 'fair', color: 'orange', message: 'Performance could be better' };
    } else {
      return { status: 'good', color: 'green', message: 'Performance is optimal' };
    }
  };

  const performanceStatus = getPerformanceStatus();

  const positionClasses = {
    'top-left': 'top-4 left-4',
    'top-right': 'top-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'bottom-right': 'bottom-4 right-4'
  };

  if (!isVisible) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      className={`fixed ${positionClasses[position]} z-40 ${className}`}
    >
      <motion.div
        layout
        className="glass-dark rounded-lg shadow-xl border border-gray-600/50 overflow-hidden"
      >
        {/* Compact view */}
        <motion.div
          className="p-3 cursor-pointer"
          onClick={() => setIsExpanded(!isExpanded)}
          whileHover={{ backgroundColor: 'rgba(255, 255, 255, 0.05)' }}
        >
          <div className="flex items-center space-x-3">
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className={`w-3 h-3 rounded-full ${
                performanceStatus.color === 'green' ? 'bg-green-400' :
                performanceStatus.color === 'orange' ? 'bg-orange-400' :
                'bg-red-400'
              }`}
            />
            <div className="text-sm">
              <div className="text-white font-medium">
                {metrics.fps} FPS
              </div>
              <div className="text-gray-400 text-xs">
                {metrics.nodeCount}N {metrics.edgeCount}E
              </div>
            </div>
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </motion.div>
          </div>
        </motion.div>

        {/* Expanded view */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="border-t border-gray-600/50"
            >
              <div className="p-4 space-y-3">
                {/* Performance status */}
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${
                    performanceStatus.color === 'green' ? 'bg-green-400' :
                    performanceStatus.color === 'orange' ? 'bg-orange-400' :
                    'bg-red-400'
                  }`} />
                  <span className="text-xs text-gray-300">
                    {performanceStatus.message}
                  </span>
                </div>

                {/* Metrics grid */}
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <div className="text-gray-400">FPS</div>
                    <div className={`font-mono ${
                      metrics.fps >= 45 ? 'text-green-400' :
                      metrics.fps >= 30 ? 'text-orange-400' :
                      'text-red-400'
                    }`}>
                      {metrics.fps}
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-gray-400">Memory</div>
                    <div className={`font-mono ${
                      metrics.memoryUsage <= 50 ? 'text-green-400' :
                      metrics.memoryUsage <= 100 ? 'text-orange-400' :
                      'text-red-400'
                    }`}>
                      {metrics.memoryUsage}MB
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-gray-400">Nodes</div>
                    <div className="font-mono text-blue-400">
                      {metrics.nodeCount}
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-gray-400">Edges</div>
                    <div className="font-mono text-purple-400">
                      {metrics.edgeCount}
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-gray-400">Latency</div>
                    <div className={`font-mono ${
                      metrics.networkLatency === -1 ? 'text-red-400' :
                      metrics.networkLatency <= 200 ? 'text-green-400' :
                      metrics.networkLatency <= 500 ? 'text-orange-400' :
                      'text-red-400'
                    }`}>
                      {metrics.networkLatency === -1 ? 'N/A' : `${metrics.networkLatency}ms`}
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-gray-400">Render</div>
                    <div className="font-mono text-cyan-400">
                      {metrics.renderTime.toFixed(1)}ms
                    </div>
                  </div>
                </div>

                {/* Performance tips */}
                {performanceStatus.status !== 'good' && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-3 p-2 bg-yellow-900/30 border border-yellow-600/50 rounded text-xs"
                  >
                    <div className="text-yellow-400 font-medium mb-1">Performance Tips:</div>
                    <ul className="text-yellow-300 space-y-1">
                      {metrics.fps < 30 && (
                        <li>• Reduce graph complexity or zoom out</li>
                      )}
                      {metrics.memoryUsage > 100 && (
                        <li>• Consider clearing old graph data</li>
                      )}
                      {metrics.networkLatency > 500 && (
                        <li>• Check network connection</li>
                      )}
                    </ul>
                  </motion.div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  );
};

export default PerformanceMonitor;