import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../services/api';
import UserAvatar from './UserAvatar';
import type { UserProfile } from '../types/api';

const MIN_QUERY_LENGTH = 2;

type Props = {
    query: string;
    isActive: boolean;
    token?: string;
    onClose: () => void;
};

export default function PeopleSearchResults({ query, isActive, token, onClose }: Props) {
    const [users, setUsers] = useState<UserProfile[]>([]);
    const requestIdRef = useRef(0);
    const normalizedQuery = query.trim();
    const canFetch = isActive && normalizedQuery.length >= MIN_QUERY_LENGTH;

    useEffect(() => {
        if (!canFetch) {
            setUsers([]);
            return;
        }
        requestIdRef.current += 1;
        const requestId = requestIdRef.current;
        const timer = setTimeout(() => {
            apiClient.searchUsers(normalizedQuery, 5, token)
                .then((result) => {
                    if (requestIdRef.current === requestId) setUsers(result);
                })
                .catch(() => {
                    if (requestIdRef.current === requestId) setUsers([]);
                });
        }, 400);
        return () => clearTimeout(timer);
    }, [canFetch, normalizedQuery, token]);

    if (normalizedQuery.length > 0 && normalizedQuery.length < MIN_QUERY_LENGTH) {
        return (
            <div className="mt-2 px-2 py-1 text-[10px] uppercase tracking-wider text-gray-400 font-bold">
                Type at least {MIN_QUERY_LENGTH} characters
            </div>
        );
    }

    if (canFetch && users.length === 0) {
        return (
            <div className="mt-2 px-2 py-1 text-[10px] uppercase tracking-wider text-gray-400 font-bold">
                Press Enter to search
            </div>
        );
    }

    if (users.length === 0) return null;

    return (
        <ul className="mt-1">
            {users.map((u) => (
                <li key={u.id}>
                    <Link
                        to={`/profile/${u.id}`}
                        onClick={onClose}
                        className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                        <UserAvatar user={u} token={token} size="sm" />
                        <span className="text-sm font-medium text-gray-900 dark:text-white truncate">{u.username}</span>
                    </Link>
                </li>
            ))}
            <li>
                <button
                    type="submit"
                    className="w-full text-left px-3 py-2 text-xs text-indigo-600 dark:text-indigo-400 font-semibold hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl transition-colors"
                >
                    See all results for &ldquo;{normalizedQuery}&rdquo;
                </button>
            </li>
        </ul>
    );
}
