/**
 * Loading states and progress indicators for the AI Knowledge Mapper.
 * 
 * This module provides:
 * - Various loading spinners and indicators
 * - Progress bars for long-running operations
 * - Skeleton loaders for content placeholders
 * - Loading overlays and modals
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Upload, Search, Brain, Network, Database } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  color?: 'blue' | 'green' | 'orange' | 'red' | 'gray';
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  color = 'blue',
  className = ''
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
    xl: 'w-12 h-12'
  };

  const colorClasses = {
    blue: 'text-blue-600',
    green: 'text-green-600',
    orange: 'text-orange-600',
    red: 'text-red-600',
    gray: 'text-gray-600'
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
    >
      <Loader2 
        className={`animate-spin ${sizeClasses[size]} ${colorClasses[color]} ${className}`}
      />
    </motion.div>
  );
};

interface ProgressBarProps {
  progress: number; // 0-100
  label?: string;
  showPercentage?: boolean;
  color?: 'blue' | 'green' | 'orange' | 'red';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  label,
  showPercentage = true,
  color = 'blue',
  size = 'md',
  className = ''
}) => {
  const clampedProgress = Math.max(0, Math.min(100, progress));
  
  const colorClasses = {
    blue: 'bg-blue-600',
    green: 'bg-green-600',
    orange: 'bg-orange-600',
    red: 'bg-red-600'
  };

  const heightClasses = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4'
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`w-full ${className}`}
    >
      {(label || showPercentage) && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="flex justify-between items-center mb-2"
        >
          {label && <span className="text-sm font-medium text-gray-700">{label}</span>}
          {showPercentage && (
            <motion.span 
              key={Math.round(clampedProgress)}
              initial={{ scale: 1.1 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.2 }}
              className="text-sm text-gray-500"
            >
              {Math.round(clampedProgress)}%
            </motion.span>
          )}
        </motion.div>
      )}
      <div className={`w-full bg-gray-200 rounded-full ${heightClasses[size]} overflow-hidden`}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${clampedProgress}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className={`${colorClasses[color]} ${heightClasses[size]} rounded-full relative`}
        >
          {/* Shimmer effect for active progress */}
          <motion.div
            animate={{ x: ['-100%', '100%'] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
          />
        </motion.div>
      </div>
    </motion.div>
  );
};

interface ProcessingStageProps {
  stage: string;
  description?: string;
  progress?: number;
  isActive?: boolean;
  isCompleted?: boolean;
  icon?: React.ReactNode;
}

