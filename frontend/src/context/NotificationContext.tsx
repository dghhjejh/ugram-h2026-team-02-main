import React, { createContext, useContext } from 'react';
import { useAuth } from './AuthContext';
import { useNotifications } from '../hooks/useNotifications';
import type { Notification } from '../types/api';

type NotificationContextValue = {
    notifications: Notification[];
    unreadCount: number;
    loading: boolean;
    markAsRead: (id: string) => Promise<void>;
};

const NotificationContext = createContext<NotificationContextValue | null>(null);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
    const { token } = useAuth();
    const notificationState = useNotifications(token ?? undefined);

    return (
        <NotificationContext.Provider value={notificationState}>
            {children}
        </NotificationContext.Provider>
    );
}

export function useNotificationContext(): NotificationContextValue {
    const context = useContext(NotificationContext);
    if (!context) throw new Error('useNotificationContext must be used within NotificationProvider');
    return context;
}
