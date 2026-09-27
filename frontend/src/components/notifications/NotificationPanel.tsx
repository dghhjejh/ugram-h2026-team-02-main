import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { X } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import type { Notification } from '../../types/api';

type NotificationPanelProps = {
    notifications: Notification[];
    onMarkAsRead: (id: string) => void;
    onClose: () => void;
};

const notificationLabel = (type: Notification['notification_type']) =>
    type === 'comment' ? 'commented on your photo' : 'liked your photo';

const actorDisplayName = (notification: Notification) =>
    notification.actor?.username ?? 'Someone';

const actorAvatarUrl = (notification: Notification) => {
    const displayName = actorDisplayName(notification);
    return notification.actor?.profile_photo_url
        ?? `https://ui-avatars.com/api/?name=${encodeURIComponent(displayName)}&size=64&background=10b981&color=white&font-size=0.4`;
};

export default function NotificationPanel({ notifications, onMarkAsRead, onClose }: NotificationPanelProps) {
    const { user } = useAuth();

    return (
        <div className="absolute right-0 mt-2 w-80 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-lg z-50 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
                <span className="font-semibold text-gray-900 dark:text-white text-sm">Notifications</span>
                <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                    aria-label="Close notifications"
                >
                    <X size={16} />
                </button>
            </div>
            {notifications.length === 0 ? (
                <div className="px-4 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
                    No notifications yet
                </div>
            ) : (
                <ul className="max-h-96 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-800">
                    {notifications.map((notification) => (
                        <li key={notification.id}>
                            <Link
                                to={`/profile/${user?.id}?openImage=${notification.image_id}`}
                                className={`px-4 py-3 flex gap-3 items-start hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${notification.is_read ? 'opacity-60' : ''}`}
                                onClick={() => {
                                    if (!notification.is_read) onMarkAsRead(notification.id);
                                    onClose();
                                }}
                            >
                                <img
                                    src={actorAvatarUrl(notification)}
                                    alt={actorDisplayName(notification)}
                                    className="w-9 h-9 rounded-full object-cover shrink-0"
                                />
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm text-gray-800 dark:text-gray-200">
                                        <span className="font-medium">{actorDisplayName(notification)}</span>
                                        {' '}{notificationLabel(notification.notification_type)}
                                    </p>
                                    <p className="text-xs text-gray-400 mt-0.5">
                                        {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                                    </p>
                                </div>
                                {notification.is_read ? null : (
                                    <button
                                        onClick={(e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            onMarkAsRead(notification.id);
                                        }}
                                        className="text-xs text-blue-500 hover:text-blue-700 shrink-0 mt-0.5"
                                        aria-label="Mark as read"
                                    >
                                        Mark as read
                                    </button>
                                )}
                            </Link>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
