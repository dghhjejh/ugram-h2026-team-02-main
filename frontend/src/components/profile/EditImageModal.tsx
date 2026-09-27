import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type MouseEvent as ReactMouseEvent } from 'react';
import { X } from 'lucide-react';
import type { Image, MentionTagPosition, UserProfile } from '../../types/api';
import { apiClient } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

type EditImageModalProps = {
    image: Image;
    open: boolean;
    onCancel: () => void;
    onSubmit: (
        description: string,
        hashtags: string,
        mentionsUserIds: string[],
        mentionTags: MentionTagPosition[],
    ) => Promise<void>;
    updating: boolean;
    updateError: string | null;
};

type MentionOption = Pick<UserProfile, 'id' | 'username' | 'profile_photo_url' | 'first_name' | 'last_name'>;
type TagPosition = { xPercent: number; yPercent: number };
type EditableMention = MentionOption & { tagPosition?: TagPosition };

const MIN_MENTION_QUERY = 2;

function buildInitialMentions(image: Image): EditableMention[] {
    const mentionMap = new Map(image.mentions.map((mention) => [mention.id, mention]));

    return image.mentions_user_ids.map((userId) => {
        const mention = mentionMap.get(userId);
        const tagPosition = image.mention_tags.find((tag) => tag.user_id === userId);
        return {
            id: userId,
            username: mention?.username ?? `user_${userId.slice(0, 4)}`,
            profile_photo_url: mention?.profile_photo_url ?? null,
            first_name: mention?.first_name ?? '',
            last_name: mention?.last_name ?? '',
            tagPosition: tagPosition
                ? {
                    xPercent: tagPosition.x_percent,
                    yPercent: tagPosition.y_percent,
                }
                : undefined,
        };
    });
}

