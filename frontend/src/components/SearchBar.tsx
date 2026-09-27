import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import PeopleSearchResults from './PeopleSearchResults';
import ImageSearchResults from './ImageSearchResults';

type SearchType = 'people' | 'images';

type SearchBarProps = {
    value?: string;
    onChange?: (value: string) => void;
    onExpandChange?: (expanded: boolean) => void;
    defaultSearchType?: SearchType;
};

export default function SearchBar({
    value,
    onChange,
    onExpandChange,
    defaultSearchType = 'people',
}: SearchBarProps = {}) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [internalQuery, setInternalQuery] = useState('');
    const [searchType, setSearchType] = useState<SearchType>(defaultSearchType);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const [imageSuggestions, setImageSuggestions] = useState<string[]>([]);
    const inputRef = useRef<HTMLInputElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const onExpandChangeRef = useRef(onExpandChange);
    const navigate = useNavigate();
    const { token } = useAuth();

    useEffect(() => {
        onExpandChangeRef.current = onExpandChange;
    });

    const isControlled = value !== undefined && onChange !== undefined;
    const query = isControlled ? value : internalQuery;
    const setQuery = isControlled ? onChange : setInternalQuery;

    useEffect(() => {
        if (!query.trim()) {
            setSearchType(defaultSearchType);
            setSelectedIndex(-1);
        }
    }, [defaultSearchType, query]);

    const handleQueryChange = (nextValue: string) => {
        setQuery(nextValue);
        setSelectedIndex(-1);
        if (nextValue.startsWith('#')) {
            setSearchType('images');
        }
    };

    const setExpanded = useCallback((expanded: boolean) => {
        setIsExpanded(expanded);
        onExpandChangeRef.current?.(expanded);
    }, []);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setExpanded(false);
            }
        }

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [setExpanded]);

    const handleKeyDown = (event: React.KeyboardEvent) => {
        if (searchType !== 'images' || imageSuggestions.length === 0) {
            return;
        }

        if (event.key === 'ArrowDown') {
            event.preventDefault();
            setSelectedIndex((index) => Math.min(index + 1, imageSuggestions.length - 1));
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            setSelectedIndex((index) => Math.max(index - 1, -1));
        } else if (event.key === 'Enter' && selectedIndex >= 0) {
            event.preventDefault();
            const suggestion = imageSuggestions[selectedIndex];
            setExpanded(false);
            inputRef.current?.blur();
            const isHashtag = query.trim().startsWith('#');
            navigate(
                isHashtag
                    ? `/search/images/${encodeURIComponent(suggestion)}`
                    : `/search/description/${encodeURIComponent(suggestion)}`,
            );
        } else if (event.key === 'Escape') {
            setExpanded(false);
        }
    };

    const handleSearch = (event: React.FormEvent) => {
        event.preventDefault();
        if (!query.trim()) {
            return;
        }

        if (query.startsWith('#')) {
            const hashtag = query.slice(1).trim();
            if (hashtag.length > 0) {
                setExpanded(false);
                inputRef.current?.blur();
                navigate(`/search/images/${encodeURIComponent(hashtag)}`, { replace: false });
                return;
            }
        }

        setExpanded(false);
        inputRef.current?.blur();
        if (searchType === 'people') {
            navigate(`/search?q=${encodeURIComponent(query.trim())}`);
        } else {
            navigate(`/search/description/${encodeURIComponent(query.trim())}`);
        }
    };

    return (
        <div
            ref={containerRef}
            className={`relative ml-auto origin-right transition-all duration-300 ease-in-out flex-1 min-w-0 ${
                isExpanded ? 'w-full' : 'w-10 lg:w-48'
            }`}
        >
            <form onSubmit={handleSearch} className="relative flex items-center h-10">
                <div className="absolute left-3 text-gray-400 pointer-events-none">
                    <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <circle cx="11" cy="11" r="8" />
                        <path d="m21 21-4.35-4.35" />
                    </svg>
                </div>

                <input
                    ref={inputRef}
                    type="text"
                    placeholder={isExpanded ? (searchType === 'people' ? 'Search people...' : 'Search words or #hashtags...') : 'Search'}
                    value={query}
                    onChange={(event) => handleQueryChange(event.target.value)}
                    onFocus={() => setExpanded(true)}
                    onKeyDown={handleKeyDown}
                    className={`h-full w-full pl-10 pr-4 py-2 bg-gray-100 dark:bg-gray-800 border-none rounded-full text-sm focus:ring-2 focus:ring-indigo-500/50 outline-none transition-all ${
                        !isExpanded && 'lg:cursor-pointer placeholder:text-transparent lg:placeholder:text-gray-400'
                    }`}
                />

                {isExpanded ? (
                    <div className="absolute top-12 left-0 right-0 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-xl p-2 z-[60] fade-in animate-in slide-in-from-top-2 duration-200">
                        <div className="flex gap-1 p-1 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
                            <button
                                type="button"
                                onClick={() => setSearchType('people')}
                                className={`flex-1 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                                    searchType === 'people'
                                        ? 'bg-white dark:bg-gray-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
                                        : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                                }`}
                            >
                                People
                            </button>
                            <button
                                type="button"
                                onClick={() => setSearchType('images')}
                                className={`flex-1 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                                    searchType === 'images'
                                        ? 'bg-white dark:bg-gray-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
                                        : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                                }`}
                            >
                                Images
                            </button>
                        </div>

                        {searchType === 'people' ? (
                            <PeopleSearchResults
                                query={query}
                                isActive={isExpanded}
                                token={token ?? undefined}
                                onClose={() => setExpanded(false)}
                            />
                        ) : null}

                        {searchType === 'images' ? (
                            <ImageSearchResults
                                query={query}
                                isActive={isExpanded}
                                token={token ?? undefined}
                                onClose={() => setExpanded(false)}
                                selectedIndex={selectedIndex}
                                onSuggestionsChange={(suggestions) => {
                                    setImageSuggestions(suggestions);
                                    setSelectedIndex(-1);
                                }}
                            />
                        ) : null}
                    </div>
                ) : null}
            </form>
        </div>
    );
}
