import { useEffect, useState, type SyntheticEvent } from 'react';
import { Heart, MessageCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { FeedItem } from '../../types/api';
import { useAuth } from '../../context/AuthContext';
import { apiClient } from '../../services/api';

interface FeedCardProps {
    item: FeedItem;
    onImageError: (imageId: string, event: SyntheticEvent<HTMLImageElement>) => void;
    onCommentClick: (item: FeedItem) => void;
}

function normalizeHashtag(tag: string): string {
    const cleaned = tag.trim().replace(/^#+/, '');
    return cleaned ? `#${cleaned}` : '';
}

export default function FeedCard({ item, onImageError, onCommentClick }: FeedCardProps) {
    const { token } = useAuth();
    const [showTags, setShowTags] = useState(true);
    const [landscapeAspectRatio, setLandscapeAspectRatio] = useState<number | null>(null);
    const [liked, setLiked] = useState(false);
    const [likeCount, setLikeCount] = useState(item.like_count);
    const [loadingLikeState, setLoadingLikeState] = useState(false);
    const [submittingLike, setSubmittingLike] = useState(false);
    const hashtags = item.hashtags.map(normalizeHashtag).filter(Boolean);
    const mentionNameLookup = new Map((item.mentions ?? []).map((mention) => [mention.id, mention.username]));
    const mentionTags = item.mention_tags ?? [];
    const commentCount = item.comment_count;
    const feedImageSrc = item.feed_view_url || item.view_url || item.image_url;
    const fallbackImageSrc = item.view_url || item.image_url;
    const defaultAvatar = `https://ui-avatars.com/api/?name=${encodeURIComponent(item.owner_username)}&size=150&background=10b981&color=white&font-size=0.4`;

    useEffect(() => {
        let active = true;

        setLiked(false);
        setLikeCount(item.like_count);
        setLoadingLikeState(Boolean(token));

        if (!token) {
            return () => {
                active = false;
            };
        }

        const loadLikeStats = async () => {
            try {
                if (!active) return;
                const likeStats = await apiClient.getImageLikeStats(item.id, token);
                setLiked(likeStats.user_has_liked);
                setLikeCount(likeStats.total_likes);
            } catch {
                if (!active) return;
                setLiked(false);
                setLikeCount(item.like_count);
            } finally {
                if (active) {
                    setLoadingLikeState(false);
                }
            }
        };

        void loadLikeStats();

        return () => {
            active = false;
        };
    }, [item.id, item.like_count, token]);

    const handleLikeClick = async () => {
        if (!token || loadingLikeState || submittingLike) return;

        setSubmittingLike(true);
        try {
            if (liked) {
                await apiClient.unlikeImage(item.id, token);
            } else {
                await apiClient.likeImage(item.id, token);
            }

            const likeStats = await apiClient.getImageLikeStats(item.id, token);
            setLiked(likeStats.user_has_liked);
            setLikeCount(likeStats.total_likes);
        } catch (error) {
            console.error('Failed to update like status', error);
        } finally {
            setSubmittingLike(false);
        }
    };

    const handleAvatarError = (event: SyntheticEvent<HTMLImageElement>) => {
        const img = event.currentTarget;
        const fallbackSrc = img.dataset.fallbackAvatar;
        if (fallbackSrc && img.src !== fallbackSrc) {
            img.src = fallbackSrc;
        }
    };

    const handleMediaLoad = (event: SyntheticEvent<HTMLImageElement>) => {
        const img = event.currentTarget;
        if (img.naturalWidth > img.naturalHeight && img.naturalHeight > 0) {
            setLandscapeAspectRatio(img.naturalWidth / img.naturalHeight);
            return;
        }

        setLandscapeAspectRatio(null);
    };

    return (
        <article className="bg-white dark:bg-gray-900 rounded-2xl shadow-soft-sm border border-gray-100 dark:border-gray-800 overflow-hidden">
            <div className="p-4 flex items-center justify-between gap-3">
                <Link to={`/profile/${item.owner_user_id}`} className="flex items-center gap-3 min-w-0">
                    <img
                        src={item.owner_profile_photo_url || defaultAvatar}
                        data-fallback-avatar={defaultAvatar}
                        alt={item.owner_username}
                        className="w-10 h-10 rounded-full object-cover border border-gray-200 dark:border-gray-700"
                        onError={handleAvatarError}
                    />
                    <div className="min-w-0">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                            {item.owner_username}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                            {new Date(item.created_at).toLocaleString()}
                        </p>
                    </div>
                </Link>
            </div>

            <div
                className="bg-gray-100 dark:bg-gray-800 relative"
                style={{ aspectRatio: landscapeAspectRatio ?? 1 }}
            >
                <img
                    src={feedImageSrc}
                    data-fallback-src={fallbackImageSrc}
                    alt={item.description || 'Feed image'}
                    className="w-full h-full object-contain"
                    loading="lazy"
                    onLoad={handleMediaLoad}
                    onError={(event) => onImageError(item.id, event)}
                />
                {mentionTags.length > 0 && (
                    <>
                        <button
                            type="button"
                            onClick={() => setShowTags((prev) => !prev)}
                            className="absolute left-3 bottom-3 inline-flex items-center gap-1 rounded-full bg-black/70 text-white text-xs font-semibold px-3 py-1 shadow hover:bg-black/80"
                        >
                            {showTags ? 'Hide tags' : 'Show tags'}
                        </button>
                        {showTags &&
                            mentionTags.map((tag) => {
                                const label = mentionNameLookup.get(tag.user_id) ?? `user_${tag.user_id.slice(0, 4)}`;
                                return (
                                    <Link
                                        key={`${item.id}-tag-${tag.user_id}`}
                                        to={`/profile/${tag.user_id}`}
                                        className="absolute z-10 inline-flex items-center gap-1 rounded-full bg-black/75 text-white text-[11px] font-semibold px-2 py-1 hover:bg-black"
                                        style={{
                                            left: `${tag.x_percent}%`,
                                            top: `${tag.y_percent}%`,
                                            transform: 'translate(-50%, -100%)',
                                        }}
                                    >
                                        <span className="w-1.5 h-1.5 rounded-full bg-lime-400" />
                                        @{label}
                                    </Link>
                                );
                            })}
                    </>
                )}
            </div>

            <div className="p-4">
                <p className="text-sm text-gray-900 dark:text-gray-100 leading-6 whitespace-pre-line break-words">
                    <Link
                        to={`/profile/${item.owner_user_id}`}
                        className="font-semibold text-gray-900 dark:text-white hover:underline mr-2"
                    >
                        {item.owner_username}
                    </Link>
                    {item.description ? <span>{item.description}</span> : null}
                    {hashtags.length > 0 && (
                        <>
                            {item.description ? ' ' : null}
                            {hashtags.map((tag, idx) => (
                                <span
                                    key={`${item.id}-tag-${idx}-${tag}`}
                                    className="mr-2 font-medium text-sky-700 dark:text-sky-400"
                                >
                                    {tag}
                                </span>
                            ))}
                        </>
                    )}
                    {!item.description && hashtags.length === 0 ? '—' : null}
                </p>
            </div>

            <div className="px-4 pb-4 flex items-center gap-4 text-gray-600 dark:text-gray-300">
                <button
                    type="button"
                    aria-label={`Like post (${likeCount} likes)`}
                    aria-pressed={liked}
                    onClick={() => void handleLikeClick()}
                    disabled={!token || loadingLikeState || submittingLike}
                    className="inline-flex items-center gap-1.5 justify-center rounded-full px-2 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-50"
                >
                    <Heart size={18} className={liked ? 'text-red-500 fill-red-500' : 'text-gray-600 dark:text-gray-300'} />
                    <span className="text-sm font-medium">{likeCount}</span>
                </button>
                <button
                    type="button"
                    onClick={() => onCommentClick(item)}
                    aria-label={`Comment on post (${commentCount} comments)`}
                    className="inline-flex items-center gap-1.5 justify-center rounded-full px-2 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                    <MessageCircle size={18} />
                    <span className="text-sm font-medium">{commentCount}</span>
                </button>
            </div>
        </article>
    );
}
