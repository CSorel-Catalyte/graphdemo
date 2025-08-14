/**
 * Comprehensive notification system for user feedback.
 * 
 * This module provides:
 * - Toast notifications for various message types
 * - Persistent notifications for important messages
 * - Action notifications with buttons
 * - Progress notifications for long operations
 * - Notification queue management
 */

import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import { X, CheckCircle, AlertCircle, AlertTriangle, Info, Wifi, WifiOff } from 'lucide-react';

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info' | 'loading';
  title: string;
  message?: string;
  duration?: number; // milliseconds, 0 for persistent
  persistent?: boolean;
  actions?: Array<{
    label: string;
    action: () => void;
    style?: 'primary' | 'secondary' | 'danger';
  }>;
  progress?: number; // 0-100 for progress notifications
  timestamp: Date;
  dismissible?: boolean;
}

interface NotificationState {
  notifications: Notification[];
  maxNotifications: number;
}

type NotificationAction =
  | { type: 'ADD_NOTIFICATION'; payload: Notification }
  | { type: 'REMOVE_NOTIFICATION'; payload: string }
  | { type: 'UPDATE_NOTIFICATION'; payload: { id: string; updates: Partial<Notification> } }
  | { type: 'CLEAR_ALL' }
  | { type: 'CLEAR_TYPE'; payload: Notification['type'] };

const initialState: NotificationState = {
  notifications: [],
  maxNotifications: 5
};

function notificationReducer(state: NotificationState, action: NotificationAction): NotificationState {
  switch (action.type) {
    case 'ADD_NOTIFICATION':
      const newNotifications = [action.payload, ...state.notifications];
      // Keep only the most recent notifications
      return {
        ...state,
        notifications: newNotifications.slice(0, state.maxNotifications)
      };

    case 'REMOVE_NOTIFICATION':
      return {
        ...state,
        notifications: state.notifications.filter(n => n.id !== action.payload)
      };

    case 'UPDATE_NOTIFICATION':
      return {
        ...state,
        notifications: state.notifications.map(n =>
          n.id === action.payload.id ? { ...n, ...action.payload.updates } : n
        )
      };

    case 'CLEAR_ALL':
      return {
        ...state,
        notifications: []
      };

    case 'CLEAR_TYPE':
      return {
        ...state,
        notifications: state.notifications.filter(n => n.type !== action.payload)
      };

    default:
      return state;
  }
}

