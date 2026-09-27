import { useState, useEffect, useCallback } from 'react';
import type { UserProfile } from '../types/api';
import { apiClient } from '../services/api';

export function useUsers(token: string | null | undefined, usersPerPage: number, keyword?: string) {
    const [users, setUsers] = useState<UserProfile[]>([]);
    const [postsCountByUserId, setPostsCountByUserId] = useState<Record<string, number>>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [offset, setOffset] = useState(0);
    const [total, setTotal] = useState(0);
    // activeKeyword batches the keyword change and offset reset into a single state update,
    // preventing a spurious fetch with the new keyword at the old offset.
    const [activeKeyword, setActiveKeyword] = useState(keyword);

    useEffect(() => {
        setActiveKeyword(keyword);
        setOffset(0);
    }, [keyword]);

    const loadUsers = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await apiClient.listUsers(usersPerPage, offset, token ?? undefined, activeKeyword);
            setUsers(response.users);
            setTotal(response.total);

            const statsEntries = await Promise.all(
                response.users.map(async (user) => {
                    try {
                        const stats = await apiClient.getUserStats(user.id, token ?? undefined);
                        return [user.id, stats.posts_count] as const;
                    } catch {
                        return [user.id, 0] as const;
                    }
                }),
            );
            setPostsCountByUserId(Object.fromEntries(statsEntries));
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load users');
        } finally {
            setLoading(false);
        }
    }, [usersPerPage, offset, token, activeKeyword]);

    useEffect(() => {
        loadUsers();
    }, [loadUsers]);

    const handleNextPage = () => {
        if (offset + usersPerPage < total) {
            setOffset(offset + usersPerPage);
            window.scrollTo(0, 0);
        }
    };

    const handlePrevPage = () => {
        if (offset - usersPerPage >= 0) {
            setOffset(offset - usersPerPage);
            window.scrollTo(0, 0);
        }
    };

    return {
        users,
        postsCountByUserId,
        loading,
        error,
        offset,
        total,
        handleNextPage,
        handlePrevPage,
        currentPage: Math.floor(offset / usersPerPage) + 1,
        totalPages: Math.ceil(total / usersPerPage),
        refresh: loadUsers
    };
}
