import { useEffect, useMemo, useState, type FormEvent, type SyntheticEvent } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Heart, MessageCircle, MoreHorizontal, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { apiClient } from '../../services/api';
import type { CommentResponse, MentionTagPosition, MentionedUser } from '../../types/api';

export interface ImagePostModalItem {
    id: string;
    owner_user_id: string;
    owner_username: string;
    owner_profile_photo_url: string | null;
    description: string;
    hashtags: string[];
    mentions: MentionedUser[];
    mention_tags: MentionTagPosition[];
    image_url: string;
    view_url: string;
    created_at: string;
    updated_at: string;
    like_count?: number;
    comment_count?: number;
}

export interface ImagePostModalProps {
    item: ImagePostModalItem | null;
    onClose: () => void;
    sizeVariant?: 'default' | 'feed';
    ownerActions?: {
        onEdit?: () => void;
        onDelete?: () => void;
    };
}

function buildAvatarUrl(name: string, size = 48): string {
    return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&size=${size}&background=10b981&color=white&font-size=0.4`;
}

function buildInitialsAvatar(
    firstName?: string | null,
    lastName?: string | null,
    username?: string | null,
    size = 48,
): string {
    const first = (firstName ?? '').trim().charAt(0).toUpperCase();
    const last = (lastName ?? '').trim().charAt(0).toUpperCase();
    const fallback = (username ?? '').trim().slice(0, 2).toUpperCase();
    const initials = `${first}${last}`.trim() || fallback || '?';
    return buildAvatarUrl(initials, size);
}

function handleAvatarError(event: SyntheticEvent<HTMLImageElement>): void {
    const img = event.currentTarget;
    const fallback = img.dataset.fallbackAvatar;
    if (fallback && img.src !== fallback) {
        img.src = fallback;
    }
}

const COMMENTS_PAGE_SIZE = 20;

export default function ImagePostModal({ item, onClose, sizeVariant = 'default', ownerActions }: ImagePostModalProps) {
    const { token } = useAuth();
    const imageId = item?.id ?? null;
    const [liked, setLiked] = useState(false);
    const [likeCount, setLikeCount] = useState(() => item?.like_count ?? 0);
    const [commentCount, setCommentCount] = useState(() => item?.comment_count ?? 0);
    const [comments, setComments] = useState<CommentResponse[]>([]);
    const [commentPhotoUrls, setCommentPhotoUrls] = useState<Record<string, string>>({});
    const [commentDraft, setCommentDraft] = useState('');
    const [menuOpen, setMenuOpen] = useState(false);
    const [showTags, setShowTags] = useState(true);
    const [loadingSocial, setLoadingSocial] = useState(false);
    const [submittingLike, setSubmittingLike] = useState(false);
    const [submittingComment, setSubmittingComment] = useState(false);
    const [actionError, setActionError] = useState<string | null>(null);
    const [commentFetchLimit, setCommentFetchLimit] = useState(COMMENTS_PAGE_SIZE);
    const [fetchingMoreComments, setFetchingMoreComments] = useState(false);

    const mentionNameLookup = useMemo(
        () => new Map((item?.mentions ?? []).map((mention) => [mention.id, mention.username])),
        [item],
    );

    useEffect(() => {
        if (!item || !imageId) return;

        setShowTags(true);
        setMenuOpen(false);
        setActionError(null);
        setLoadingSocial(true);
        setLiked(false);
        setLikeCount(item.like_count ?? 0);
        setCommentCount(item.comment_count ?? 0);
        setComments([]);
        setCommentPhotoUrls({});
        setCommentDraft('');
        setCommentFetchLimit(COMMENTS_PAGE_SIZE);
    }, [imageId]);

    useEffect(() => {
        if (!imageId) return;

        let active = true;
        const initialLoad = commentFetchLimit === COMMENTS_PAGE_SIZE;
        if (initialLoad) {
            setLoadingSocial(true);
        } else {
            setFetchingMoreComments(true);
        }

        const load = async () => {
            if (!token) {
                if (active) {
                    setLoadingSocial(false);
                    setFetchingMoreComments(false);
                }
                return;
            }

            try {
                const commentList = await apiClient.listImageComments(imageId, commentFetchLimit, token);
                if (!active) return;
                setCommentCount(commentList.total);
                setComments(commentList.comments);
            } catch (error) {
                if (active) {
                    setActionError(error instanceof Error ? error.message : 'Failed to load comments');
                }
            } finally {
                if (active) {
                    setLoadingSocial(false);
                    setFetchingMoreComments(false);
                }
            }
        };

        void load();
        return () => {
            active = false;
        };
    }, [imageId, token, commentFetchLimit]);

    useEffect(() => {
        if (!token || comments.length === 0) {
            return;
        }

        let active = true;

        const loadCommentPhotos = async () => {
            const authorIds = Array.from(new Set(comments.map((comment) => comment.user_id)));
            const entries = await Promise.all(
                authorIds.map(async (userId) => {
                    try {
                        const res = await apiClient.getProfilePhotoUrl(userId, token);
                        return [userId, res.signed_url] as const;
                    } catch {
                        return [userId, ''] as const;
                    }
                }),
            );

            if (!active) return;

            const mapped: Record<string, string> = {};
            for (const [userId, url] of entries) {
                if (url) {
                    mapped[userId] = url;
                }
            }
            setCommentPhotoUrls(mapped);
        };

        void loadCommentPhotos();

        return () => {
            active = false;
        };
    }, [comments, token]);

    if (!item) return null;
    const isFeedVariant = sizeVariant === 'feed';

    const handleLike = async () => {
        if (!token || submittingLike) return;
        setSubmittingLike(true);
        setActionError(null);
        const previousLiked = liked;
        const previousLikeCount = likeCount;
        const nextLiked = !liked;
        setLiked(nextLiked);
        setLikeCount((current) => Math.max(0, current + (nextLiked ? 1 : -1)));
        try {
            if (liked) {
                await apiClient.unlikeImage(item.id, token);
            } else {
                await apiClient.likeImage(item.id, token);
            }
        } catch (error) {
            setLiked(previousLiked);
            setLikeCount(previousLikeCount);
            setActionError(error instanceof Error ? error.message : 'Failed to update like');
        } finally {
            setSubmittingLike(false);
        }
    };

    const handleCommentSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!token || submittingComment) return;
        const content = commentDraft.trim();
        if (!content) return;

        setSubmittingComment(true);
        setActionError(null);
        try {
            await apiClient.createImageComment(item.id, { content }, token);
            const commentList = await apiClient.listImageComments(item.id, commentFetchLimit, token);
            setCommentCount(commentList.total);
            setComments(commentList.comments);
            setCommentDraft('');
        } catch (error) {
            setActionError(error instanceof Error ? error.message : 'Failed to post comment');
        } finally {
            setSubmittingComment(false);
        }
    };

    const handleCommentsScroll = (event: SyntheticEvent<HTMLDivElement>) => {
        if (loadingSocial || fetchingMoreComments || !token) return;

        const container = event.currentTarget;
        const reachedBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 8;
        const hasMoreComments = comments.length < commentCount;

        if (!reachedBottom || !hasMoreComments) {
            return;
        }

        setCommentFetchLimit((current) => current + COMMENTS_PAGE_SIZE);
    };

    const commentsSection = (
        <div className="space-y-3 border-t border-gray-200 dark:border-neutral-700 px-4 py-4">
            <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Comments</h3>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                    {loadingSocial ? 'Loading…' : `${commentCount} total`}
                </span>
            </div>

            {actionError && (
                <p className="text-xs text-red-600 dark:text-red-400" role="alert">
                    {actionError}
                </p>
            )}

            <div className="space-y-3 max-h-56 overflow-y-auto pr-1" onScroll={handleCommentsScroll}>
                {comments.length > 0 ? (
                    comments.map((comment) => {
                        const author = comment.author;
                        const authorId = author?.id ?? comment.user_id;
                        const authorName = author?.username ?? `user_${comment.user_id.slice(0, 4)}`;
                        const initialsAvatar = buildInitialsAvatar(author?.first_name, author?.last_name, authorName);
                        const authorAvatar = commentPhotoUrls[authorId] || author?.profile_photo_url || initialsAvatar;

                        return (
                            <div key={comment.id} className="flex gap-3">
                                <Link to={`/profile/${authorId}`} className="shrink-0">
                                    <img
                                        src={authorAvatar}
                                        data-fallback-avatar={initialsAvatar}
                                        onError={handleAvatarError}
                                        alt={authorName}
                                        className="w-8 h-8 rounded-full object-cover"
                                    />
                                </Link>
                                <div className="min-w-0 flex-1 rounded-2xl bg-gray-50 dark:bg-neutral-800 px-3 py-2">
                                    <div className="flex items-center justify-between gap-3">
                                        <Link
                                            to={`/profile/${authorId}`}
                                            className="text-sm font-semibold text-gray-900 dark:text-gray-100 hover:underline truncate"
                                        >
                                            {authorName}
                                        </Link>
                                        <span className="text-[11px] text-gray-400 dark:text-gray-500 shrink-0">
                                            {formatDistanceToNow(new Date(comment.created_at), { addSuffix: true })}
                                        </span>
                                    </div>
                                    <p className="mt-1 text-sm text-gray-700 dark:text-gray-200 whitespace-pre-line break-words">
                                        {comment.content}
                                    </p>
                                </div>
                            </div>
                        );
                    })
                ) : loadingSocial ? null : (
                    <p className="text-sm text-gray-500 dark:text-gray-400">No comments yet.</p>
                )}
                {fetchingMoreComments && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">Loading more comments...</p>
                )}
            </div>
        </div>
    );

    const menuItems = (
        <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-neutral-800 rounded-xl shadow-xl border dark:border-neutral-700 z-50 overflow-hidden">
            <button
                onClick={() => {
                    window.open(item.view_url || item.image_url, '_blank');
                    setMenuOpen(false);
                }}
                className="w-full px-4 py-3 text-sm text-left hover:bg-gray-50 dark:hover:bg-neutral-700 text-gray-900 dark:text-gray-100"
            >
                Open in new tab
            </button>
            {ownerActions?.onEdit && (
                <button
                    onClick={() => {
                        ownerActions.onEdit?.();
                        setMenuOpen(false);
                    }}
                    className="w-full px-4 py-3 text-sm text-left hover:bg-gray-50 dark:hover:bg-neutral-700 text-gray-900 dark:text-gray-100"
                >
                    Edit
                </button>
            )}
            {ownerActions?.onDelete && (
                <button
                    onClick={() => {
                        ownerActions.onDelete?.();
                        setMenuOpen(false);
                    }}
                    className="w-full px-4 py-3 text-sm text-left text-red-500 font-semibold hover:bg-gray-50 dark:hover:bg-neutral-700"
                >
                    Delete
                </button>
            )}
        </div>
    );

    return (
        <div className="fixed inset-0 z-50 bg-black/70" onClick={onClose}>
            <div className="hidden md:flex items-center justify-center w-full h-full px-4">
                <button
                    className="absolute top-4 right-4 text-white/80 hover:text-white z-50"
                    onClick={onClose}
                    aria-label="Close"
                    type="button"
                >
                    <X size={24} />
                </button>

                <div
                    className={
                        isFeedVariant
                            ? 'relative flex w-full max-w-3xl max-h-[75vh] bg-white dark:bg-neutral-900 rounded-xl overflow-hidden'
                            : 'relative flex w-full max-w-5xl max-h-[85vh] bg-white dark:bg-neutral-900 rounded-xl overflow-hidden'
                    }
                    onClick={(event) => event.stopPropagation()}
                >
                    <div
                        className={
                            isFeedVariant
                                ? 'relative bg-black flex items-center justify-center flex-shrink-0 w-[66%] min-h-[520px]'
                                : 'relative bg-black flex items-center justify-center flex-shrink-0 w-[62%] min-h-[540px]'
                        }
                    >
                        <img
                            src={item.view_url || item.image_url}
                            alt={item.description || 'Image'}
                            className={isFeedVariant ? 'w-full h-full object-contain max-h-[88vh]' : 'w-full h-full object-contain max-h-[94vh]'}
                        />
                        {item.mention_tags.length > 0 && (
                            <>
                                <button
                                    type="button"
                                    className="absolute left-3 bottom-3 inline-flex items-center gap-1 rounded-full bg-black/70 text-white text-xs font-semibold px-3 py-1 shadow hover:bg-black/80 z-10"
                                    onClick={() => setShowTags((prev) => !prev)}
                                >
                                    {showTags ? 'Hide tags' : 'Show tags'}
                                </button>
                                {showTags &&
                                    item.mention_tags.map((tag) => (
                                        <Link
                                            key={`feed-modal-tag-${tag.user_id}`}
                                            to={`/profile/${tag.user_id}`}
                                            className="absolute z-10 inline-flex items-center gap-1 rounded-full bg-black/75 text-white text-xs font-semibold px-2 py-1 hover:bg-black"
                                            style={{
                                                left: `${tag.x_percent}%`,
                                                top: `${tag.y_percent}%`,
                                                transform: 'translate(-50%, -100%)',
                                            }}
                                        >
                                            <span className="w-1.5 h-1.5 rounded-full bg-lime-400" />
                                            @{mentionNameLookup.get(tag.user_id) ?? `user_${tag.user_id.slice(0, 4)}`}
                                        </Link>
                                    ))}
                            </>
                        )}
                    </div>

                    <div
                        className={
                            isFeedVariant
                                ? 'flex flex-col w-[34%] min-w-[300px] border-l border-gray-200 dark:border-neutral-700'
                                : 'flex flex-col w-[38%] min-w-[320px] border-l border-gray-200 dark:border-neutral-700'
                        }
                    >
                        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-neutral-700">
                            <div className="flex items-center gap-3 min-w-0">
                                <img src={item.owner_profile_photo_url || buildAvatarUrl(item.owner_username, 64)} alt={item.owner_username} className="w-8 h-8 rounded-full object-cover" />
                                <Link
                                    to={`/profile/${item.owner_user_id}`}
                                    className="text-sm font-semibold text-gray-900 dark:text-gray-100 hover:underline truncate"
                                >
                                    {item.owner_username}
                                </Link>
                            </div>
                            <div className="relative">
                                <button
                                    onClick={() => setMenuOpen((prev) => !prev)}
                                    className="text-gray-900 dark:text-gray-100 hover:text-gray-500"
                                    aria-label="Options"
                                    type="button"
                                >
                                    <MoreHorizontal size={20} />
                                </button>
                                {menuOpen && menuItems}
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto px-4 py-4">
                            {item.description && (
                                <div className="flex gap-3 mb-4">
                                    <img src={item.owner_profile_photo_url || buildAvatarUrl(item.owner_username, 64)} alt={item.owner_username} className="w-8 h-8 rounded-full object-cover" />
                                    <div className="text-sm text-gray-900 dark:text-gray-100">
                                        <Link to={`/profile/${item.owner_user_id}`} className="font-semibold hover:underline mr-1">
                                            {item.owner_username}
                                        </Link>
                                        <span className="whitespace-pre-line">{item.description}</span>
                                        {item.hashtags.length > 0 && (
                                            <span className="text-blue-500 dark:text-blue-400">
                                                {' '}
                                                {item.hashtags.map((tag) => `#${tag}`).join(' ')}
                                            </span>
                                        )}
                                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                                            {formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}
                                        </p>
                                    </div>
                                </div>
                            )}

                            {commentsSection}
                        </div>

                        <div className="border-t border-gray-200 dark:border-neutral-700 px-4 pt-3 pb-1">
                            <div className="mb-2 flex items-center gap-4 text-gray-600 dark:text-gray-300">
                                <button
                                    onClick={() => void handleLike()}
                                    className="inline-flex items-center gap-1.5 hover:opacity-60 disabled:opacity-50"
                                    type="button"
                                    aria-label={`Like post (${likeCount} likes)`}
                                    aria-pressed={liked}
                                    disabled={submittingLike || loadingSocial}
                                >
                                    <Heart size={24} className={liked ? 'text-red-500 fill-red-500' : 'text-gray-900 dark:text-gray-100'} />
                                    <span className="text-sm font-medium">{likeCount}</span>
                                </button>
                                <button
                                    className="inline-flex items-center gap-1.5 hover:opacity-60"
                                    aria-label={`Comment on post (${commentCount} comments)`}
                                    type="button"
                                >
                                    <MessageCircle size={24} className="text-gray-900 dark:text-gray-100" />
                                    <span className="text-sm font-medium">{commentCount}</span>
                                </button>
                            </div>
                        </div>

                        <form
                            className="border-t border-gray-200 dark:border-neutral-700 px-4 py-3 flex items-center gap-3"
                            onSubmit={(event) => void handleCommentSubmit(event)}
                        >
                            <input
                                type="text"
                                placeholder="Add a comment..."
                                className="flex-1 text-sm bg-transparent outline-none text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
                                value={commentDraft}
                                onChange={(event) => setCommentDraft(event.target.value)}
                                disabled={submittingComment || loadingSocial}
                            />
                            <button
                                type="submit"
                                className="text-sm font-semibold text-blue-500 disabled:opacity-50"
                                disabled={submittingComment || !commentDraft.trim()}
                            >
                                {submittingComment ? 'Posting…' : 'Post'}
                            </button>
                        </form>
                    </div>
                </div>
            </div>

            <div className="flex md:hidden flex-col w-full h-full bg-white dark:bg-black" onClick={(event) => event.stopPropagation()}>
                <div className="flex items-center justify-between px-2 py-3 border-b border-gray-200 dark:border-neutral-800 flex-shrink-0">
                    <button onClick={onClose} className="p-1 text-gray-900 dark:text-gray-100" type="button">
                        <X size={24} />
                    </button>
                    <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100">Post</h1>
                    <div className="w-9" />
                </div>

                <div className="flex-1 overflow-y-auto">
                    <div className="flex items-center justify-between px-3 py-2.5">
                        <div className="flex items-center gap-3 min-w-0">
                            <img src={item.owner_profile_photo_url || buildAvatarUrl(item.owner_username, 64)} alt={item.owner_username} className="w-9 h-9 rounded-full object-cover" />
                            <Link to={`/profile/${item.owner_user_id}`} className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
                                {item.owner_username}
                            </Link>
                        </div>
                        <div className="relative">
                            <button
                                onClick={() => setMenuOpen((prev) => !prev)}
                                className="text-gray-900 dark:text-gray-100 p-1"
                                aria-label="Options"
                                type="button"
                            >
                                <MoreHorizontal size={20} />
                            </button>
                            {menuOpen && menuItems}
                        </div>
                    </div>

                    <div className="relative bg-black w-full">
                        <img
                            src={item.view_url || item.image_url}
                            alt={item.description || 'Image'}
                            className={isFeedVariant ? 'w-full object-contain max-h-[90vh]' : 'w-full object-contain max-h-[76vh]'}
                        />
                        {item.mention_tags.length > 0 && (
                            <>
                                <button
                                    type="button"
                                    className="absolute left-3 bottom-3 inline-flex items-center gap-1 rounded-full bg-black/70 text-white text-xs font-semibold px-3 py-1 shadow hover:bg-black/80 z-10"
                                    onClick={() => setShowTags((prev) => !prev)}
                                >
                                    {showTags ? 'Hide tags' : 'Show tags'}
                                </button>
                                {showTags &&
                                    item.mention_tags.map((tag) => (
                                        <Link
                                            key={`feed-modal-mobile-tag-${tag.user_id}`}
                                            to={`/profile/${tag.user_id}`}
                                            className="absolute z-10 inline-flex items-center gap-1 rounded-full bg-black/75 text-white text-[11px] font-semibold px-2 py-1 hover:bg-black"
                                            style={{
                                                left: `${tag.x_percent}%`,
                                                top: `${tag.y_percent}%`,
                                                transform: 'translate(-50%, -100%)',
                                            }}
                                        >
                                            <span className="w-1.5 h-1.5 rounded-full bg-lime-400" />
                                            @{mentionNameLookup.get(tag.user_id) ?? `user_${tag.user_id.slice(0, 4)}`}
                                        </Link>
                                    ))}
                            </>
                        )}
                    </div>

                    <div className="px-3 pt-3 pb-1">
                        {item.description && (
                            <div className="flex gap-3 mb-4">
                                <img src={item.owner_profile_photo_url || buildAvatarUrl(item.owner_username, 64)} alt={item.owner_username} className="w-8 h-8 rounded-full object-cover" />
                                <div className="text-sm text-gray-900 dark:text-gray-100">
                                    <Link to={`/profile/${item.owner_user_id}`} className="font-semibold hover:underline mr-1">
                                        {item.owner_username}
                                    </Link>
                                    <span className="whitespace-pre-line">{item.description}</span>
                                    {item.hashtags.length > 0 && (
                                        <span className="text-blue-500 dark:text-blue-400">
                                            {' '}
                                            {item.hashtags.map((tag) => `#${tag}`).join(' ')}
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}

                        {commentsSection}
                    </div>

                    <div className="px-3 pt-1 pb-1">
                        <div className="mb-2 flex items-center gap-4 text-gray-600 dark:text-gray-300">
                            <button
                                onClick={() => void handleLike()}
                                className="inline-flex items-center gap-1.5 hover:opacity-60 disabled:opacity-50"
                                type="button"
                                aria-label={`Like post (${likeCount} likes)`}
                                aria-pressed={liked}
                                disabled={submittingLike || loadingSocial}
                            >
                                <Heart size={24} className={liked ? 'text-red-500 fill-red-500' : 'text-gray-900 dark:text-gray-100'} />
                                <span className="text-sm font-medium">{likeCount}</span>
                            </button>
                            <button
                                className="inline-flex items-center gap-1.5 hover:opacity-60"
                                aria-label={`Comment on post (${commentCount} comments)`}
                                type="button"
                            >
                                <MessageCircle size={24} className="text-gray-900 dark:text-gray-100" />
                                <span className="text-sm font-medium">{commentCount}</span>
                            </button>
                        </div>
                    </div>
                </div>

                <form
                    className="border-t border-gray-200 dark:border-neutral-700 px-4 py-3 flex items-center gap-3"
                    onSubmit={(event) => void handleCommentSubmit(event)}
                >
                    <input
                        type="text"
                        placeholder="Add a comment..."
                        className="flex-1 text-sm bg-transparent outline-none text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
                        value={commentDraft}
                        onChange={(event) => setCommentDraft(event.target.value)}
                        disabled={submittingComment || loadingSocial}
                    />
                    <button
                        type="submit"
                        className="text-sm font-semibold text-blue-500 disabled:opacity-50"
                        disabled={submittingComment || !commentDraft.trim()}
                    >
                        {submittingComment ? 'Posting…' : 'Post'}
                    </button>
                </form>
            </div>
        </div>
    );
}


