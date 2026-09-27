import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Notification } from '../types/api';
import { apiClient, API_BASE } from '../services/api';

export function useNotifications(token: string | undefined) {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const eventSourceRef = useRef<EventSource | null>(null);

    const fetchExisting = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const response = await apiClient.getNotifications(50, token);
            setNotifications(response.notifications);
            setUnreadCount(response.unread_count);
        } catch {
            // silent — notifications unavailable
        } finally {
            setLoading(false);
        }
    }, [token]);

    const markAsRead = useCallback(
        async (notificationId: string) => {
            if (!token) return;
            try {
                await apiClient.markNotificationRead(notificationId, token);
                setNotifications((prev) =>
                    prev.map((n) => (n.id === notificationId ? { ...n, is_read: true } : n)),
                );
                setUnreadCount((prev) => Math.max(0, prev - 1));
            } catch {}
        },
        [token],
    );

    useEffect(() => {
        if (!token) return;

        fetchExisting();

        const url = `${API_BASE}/notifications/stream?token=${encodeURIComponent(token)}`;
        const source = new EventSource(url);
        eventSourceRef.current = source;

        source.addEventListener('notification', (event) => {
            const incoming: Notification = JSON.parse(event.data);
            setNotifications((prev) => [incoming, ...prev]);
            setUnreadCount((prev) => prev + 1);
        });

        return () => {
            source.close();
        };
    }, [token, fetchExisting]);

    return useMemo(
        () => ({ notifications, unreadCount, loading, fetchExisting, markAsRead }),
        [notifications, unreadCount, loading, fetchExisting, markAsRead],
    );
}
