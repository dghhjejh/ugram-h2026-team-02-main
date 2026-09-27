import { Link } from 'react-router-dom';
import type { TrendingKeywordItem } from '../../types/api';

interface TrendingKeywordsPanelProps {
    hashtags: TrendingKeywordItem[];
    descriptionKeywords: TrendingKeywordItem[];
    loading: boolean;
    error: string | null;
}

interface TrendRowProps {
    item: TrendingKeywordItem;
    href: string;
    label: string;
}

function TrendRow({ item, href, label }: TrendRowProps) {
    return (
        <Link
            to={href}
            className="block rounded-2xl px-4 py-3 transition-colors hover:bg-gray-50 dark:hover:bg-gray-900"
        >
            <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-gray-900 dark:text-white">
                    {label}
                </p>
                <span className="shrink-0 text-xs text-gray-500 dark:text-gray-400">
                    {item.count} searches
                </span>
            </div>
        </Link>
    );
}

export default function TrendingKeywordsPanel({
    hashtags,
    descriptionKeywords,
    loading,
    error,
}: TrendingKeywordsPanelProps) {
    return (
        <aside className="rounded-[28px] border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-950">
            <div className="border-b border-gray-200 px-5 py-4 dark:border-gray-800">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-600 dark:text-sky-300">
                    Right Now
                </p>
                <h2 className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                    Most Searched Today
                </h2>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    Most searched hashtags and keywords today.
                </p>
            </div>

            {loading ? (
                <div className="space-y-3 p-5">
                    <div className="h-16 animate-pulse rounded-2xl bg-gray-100 dark:bg-gray-900" />
                    <div className="h-16 animate-pulse rounded-2xl bg-gray-100 dark:bg-gray-900" />
                    <div className="h-16 animate-pulse rounded-2xl bg-gray-100 dark:bg-gray-900" />
                </div>
            ) : error ? (
                <div className="p-5">
                    <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-950/40 dark:text-red-300">
                        {error}
                    </div>
                </div>
            ) : (
                <div className="py-2">
                    {hashtags.length === 0 && descriptionKeywords.length === 0 ? (
                        <div className="px-5 py-6 text-sm text-gray-500 dark:text-gray-400">
                            No searched trends yet. Search an image keyword or hashtag from the home feed to populate this list.
                        </div>
                    ) : (
                        <>
                            <section className="border-b border-gray-100 px-5 py-4 dark:border-gray-900">
                                <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
                                    Most searched hashtags
                                </h3>
                                {hashtags.length === 0 ? (
                                    <p className="text-sm text-gray-500 dark:text-gray-400">No hashtag searches yet.</p>
                                ) : (
                                    <div className="space-y-1">
                                        {hashtags.map((item) => (
                                            <TrendRow
                                                key={`hashtag-${item.keyword}`}
                                                item={item}
                                                href={`/search/images/${encodeURIComponent(item.keyword)}`}
                                                label={`#${item.keyword}`}
                                            />
                                        ))}
                                    </div>
                                )}
                            </section>
                            <section className="px-5 py-4">
                                <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
                                    Most searched keywords
                                </h3>
                                {descriptionKeywords.length === 0 ? (
                                    <p className="text-sm text-gray-500 dark:text-gray-400">No keyword searches yet.</p>
                                ) : (
                                    <div className="space-y-1">
                                        {descriptionKeywords.map((item) => (
                                            <TrendRow
                                                key={`keyword-${item.keyword}`}
                                                item={item}
                                                href={`/search/description/${encodeURIComponent(item.keyword)}`}
                                                label={item.keyword}
                                            />
                                        ))}
                                    </div>
                                )}
                            </section>
                        </>
                    )}
                </div>
            )}
        </aside>
    );
}
