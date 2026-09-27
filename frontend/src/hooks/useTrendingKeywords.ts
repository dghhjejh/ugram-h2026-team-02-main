import { useEffect, useState } from 'react';
import type { TrendingKeywordsResponse } from '../types/api';
import { apiClient } from '../services/api';

const DEFAULT_TREND_LIMIT = 8;
type TrendWindow = 'all_time' | 'today';

export function useTrendingKeywords(
    token: string | undefined,
    limit: number = DEFAULT_TREND_LIMIT,
    window: TrendWindow = 'all_time',
) {
    const [data, setData] = useState<TrendingKeywordsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;

        if (!token) {
            setData(null);
            setError(null);
            setLoading(false);
            return () => {
                cancelled = true;
            };
        }

        setLoading(true);
        setError(null);

        apiClient.getTrendingKeywords(limit, window, token)
            .then((response) => {
                if (cancelled) {
                    return;
                }
                setData(response);
                setLoading(false);
            })
            .catch((err: unknown) => {
                if (cancelled) {
                    return;
                }
                const message = err instanceof Error ? err.message : 'Failed to load trends';
                setError(message);
                setLoading(false);
            });

        return () => {
            cancelled = true;
        };
    }, [limit, token, window]);

    return {
        data,
        loading,
        error,
    };
}
