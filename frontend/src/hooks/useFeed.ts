import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FeedItem } from '../types/api';
import { apiClient } from '../services/api';

const DEFAULT_FEED_PAGE_SIZE = 12;
const MAX_RETRIES = 2;

function mergeUniqueById(current: FeedItem[], incoming: FeedItem[]): FeedItem[] {
    const unique = new Map<string, FeedItem>();
    for (const item of current) {
        unique.set(item.id, item);
    }
    for (const item of incoming) {
        unique.set(item.id, item);
    }
    return Array.from(unique.values());
}

async function fetchWithRetry<T>(runner: () => Promise<T>, maxRetries: number): Promise<T> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
        try {
            return await runner();
        } catch (error) {
            lastError = error instanceof Error ? error : new Error('Unknown error');
            if (attempt >= maxRetries || lastError.message.includes('401')) {
                break;
            }
        }
    }

    throw lastError ?? new Error('Failed to load feed');
}

export function useFeed(
    token: string | undefined,
    onUnauthorized?: () => void,
    pageSize: number = DEFAULT_FEED_PAGE_SIZE,
) {
    const [items, setItems] = useState<FeedItem[]>([]);
    const [nextCursor, setNextCursor] = useState<string | null>(null);
    const [hasMore, setHasMore] = useState(true);
    const [loadingInitial, setLoadingInitial] = useState(true);
    const [isFetchingNextPage, setIsFetchingNextPage] = useState(false);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleError = useCallback(
        (err: unknown) => {
            const message = err instanceof Error ? err.message : 'Failed to load feed';
            setError(message);
            if (message.includes('401') && onUnauthorized) {
                onUnauthorized();
            }
        },
        [onUnauthorized],
    );

    const loadFirstPage = useCallback(
        async (asRefresh = false) => {
            if (!token) {
                setItems([]);
                setNextCursor(null);
                setHasMore(false);
                setLoadingInitial(false);
                setIsRefreshing(false);
                setError(null);
                return;
            }

            if (asRefresh) {
                setIsRefreshing(true);
            } else {
                setLoadingInitial(true);
            }
            setError(null);

            try {
                const response = await fetchWithRetry(
                    () => apiClient.getFeed(pageSize, undefined, token ?? undefined),
                    MAX_RETRIES,
                );
                setItems(response.items);
                setNextCursor(response.next_cursor);
                setHasMore(response.has_more);
            } catch (err) {
                handleError(err);
            } finally {
                setLoadingInitial(false);
                setIsRefreshing(false);
            }
        },
        [handleError, pageSize, token],
    );

    useEffect(() => {
        void loadFirstPage(false);
    }, [loadFirstPage]);

    const fetchNextPage = useCallback(async () => {
        if (!token || !hasMore || isFetchingNextPage) {
            return;
        }

        setIsFetchingNextPage(true);
        setError(null);

        try {
            const response = await fetchWithRetry(
                () => apiClient.getFeed(pageSize, nextCursor ?? undefined, token ?? undefined),
                MAX_RETRIES,
            );
            setItems((current) => mergeUniqueById(current, response.items));
            setNextCursor(response.next_cursor);
            setHasMore(response.has_more);
        } catch (err) {
            handleError(err);
        } finally {
            setIsFetchingNextPage(false);
        }
    }, [handleError, hasMore, isFetchingNextPage, nextCursor, pageSize, token]);

    const refresh = useCallback(async () => {
        await loadFirstPage(true);
    }, [loadFirstPage]);

    const stableItems = useMemo(() => items, [items]);

    return {
        items: stableItems,
        loadingInitial,
        error,
        hasMore,
        isFetchingNextPage,
        isRefreshing,
        fetchNextPage,
        refresh,
    };
}