export default function EditImageModal({
    image,
    open,
    onCancel,
    onSubmit,
    updating,
    updateError,
}: EditImageModalProps) {
    const { token } = useAuth();
    const [descriptionInput, setDescriptionInput] = useState('');
    const [hashtagsInput, setHashtagsInput] = useState('');
    const [selectedMentions, setSelectedMentions] = useState<EditableMention[]>([]);
    const [mentionQuery, setMentionQuery] = useState('');
    const [suggestions, setSuggestions] = useState<MentionOption[]>([]);
    const [mentionsLoading, setMentionsLoading] = useState(false);
    const [mentionsError, setMentionsError] = useState<string | null>(null);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [tagPopover, setTagPopover] = useState<TagPosition | null>(null);
    const mentionInputRef = useRef<HTMLInputElement | null>(null);
    const modalBodyRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        if (!open) {
            return;
        }
        setDescriptionInput(image.description || '');
        setHashtagsInput(image.hashtags.join(' '));
        setSelectedMentions(buildInitialMentions(image));
        setMentionQuery('');
        setSuggestions([]);
        setMentionsLoading(false);
        setMentionsError(null);
        setShowSuggestions(false);
        setTagPopover(null);
    }, [image, open]);

    const loadSuggestions = useCallback(
        async (query: string) => {
            const normalizedQuery = query.trim().replace(/^@+/, '');
            if (normalizedQuery.length < MIN_MENTION_QUERY || !token) {
                setSuggestions([]);
                setMentionsLoading(false);
                setMentionsError(token ? null : 'Sign in again to edit mention tags.');
                return;
            }

            setMentionsLoading(true);
            setMentionsError(null);

            try {
                const users = await apiClient.searchUsers(normalizedQuery, 8, token);
                const filtered = users.filter((user) => !selectedMentions.some((mention) => mention.id === user.id));
                setSuggestions(filtered);
                if (filtered.length === 0) {
                    setMentionsError('No users match that username yet.');
                }
            } catch (error) {
                setMentionsError(error instanceof Error ? error.message : 'Failed to load suggestions');
            } finally {
                setMentionsLoading(false);
            }
        },
        [selectedMentions, token],
    );

    useEffect(() => {
        if (!open || !showSuggestions) {
            return;
        }

        const sanitizedQuery = mentionQuery.trim().replace(/^@+/, '');
        if (!sanitizedQuery) {
            setSuggestions([]);
            setMentionsLoading(false);
            return;
        }

        const timeoutId = window.setTimeout(() => {
            void loadSuggestions(sanitizedQuery);
        }, 250);

        return () => {
            window.clearTimeout(timeoutId);
        };
    }, [loadSuggestions, mentionQuery, open, showSuggestions]);

    useEffect(() => {
        if (!open) {
            return;
        }

        const handleClickOutside = (event: MouseEvent) => {
            if (!(event.target instanceof Node) || modalBodyRef.current?.contains(event.target)) {
                return;
            }
            setShowSuggestions(false);
            setTagPopover(null);
            setMentionQuery('');
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [open]);

    const positionedMentions = useMemo(
        () => selectedMentions.filter((mention) => mention.tagPosition),
        [selectedMentions],
    );

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        onSubmit(
            descriptionInput.trim(),
            hashtagsInput,
            selectedMentions.map((mention) => mention.id),
            positionedMentions.map((mention) => ({
                user_id: mention.id,
                x_percent: mention.tagPosition!.xPercent,
                y_percent: mention.tagPosition!.yPercent,
            })),
        );
    };

    const handleImageClick = (event: ReactMouseEvent<HTMLImageElement>) => {
        const bounds = event.currentTarget.getBoundingClientRect();
        if (!bounds.width || !bounds.height) {
            return;
        }

        const clamp = (value: number) => Math.min(Math.max(value, 8), 92);
        const xPercent = clamp(((event.clientX - bounds.left) / bounds.width) * 100);
        const yPercent = clamp(((event.clientY - bounds.top) / bounds.height) * 100);

        setTagPopover({ xPercent, yPercent });
        setShowSuggestions(true);
        setMentionQuery('');
        setSuggestions([]);
        setMentionsError(null);
        window.setTimeout(() => {
            mentionInputRef.current?.focus();
        }, 0);
    };

    const handleMentionSelect = (user: MentionOption) => {
        setSelectedMentions((prev) => {
            const existing = prev.find((mention) => mention.id === user.id);
            const nextMention: EditableMention = {
                ...user,
                tagPosition: tagPopover
                    ? {
                        xPercent: tagPopover.xPercent,
                        yPercent: tagPopover.yPercent,
                    }
                    : existing?.tagPosition,
            };

            if (existing) {
                return prev.map((mention) => (mention.id === user.id ? nextMention : mention));
            }

            return [...prev, nextMention];
        });
        setMentionQuery('');
        setSuggestions([]);
        setMentionsError(null);
        setShowSuggestions(false);
        setTagPopover(null);
    };

    const handleMentionRemove = (userId: string) => {
        setSelectedMentions((prev) => prev.filter((mention) => mention.id !== userId));
    };

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center px-4">
            <div
                ref={modalBodyRef}
                className="w-full max-w-xl bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden"
            >
                <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Edit Image</h3>
                    <button
                        className="text-gray-500 hover:text-gray-800 dark:text-gray-300 dark:hover:text-white text-lg"
                        onClick={onCancel}
                        aria-label="Close"
                    >
                        <X />
                    </button>
                </div>
                <form onSubmit={handleSubmit}>
                    <div className="p-5 space-y-4">
                        <div className="relative">
                            <img
                                src={image.view_url || image.image_url}
                                alt={image.description || 'Image'}
                                className="w-full rounded-xl border border-gray-100 dark:border-gray-800 max-h-72 object-cover cursor-crosshair"
                                onClick={handleImageClick}
                            />
                            {positionedMentions.map((mention) => (
                                <button
                                    key={`edit-image-tag-${mention.id}`}
                                    type="button"
                                    className="absolute z-10 inline-flex items-center gap-1 rounded-full bg-black/75 text-white text-xs font-semibold px-2 py-1 pr-1"
                                    style={{
                                        left: `${mention.tagPosition!.xPercent}%`,
                                        top: `${mention.tagPosition!.yPercent}%`,
                                        transform: 'translate(-50%, -100%)',
                                    }}
                                    onClick={(event) => {
                                        event.stopPropagation();
                                        handleMentionRemove(mention.id);
                                    }}
                                    title={`Remove @${mention.username}`}
                                >
                                    <span className="w-1.5 h-1.5 rounded-full bg-lime-400" />
                                    @{mention.username}
                                    <span className="rounded-full bg-white/20 px-1 text-[10px] leading-4">x</span>
                                </button>
                            ))}
                            {tagPopover && (
                                <div
                                    className="absolute z-20 w-64 -translate-x-1/2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg"
                                    style={{
                                        left: `${tagPopover.xPercent}%`,
                                        top: `${tagPopover.yPercent}%`,
                                        transform: 'translate(-50%, calc(-100% - 12px))',
                                    }}
                                    onClick={(event) => event.stopPropagation()}
                                >
                                    <div className="p-3 border-b border-gray-100 dark:border-gray-800">
                                        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                            Tag Someone Here
                                        </p>
                                        <input
                                            ref={mentionInputRef}
                                            type="text"
                                            value={mentionQuery}
                                            onChange={(event) => {
                                                setMentionQuery(event.target.value);
                                                setShowSuggestions(true);
                                            }}
                                            placeholder="Search username"
                                            className="mt-2 w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-700 text-gray-900 dark:text-gray-100"
                                        />
                                    </div>
                                    <div className="max-h-48 overflow-y-auto">
                                        {mentionsLoading && (
                                            <p className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">Searching…</p>
                                        )}
                                        {!mentionsLoading && suggestions.map((user) => (
                                            <button
                                                key={user.id}
                                                type="button"
                                                className="w-full px-3 py-2 text-left text-sm text-gray-900 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800"
                                                onClick={() => handleMentionSelect(user)}
                                            >
                                                @{user.username}
                                            </button>
                                        ))}
                                        {!mentionsLoading && mentionsError && (
                                            <p className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">{mentionsError}</p>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                        <p className="text-xs text-gray-400 dark:text-gray-500">
                            Click the image to place a tag. Click an existing tag bubble to remove it.
                        </p>
                        {selectedMentions.length > 0 && (
                            <div className="space-y-2">
                                <label className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Tagged People</label>
                                <div className="flex flex-wrap gap-2">
                                    {selectedMentions.map((mention) => (
                                        <button
                                            key={`selected-mention-${mention.id}`}
                                            type="button"
                                            className="inline-flex items-center gap-2 rounded-full bg-gray-100 dark:bg-gray-800 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-200"
                                            onClick={() => handleMentionRemove(mention.id)}
                                        >
                                            <span>@{mention.username}</span>
                                            <span className="text-[10px] uppercase tracking-wide text-gray-400 dark:text-gray-500">
                                                {mention.tagPosition ? 'tagged' : 'linked'}
                                            </span>
                                            <span className="rounded-full bg-black/10 dark:bg-white/10 px-1">x</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                        <div className="space-y-2">
                            <label className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Description</label>
                            <textarea
                                value={descriptionInput}
                                onChange={(e) => setDescriptionInput(e.target.value)}
                                placeholder="Write a caption…"
                                className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-700 text-gray-900 dark:text-gray-100"
                                rows={3}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Hashtags</label>
                            <input
                                type="text"
                                value={hashtagsInput}
                                onChange={(e) => setHashtagsInput(e.target.value)}
                                placeholder="e.g. sunset travel friends"
                                className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-700 text-gray-900 dark:text-gray-100"
                            />
                            <p className="text-xs text-gray-400 dark:text-gray-500">Separate with spaces or commas, # optional.</p>
                        </div>
                        {updateError && (
                            <p className="text-sm text-red-500">{updateError}</p>
                        )}
                    </div>
                    <div className="flex justify-end gap-3 px-5 py-4 border-t border-gray-100 dark:border-gray-800">
                        <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={updating}>
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={updating}
                        >
                            {updating ? 'Saving…' : 'Save'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