export const ProcessingStage: React.FC<ProcessingStageProps> = ({
  stage,
  description,
  progress,
  isActive = false,
  isCompleted = false,
  icon
}) => {
  const getIcon = () => {
    if (icon) return icon;
    
    // Default icons based on stage name
    if (stage.toLowerCase().includes('chunk')) return <Upload className="w-5 h-5" />;
    if (stage.toLowerCase().includes('extract')) return <Brain className="w-5 h-5" />;
    if (stage.toLowerCase().includes('search')) return <Search className="w-5 h-5" />;
    if (stage.toLowerCase().includes('canon')) return <Network className="w-5 h-5" />;
    if (stage.toLowerCase().includes('stor')) return <Database className="w-5 h-5" />;
    
    return <Loader2 className="w-5 h-5" />;
  };

  return (
    <motion.div 
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex items-center space-x-3 p-3 rounded-lg transition-all duration-300 ${
        isActive ? 'bg-blue-50 border border-blue-200 shadow-sm' : 
        isCompleted ? 'bg-green-50 border border-green-200 shadow-sm' : 
        'bg-gray-50 border border-gray-200'
      }`}
    >
      <motion.div 
        animate={isActive ? { scale: [1, 1.1, 1] } : { scale: 1 }}
        transition={{ duration: 2, repeat: isActive ? Infinity : 0 }}
        className={`flex-shrink-0 ${
          isActive ? 'text-blue-600' :
          isCompleted ? 'text-green-600' :
          'text-gray-400'
        }`}
      >
        {isActive && !isCompleted ? (
          <LoadingSpinner size="sm" color="blue" />
        ) : isCompleted ? (
          <motion.div
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 200, damping: 15 }}
          >
            {getIcon()}
          </motion.div>
        ) : (
          getIcon()
        )}
      </motion.div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <h4 className={`text-sm font-medium ${
            isActive ? 'text-blue-900' :
            isCompleted ? 'text-green-900' :
            'text-gray-700'
          }`}>
            {stage}
          </h4>
          
          <AnimatePresence>
            {isCompleted && (
              <motion.span 
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                className="text-green-600 text-sm"
              >
                ✓
              </motion.span>
            )}
          </AnimatePresence>
        </div>
        
        <AnimatePresence>
          {description && (
            <motion.p 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className={`text-xs mt-1 ${
                isActive ? 'text-blue-700' :
                isCompleted ? 'text-green-700' :
                'text-gray-500'
              }`}
            >
              {description}
            </motion.p>
          )}
        </AnimatePresence>
        
        <AnimatePresence>
          {typeof progress === 'number' && isActive && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-2"
            >
              <ProgressBar 
                progress={progress} 
                size="sm" 
                color="blue"
                showPercentage={false}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};

interface LoadingOverlayProps {
  isVisible: boolean;
  message?: string;
  progress?: number;
  stages?: Array<{
    name: string;
    description?: string;
    progress?: number;
    isActive?: boolean;
    isCompleted?: boolean;
  }>;
  onCancel?: () => void;
  className?: string;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  isVisible,
  message = 'Loading...',
  progress,
  stages,
  onCancel,
  className = ''
}) => {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className={`fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 ${className}`}
        >
          <motion.div 
            initial={{ scale: 0.8, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.8, opacity: 0, y: 20 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4"
          >
            <motion.div 
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="text-center mb-4"
            >
              <LoadingSpinner size="lg" color="blue" className="mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-gray-900">{message}</h3>
            </motion.div>

            <AnimatePresence>
              {typeof progress === 'number' && (
                <motion.div 
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mb-4"
                >
                  <ProgressBar progress={progress} color="blue" />
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {stages && stages.length > 0 && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-2 mb-4"
                >
                  {stages.map((stage, index) => (
                    <ProcessingStage
                      key={index}
                      stage={stage.name}
                      description={stage.description}
                      progress={stage.progress}
                      isActive={stage.isActive}
                      isCompleted={stage.isCompleted}
                    />
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {onCancel && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ delay: 0.2 }}
                  className="text-center"
                >
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={onCancel}
                    className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
                  >
                    Cancel
                  </motion.button>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
  animation?: 'pulse' | 'wave' | 'none';
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'text',
  width,
  height,
  animation = 'pulse'
}) => {
  const baseClasses = 'bg-gray-200';
  
  const variantClasses = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-md'
  };

  const animationClasses = {
    pulse: 'animate-pulse',
    wave: 'animate-pulse', // Could implement wave animation with CSS
    none: ''
  };

  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === 'number' ? `${width}px` : width;
  if (height) style.height = typeof height === 'number' ? `${height}px` : height;

  // Default dimensions for text variant
  if (variant === 'text' && !height) {
    style.height = '1rem';
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      className={`${baseClasses} ${variantClasses[variant]} ${animationClasses[animation]} ${className} relative overflow-hidden`}
      style={style}
    >
      {animation === 'wave' && (
        <motion.div
          animate={{ x: ['-100%', '100%'] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent"
        />
      )}
    </motion.div>
  );
};

// Skeleton components for specific UI elements
export const GraphSkeleton: React.FC = () => (
  <motion.div 
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    className="h-64 bg-gray-100 rounded-lg flex items-center justify-center"
  >
    <motion.div 
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ delay: 0.2 }}
      className="text-center"
    >
      <Skeleton variant="circular" width={64} height={64} className="mx-auto mb-4" animation="wave" />
      <Skeleton width="120px" height="16px" className="mx-auto mb-2" animation="wave" />
      <Skeleton width="80px" height="12px" className="mx-auto" animation="wave" />
    </motion.div>
  </motion.div>
);

export const SidePanelSkeleton: React.FC = () => (
  <motion.div 
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    className="p-4 space-y-4"
  >
    <motion.div 
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ delay: 0.1 }}
      className="flex items-center space-x-3"
    >
      <Skeleton variant="circular" width={40} height={40} animation="wave" />
      <div className="flex-1">
        <Skeleton width="60%" height="16px" className="mb-2" animation="wave" />
        <Skeleton width="40%" height="12px" animation="wave" />
      </div>
    </motion.div>
    
    <motion.div 
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ delay: 0.2 }}
      className="space-y-2"
    >
      <Skeleton width="100%" height="12px" animation="wave" />
      <Skeleton width="80%" height="12px" animation="wave" />
      <Skeleton width="90%" height="12px" animation="wave" />
    </motion.div>
    
    <motion.div 
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ delay: 0.3 }}
      className="space-y-3"
    >
      <Skeleton width="100%" height="32px" animation="wave" />
      <Skeleton width="100%" height="32px" animation="wave" />
    </motion.div>
  </motion.div>
);

export const SearchResultsSkeleton: React.FC = () => (
  <motion.div 
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    className="space-y-2"
  >
    {[...Array(5)].map((_, i) => (
      <motion.div 
        key={i}
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ delay: i * 0.1 }}
        className="flex items-center space-x-3 p-2"
      >
        <Skeleton variant="circular" width={24} height={24} animation="wave" />
        <div className="flex-1">
          <Skeleton width="70%" height="14px" className="mb-1" animation="wave" />
          <Skeleton width="50%" height="12px" animation="wave" />
        </div>
      </motion.div>
    ))}
  </motion.div>
);

// Hook for managing loading states
export const useLoadingState = (initialState = false) => {
  const [isLoading, setIsLoading] = React.useState(initialState);
  const [progress, setProgress] = React.useState(0);
  const [message, setMessage] = React.useState('');
  const [stages, setStages] = React.useState<Array<{
    name: string;
    description?: string;
    progress?: number;
    isActive?: boolean;
    isCompleted?: boolean;
  }>>([]);

  const startLoading = React.useCallback((loadingMessage = 'Loading...') => {
    setIsLoading(true);
    setProgress(0);
    setMessage(loadingMessage);
    setStages([]);
  }, []);

  const stopLoading = React.useCallback(() => {
    setIsLoading(false);
    setProgress(0);
    setMessage('');
    setStages([]);
  }, []);

  const updateProgress = React.useCallback((newProgress: number, newMessage?: string) => {
    setProgress(newProgress);
    if (newMessage) setMessage(newMessage);
  }, []);

  const updateStages = React.useCallback((newStages: typeof stages) => {
    setStages(newStages);
  }, []);

  const updateStage = React.useCallback((stageName: string, updates: Partial<typeof stages[0]>) => {
    setStages(prev => prev.map(stage => 
      stage.name === stageName ? { ...stage, ...updates } : stage
    ));
  }, []);

  return {
    isLoading,
    progress,
    message,
    stages,
    startLoading,
    stopLoading,
    updateProgress,
    updateStages,
    updateStage
  };
};