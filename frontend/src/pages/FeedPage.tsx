import { useEffect, useRef, useState, type SyntheticEvent } from 'react';
import FeedCard from '../components/feed/FeedCard';
import FeedEmptyState from '../components/feed/FeedEmptyState';
import FeedErrorBanner from '../components/feed/FeedErrorBanner';
import FeedHeader from '../components/feed/FeedHeader';
import FeedPaginationControls from '../components/feed/FeedPaginationControls';
import FeedSkeleton from '../components/feed/FeedSkeleton';
import TrendingKeywordsPanel from '../components/feed/TrendingKeywordsPanel';
import Header from '../components/profile/Header';
import ImagePostModal from '../components/profile/ImagePostModal';
import { useAuth } from '../context/AuthContext';
import { useFeed } from '../hooks/useFeed';
import { useTrendingKeywords } from '../hooks/useTrendingKeywords';
import type { FeedItem } from '../types/api';

const FEED_PAGE_SIZE = 12;
const TREND_LIMIT = 5;

export default function FeedPage() {
    const { token, loading: authLoading, logout } = useAuth();
    const {
        data: trendingKeywords,
        loading: trendingLoading,
        error: trendingError,
    } = useTrendingKeywords(token, TREND_LIMIT, 'today');
    const {
        items,
        loadingInitial,
        error,
        hasMore,
        isFetchingNextPage,
        fetchNextPage,
        refresh,
    } = useFeed(token, logout, FEED_PAGE_SIZE);

    const sentinelRef = useRef<HTMLDivElement | null>(null);
    const refreshedImageIds = useRef<Set<string>>(new Set());
    const [selectedItem, setSelectedItem] = useState<FeedItem | null>(null);

    useEffect(() => {
        const node = sentinelRef.current;
        if (!node || !hasMore) {
            return;
        }

        const observer = new IntersectionObserver(
            (entries) => {
                const [entry] = entries;
                if (entry.isIntersecting && !isFetchingNextPage) {
                    void fetchNextPage();
                }
            },
            { rootMargin: '400px 0px' },
        );

        observer.observe(node);
        return () => observer.disconnect();
    }, [hasMore, isFetchingNextPage, fetchNextPage]);

    const handleImageError = (imageId: string, event: SyntheticEvent<HTMLImageElement>) => {
        const img = event.currentTarget;
        if (img.dataset.fallbackApplied === 'true') {
            return;
        }

        const fallbackSrc = img.dataset.fallbackSrc;
        if (fallbackSrc && fallbackSrc !== img.src) {
            img.dataset.fallbackApplied = 'true';
            img.src = fallbackSrc;
        }

        // Signed URLs can expire; refresh feed data once per failed image.
        if (!refreshedImageIds.current.has(imageId)) {
            refreshedImageIds.current.add(imageId);
            void refresh();
        }
    };

    if (authLoading || (loadingInitial && items.length === 0)) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-950 dark:text-gray-100 fade-in">
                <Header appName="uGram" defaultSearchType="images" />
                <main className="container-custom py-8">
                    <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-[minmax(0,1fr)_280px] xl:grid-cols-[minmax(0,2fr)_320px]">
                        <div className="max-w-2xl md:max-w-none">
                            <FeedSkeleton />
                        </div>
                        <div className="hidden md:block">
                            <div className="h-80 rounded-[28px] bg-gray-100/70 dark:bg-gray-900/60 animate-pulse" />
                        </div>
                    </div>
                </main>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 dark:text-gray-100 fade-in">
            <Header appName="uGram" defaultSearchType="images" />

            <main className="container-custom py-8">
                <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-[minmax(0,1fr)_280px] md:items-start xl:grid-cols-[minmax(0,2fr)_320px]">
                    <div className="max-w-2xl md:max-w-none">
                        <FeedHeader count={items.length} />

                        {error && <FeedErrorBanner message={error} onRetry={() => void refresh()} />}

                        {items.length === 0 ? (
                            <FeedEmptyState />
                        ) : (
                            <div className="space-y-6">
                                {items.map((item) => (
                                    <FeedCard
                                        key={item.id}
                                        item={item}
                                        onImageError={handleImageError}
                                        onCommentClick={setSelectedItem}
                                    />
                                ))}
                            </div>
                        )}

                        <div ref={sentinelRef} className="h-1" aria-hidden="true" />

                        <FeedPaginationControls
                            hasMore={hasMore}
                            isFetchingNextPage={isFetchingNextPage}
                            onLoadMore={() => void fetchNextPage()}
                        />
                    </div>

                    <div className="md:sticky md:top-28">
                        <TrendingKeywordsPanel
                            hashtags={trendingKeywords?.hashtags ?? []}
                            descriptionKeywords={trendingKeywords?.description_keywords ?? []}
                            loading={trendingLoading}
                            error={trendingError}
                        />
                    </div>
                </div>
            </main>

            <ImagePostModal key={selectedItem?.id ?? 'closed'} item={selectedItem} onClose={() => setSelectedItem(null)} />
        </div>
    );
}