interface NotificationContextType {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => string;
  removeNotification: (id: string) => void;
  updateNotification: (id: string, updates: Partial<Notification>) => void;
  clearAll: () => void;
  clearType: (type: Notification['type']) => void;
  // Convenience methods
  success: (title: string, message?: string, options?: Partial<Notification>) => string;
  error: (title: string, message?: string, options?: Partial<Notification>) => string;
  warning: (title: string, message?: string, options?: Partial<Notification>) => string;
  info: (title: string, message?: string, options?: Partial<Notification>) => string;
  loading: (title: string, message?: string, options?: Partial<Notification>) => string;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: React.ReactNode;
  maxNotifications?: number;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({
  children,
  maxNotifications = 5
}) => {
  const [state, dispatch] = useReducer(notificationReducer, {
    ...initialState,
    maxNotifications
  });

  const addNotification = useCallback((notification: Omit<Notification, 'id' | 'timestamp'>) => {
    const id = `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const fullNotification: Notification = {
      ...notification,
      id,
      timestamp: new Date(),
      dismissible: notification.dismissible ?? true,
      duration: notification.duration ?? (notification.type === 'error' ? 8000 : 4000)
    };

    dispatch({ type: 'ADD_NOTIFICATION', payload: fullNotification });
    return id;
  }, []);

  const removeNotification = useCallback((id: string) => {
    dispatch({ type: 'REMOVE_NOTIFICATION', payload: id });
  }, []);

  const updateNotification = useCallback((id: string, updates: Partial<Notification>) => {
    dispatch({ type: 'UPDATE_NOTIFICATION', payload: { id, updates } });
  }, []);

  const clearAll = useCallback(() => {
    dispatch({ type: 'CLEAR_ALL' });
  }, []);

  const clearType = useCallback((type: Notification['type']) => {
    dispatch({ type: 'CLEAR_TYPE', payload: type });
  }, []);

  // Convenience methods
  const success = useCallback((title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({ ...options, type: 'success', title, message });
  }, [addNotification]);

  const error = useCallback((title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({ ...options, type: 'error', title, message });
  }, [addNotification]);

  const warning = useCallback((title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({ ...options, type: 'warning', title, message });
  }, [addNotification]);

  const info = useCallback((title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({ ...options, type: 'info', title, message });
  }, [addNotification]);

  const loading = useCallback((title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({ 
      ...options, 
      type: 'loading', 
      title, 
      message, 
      duration: 0, // Loading notifications are persistent by default
      persistent: true 
    });
  }, [addNotification]);

  const contextValue: NotificationContextType = {
    notifications: state.notifications,
    addNotification,
    removeNotification,
    updateNotification,
    clearAll,
    clearType,
    success,
    error,
    warning,
    info,
    loading
  };

  return (
    <NotificationContext.Provider value={contextValue}>
      {children}
      <NotificationContainer />
    </NotificationContext.Provider>
  );
};

const NotificationContainer: React.FC = () => {
  const { notifications, removeNotification } = useNotifications();

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm w-full">
      {notifications.map(notification => (
        <NotificationItem
          key={notification.id}
          notification={notification}
          onDismiss={() => removeNotification(notification.id)}
        />
      ))}
    </div>
  );
};

interface NotificationItemProps {
  notification: Notification;
  onDismiss: () => void;
}

const NotificationItem: React.FC<NotificationItemProps> = ({ notification, onDismiss }) => {
  const { updateNotification } = useNotifications();

  // Auto-dismiss timer
  useEffect(() => {
    if (notification.duration && notification.duration > 0 && !notification.persistent) {
      const timer = setTimeout(() => {
        onDismiss();
      }, notification.duration);

      return () => clearTimeout(timer);
    }
  }, [notification.duration, notification.persistent, onDismiss]);

  const getIcon = () => {
    switch (notification.type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-orange-500" />;
      case 'info':
        return <Info className="w-5 h-5 text-blue-500" />;
      case 'loading':
        return (
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        );
      default:
        return <Info className="w-5 h-5 text-gray-500" />;
    }
  };

  const getBackgroundColor = () => {
    switch (notification.type) {
      case 'success':
        return 'bg-green-50 border-green-200';
      case 'error':
        return 'bg-red-50 border-red-200';
      case 'warning':
        return 'bg-orange-50 border-orange-200';
      case 'info':
        return 'bg-blue-50 border-blue-200';
      case 'loading':
        return 'bg-blue-50 border-blue-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const handleActionClick = (action: () => void) => {
    action();
    if (!notification.persistent) {
      onDismiss();
    }
  };

  return (
    <div
      className={`
        ${getBackgroundColor()}
        border rounded-lg shadow-lg p-4 transition-all duration-300 ease-in-out
        transform translate-x-0 opacity-100
        hover:shadow-xl
      `}
      role="alert"
    >
      <div className="flex items-start">
        <div className="flex-shrink-0 mr-3">
          {getIcon()}
        </div>
        
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-gray-900 mb-1">
            {notification.title}
          </h4>
          
          {notification.message && (
            <p className="text-sm text-gray-700 mb-2">
              {notification.message}
            </p>
          )}

          {typeof notification.progress === 'number' && (
            <div className="mb-3">
              <div className="flex justify-between text-xs text-gray-600 mb-1">
                <span>Progress</span>
                <span>{Math.round(notification.progress)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${notification.progress}%` }}
                />
              </div>
            </div>
          )}

          {notification.actions && notification.actions.length > 0 && (
            <div className="flex space-x-2 mt-3">
              {notification.actions.map((action, index) => (
                <button
                  key={index}
                  onClick={() => handleActionClick(action.action)}
                  className={`
                    px-3 py-1 text-xs font-medium rounded transition-colors
                    ${action.style === 'primary' ? 'bg-blue-600 text-white hover:bg-blue-700' :
                      action.style === 'danger' ? 'bg-red-600 text-white hover:bg-red-700' :
                      'bg-gray-200 text-gray-800 hover:bg-gray-300'}
                  `}
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {notification.dismissible && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 ml-2 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Dismiss notification"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};

// Connection status notification hook
export const useConnectionNotifications = () => {
  const { addNotification, removeNotification, clearType } = useNotifications();
  const [connectionNotificationId, setConnectionNotificationId] = React.useState<string | null>(null);

  const showConnectionLost = useCallback(() => {
    clearType('error'); // Clear any existing connection errors
    const id = addNotification({
      type: 'error',
      title: 'Connection Lost',
      message: 'Real-time updates are unavailable. Attempting to reconnect...',
      persistent: true,
      actions: [
        {
          label: 'Retry',
          action: () => window.location.reload(),
          style: 'primary'
        }
      ]
    });
    setConnectionNotificationId(id);
  }, [addNotification, clearType]);

  const showConnectionRestored = useCallback(() => {
    if (connectionNotificationId) {
      removeNotification(connectionNotificationId);
      setConnectionNotificationId(null);
    }
    addNotification({
      type: 'success',
      title: 'Connection Restored',
      message: 'Real-time updates are now available.',
      duration: 3000
    });
  }, [addNotification, removeNotification, connectionNotificationId]);

  const showReconnecting = useCallback(() => {
    if (connectionNotificationId) {
      removeNotification(connectionNotificationId);
    }
    const id = addNotification({
      type: 'loading',
      title: 'Reconnecting...',
      message: 'Attempting to restore connection.',
      persistent: true
    });
    setConnectionNotificationId(id);
  }, [addNotification, removeNotification, connectionNotificationId]);

  return {
    showConnectionLost,
    showConnectionRestored,
    showReconnecting
  };
};

// Processing notification hook for long operations
export const useProcessingNotifications = () => {
  const { addNotification, updateNotification, removeNotification } = useNotifications();

  const startProcessing = useCallback((title: string, message?: string) => {
    return addNotification({
      type: 'loading',
      title,
      message,
      persistent: true,
      progress: 0
    });
  }, [addNotification]);

  const updateProcessing = useCallback((id: string, progress: number, message?: string) => {
    updateNotification(id, {
      progress,
      ...(message && { message })
    });
  }, [updateNotification]);

  const completeProcessing = useCallback((id: string, successTitle: string, successMessage?: string) => {
    removeNotification(id);
    addNotification({
      type: 'success',
      title: successTitle,
      message: successMessage,
      duration: 4000
    });
  }, [addNotification, removeNotification]);

  const failProcessing = useCallback((id: string, errorTitle: string, errorMessage?: string) => {
    removeNotification(id);
    addNotification({
      type: 'error',
      title: errorTitle,
      message: errorMessage,
      duration: 8000
    });
  }, [addNotification, removeNotification]);

  return {
    startProcessing,
    updateProcessing,
    completeProcessing,
    failProcessing
  };
};