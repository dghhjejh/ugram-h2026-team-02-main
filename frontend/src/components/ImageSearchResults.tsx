import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../services/api';
import { TextSearch, Hash } from 'lucide-react';

const MIN_QUERY_LENGTH = 2;

type Props = {
    query: string;
    isActive: boolean;
    token?: string;
    onClose: () => void;
    selectedIndex: number;
    onSuggestionsChange: (suggestions: string[]) => void;
};

export default function ImageSearchResults({ query, isActive, token, onClose, selectedIndex, onSuggestionsChange }: Props) {
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const requestIdRef = useRef(0);
    const navigate = useNavigate();

    const normalizedQuery = query.trim();
    const isHashtagQuery = normalizedQuery.startsWith('#');
    const partial = isHashtagQuery ? normalizedQuery.slice(1) : normalizedQuery;
    const canFetch = isActive && partial.length >= MIN_QUERY_LENGTH;

    useEffect(() => {
        if (!canFetch) {
            setSuggestions([]);
            onSuggestionsChange([]);
            return;
        }
        requestIdRef.current += 1;
        const requestId = requestIdRef.current;
        const timer = setTimeout(() => {
            const type = isHashtagQuery ? 'hashtag' : 'description';
            apiClient.getAutoCompleteImageMetadata(partial, type, token)
                .then(({ suggestions: result }) => {
                    if (requestIdRef.current === requestId) {
                        setSuggestions(result);
                        onSuggestionsChange(result);
                    }
                })
                .catch(() => {
                    if (requestIdRef.current === requestId) {
                        setSuggestions([]);
                        onSuggestionsChange([]);
                    }
                });
        }, 400);
        return () => clearTimeout(timer);
    }, [canFetch, partial, isHashtagQuery, token]);

    const navigateToSuggestion = (suggestion: string) => {
        onClose();
        if (isHashtagQuery) {
            navigate(`/search/images/${encodeURIComponent(suggestion)}`);
        } else {
            navigate(`/search/description/${encodeURIComponent(suggestion)}`);
        }
    };

    if (partial.length > 0 && partial.length < MIN_QUERY_LENGTH) {
        return (
            <div className="mt-2 px-2 py-1 text-[10px] uppercase tracking-wider text-gray-400 font-bold">
                Type at least {MIN_QUERY_LENGTH} characters
            </div>
        );
    }

    if (partial.length === 0) {
        return (
            <div className="mt-2 px-2 py-1 text-[10px] uppercase tracking-wider text-gray-400 font-bold">
                Type a word or #hashtag
            </div>
        );
    }

    if (canFetch && suggestions.length === 0) {
        return (
            <div className="mt-2 px-2 py-1 text-[10px] uppercase tracking-wider text-gray-400 font-bold">
                No suggestions — press Enter to search
            </div>
        );
    }

    return (
        <ul className="mt-1">
            {suggestions.map((suggestion, index) => (
                <li key={suggestion}>
                    <button
                        type="button"
                        onClick={() => navigateToSuggestion(suggestion)}
                        className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-colors ${
                            index === selectedIndex
                                ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400'
                                : 'hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-800 dark:text-gray-200'
                        }`}
                    >
                        <span className="text-gray-400 text-xs">{isHashtagQuery ? <Hash className="w-4 h-4" /> : <TextSearch className="w-4 h-4" />}</span>
                        {suggestion}
                    </button>
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
