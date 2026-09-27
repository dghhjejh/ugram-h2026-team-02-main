import { useState, useEffect, useRef, useCallback, type FormEvent, type KeyboardEvent, type MouseEvent as ReactMouseEvent } from 'react';
import type { MentionTagPosition, UserProfile } from '../../types/api';
import { apiClient } from '../../services/api';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import { FILTERS, type FilterType, getFilterCSS } from '../../utils/imageFilters';

type NewPostModalProps = {
    previewUrl: string;
    onCancel: () => void;
    onSubmit: (
        description: string,
        hashtags: string,
        mentions: string[],
        mentionTags: MentionTagPosition[],
        selectedFilter: FilterType,
        cropSettings?: {
            aspectRatio?: number;
            zoom?: number;
            centerXPercent?: number;
            centerYPercent?: number;
        },
    ) => Promise<void>;
    uploading: boolean;
    uploadError: string | null;
    token: string | undefined;
};

type MentionOption = Pick<UserProfile, 'id' | 'username' | 'profile_photo_url' | 'first_name' | 'last_name'>;
type TagPosition = { xPercent: number; yPercent: number };
type MentionTag = MentionOption & { tagPosition?: TagPosition };
type MentionOrigin = 'photo';
type CropMode = 'normal' | 'zoom';
const MIN_MENTION_QUERY = 2;
const ZOOM_VIEWPORT_ASPECT_RATIO = 1;
const MIN_ORIGINAL_ASPECT_RATIO = 4 / 5;
const MAX_ORIGINAL_ASPECT_RATIO = 1.91;
const NORMAL_PREVIEW_HEIGHT_PX = 420;

export default function NewPostModal({
    previewUrl,
    onCancel,
    onSubmit,
    uploading,
    uploadError,
    token,
}: NewPostModalProps) {
    const [descriptionInput, setDescriptionInput] = useState('');
    const [hashtagsInput, setHashtagsInput] = useState('');
    const [mentionQuery, setMentionQuery] = useState('');
    const [selectedMentions, setSelectedMentions] = useState<MentionTag[]>([]);
    const [suggestions, setSuggestions] = useState<MentionOption[]>([]);
    const [mentionsLoading, setMentionsLoading] = useState(false);
    const [mentionsError, setMentionsError] = useState<string | null>(null);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [tagPopover, setTagPopover] = useState<TagPosition | null>(null);
    const [activeMentionOrigin, setActiveMentionOrigin] = useState<MentionOrigin | null>(null);
    const [selectedFilter, setSelectedFilter] = useState<FilterType>('none');
    const [cropMode, setCropMode] = useState<CropMode>('normal');
    const [cropZoom, setCropZoom] = useState(1);
    const [cropCenterX, setCropCenterX] = useState(50);
    const [cropCenterY, setCropCenterY] = useState(50);
    const [isDraggingCrop, setIsDraggingCrop] = useState(false);
    const [originalAspectRatio, setOriginalAspectRatio] = useState(1);

    const photoMentionInputRef = useRef<HTMLInputElement | null>(null);
    const mentionSectionRef = useRef<HTMLDivElement | null>(null);
    const photoAreaRef = useRef<HTMLDivElement | null>(null);
    const cropPreviewRef = useRef<HTMLDivElement | null>(null);
    const cropDragOriginRef = useRef<{ x: number; y: number; centerX: number; centerY: number } | null>(null);
    const wasCropDraggedRef = useRef(false);
    const sanitizedQuery = mentionQuery.trim().replace(/^@+/, '');

    const clampPercent = (value: number) => Math.min(Math.max(value, 0), 100);

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        const mentionIds = selectedMentions.map((mention) => mention.id);
        const mentionTags: MentionTagPosition[] = selectedMentions
            .filter((mention) => mention.tagPosition)
            .map((mention) => ({
                user_id: mention.id,
                x_percent: mention.tagPosition!.xPercent,
                y_percent: mention.tagPosition!.yPercent,
            }));

        const cropSettings = cropMode === 'normal'
            ? undefined
            : {
                aspectRatio: ZOOM_VIEWPORT_ASPECT_RATIO,
                zoom: cropZoom,
                centerXPercent: cropCenterX,
                centerYPercent: cropCenterY,
            };

        onSubmit(descriptionInput, hashtagsInput, mentionIds, mentionTags, selectedFilter, cropSettings);
    };

    const loadSuggestions = useCallback(
        async (query: string) => {
            if (query.length < MIN_MENTION_QUERY) {
                setSuggestions([]);
                setMentionsLoading(false);
                setMentionsError(null);
                return;
            }

            setMentionsLoading(true);
            setMentionsError(null);

            try {
                const users = await apiClient.searchUsers(query, 8, token ?? undefined);
                const filtered = users.filter(
                    (user) => !selectedMentions.some((mention) => mention.id === user.id),
                );
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
        [token, selectedMentions],
    );

    useEffect(() => {
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
    }, [sanitizedQuery, loadSuggestions]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (!(event.target instanceof Node)) {
                return;
            }
            const inMentionSection = mentionSectionRef.current?.contains(event.target);
            const inPhotoArea = photoAreaRef.current?.contains(event.target);
            if (inMentionSection || inPhotoArea) {
                return;
            }
            setShowSuggestions(false);
            setActiveMentionOrigin(null);
            setTagPopover(null);
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleMentionSelect = (user: MentionOption, position?: TagPosition) => {
        setSelectedMentions((prev) => {
            if (prev.some((mention) => mention.id === user.id)) {
                return prev;
            }
            const nextMention: MentionTag = position ? { ...user, tagPosition: position } : user;
            return [...prev, nextMention];
        });
        setMentionQuery('');
        setSuggestions([]);
        setMentionsError(null);
        setShowSuggestions(false);
        setActiveMentionOrigin(null);
        if (position) {
            setTagPopover(null);
        }
    };

    const handleMentionRemove = (userId: string) => {
        setSelectedMentions((prev) => prev.filter((mention) => mention.id !== userId));
    };

    const handleMentionKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Backspace' && !mentionQuery && selectedMentions.length > 0) {
            event.preventDefault();
            const lastMention = selectedMentions[selectedMentions.length - 1];
            if (lastMention) {
                handleMentionRemove(lastMention.id);
            }
        }
    };

    const startPhotoTagging = (event: ReactMouseEvent<HTMLDivElement>) => {
        if (wasCropDraggedRef.current) {
            wasCropDraggedRef.current = false;
            return;
        }
        const bounds = event.currentTarget.getBoundingClientRect();
        if (!bounds.width || !bounds.height) {
            return;
        }
        const relativeX = ((event.clientX - bounds.left) / bounds.width) * 100;
        const relativeY = ((event.clientY - bounds.top) / bounds.height) * 100;
        const clamp = (value: number) => Math.min(Math.max(value, 8), 92);
        const normalized: TagPosition = {
            xPercent: clamp(relativeX),
            yPercent: clamp(relativeY),
        };
        setTagPopover(normalized);
        setActiveMentionOrigin('photo');
        setMentionsError(null);
        setShowSuggestions(true);
        setTimeout(() => {
            photoMentionInputRef.current?.focus();
        }, 0);
    };

    const handleFilterPrev = () => {
        const currentIndex = FILTERS.findIndex((f) => f.id === selectedFilter);
        const prevIndex = currentIndex === 0 ? FILTERS.length - 1 : currentIndex - 1;
        setSelectedFilter(FILTERS[prevIndex].id);
    };

    const handleFilterNext = () => {
        const currentIndex = FILTERS.findIndex((f) => f.id === selectedFilter);
        const nextIndex = (currentIndex + 1) % FILTERS.length;
        setSelectedFilter(FILTERS[nextIndex].id);
    };

    const handleCropModeChange = (mode: CropMode) => {
        setCropMode(mode);
        if (mode === 'normal') {
            setCropZoom(1);
            setCropCenterX(50);
            setCropCenterY(50);
        }
    };

    const startCropDrag = (event: ReactMouseEvent<HTMLDivElement>) => {
        if (cropMode === 'normal') {
            return;
        }
        event.preventDefault();
        cropDragOriginRef.current = {
            x: event.clientX,
            y: event.clientY,
            centerX: cropCenterX,
            centerY: cropCenterY,
        };
        wasCropDraggedRef.current = false;
        setIsDraggingCrop(true);
    };

    const moveCropDrag = (event: ReactMouseEvent<HTMLDivElement>) => {
        if (cropMode === 'normal') {
            return;
        }
        const origin = cropDragOriginRef.current;
        const bounds = cropPreviewRef.current?.getBoundingClientRect();
        if (!origin || !bounds?.width || !bounds?.height) {
            return;
        }

        const dx = event.clientX - origin.x;
        const dy = event.clientY - origin.y;
        if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
            wasCropDraggedRef.current = true;
        }
        const sensitivity = 100 / cropZoom;

        setCropCenterX(clampPercent(origin.centerX - (dx / bounds.width) * sensitivity));
        setCropCenterY(clampPercent(origin.centerY - (dy / bounds.height) * sensitivity));
    };

    const endCropDrag = () => {
        cropDragOriginRef.current = null;
        setIsDraggingCrop(false);
    };

    const currentFilterName = FILTERS.find((f) => f.id === selectedFilter)?.name || 'Original';
    const isNormalMode = cropMode === 'normal';
    const effectiveCropZoom = isNormalMode ? 1 : cropZoom;
    const effectiveCenterX = isNormalMode ? 50 : cropCenterX;
    const effectiveCenterY = isNormalMode ? 50 : cropCenterY;
    const normalizedOriginalAspectRatio = Math.min(
        MAX_ORIGINAL_ASPECT_RATIO,
        Math.max(MIN_ORIGINAL_ASPECT_RATIO, originalAspectRatio),
    );
    const normalPreviewWidthPx = NORMAL_PREVIEW_HEIGHT_PX * normalizedOriginalAspectRatio;
    const previewFrameStyle = isNormalMode
        ? {
            height: NORMAL_PREVIEW_HEIGHT_PX,
            width: normalPreviewWidthPx,
            maxWidth: '100%',
        }
        : {
            height: NORMAL_PREVIEW_HEIGHT_PX,
            width: NORMAL_PREVIEW_HEIGHT_PX,
            maxWidth: '100%',
        };

    const shouldShowSuggestions = showSuggestions && sanitizedQuery.length >= MIN_MENTION_QUERY;

    const renderSuggestions = (onSelect: (user: MentionOption) => void) => (
        <>
            {mentionsLoading && (
                <p className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">Searching…</p>
            )}
            {!mentionsLoading && suggestions.length > 0 && suggestions.map((user) => (
                <button
                    type="button"
                    key={user.id}
                    className="w-full px-3 py-2 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-gray-800 text-left"
                    onClick={() => onSelect(user)}
                >
                    {user.profile_photo_url ? (
                        <img
                            src={user.profile_photo_url}
                            alt={user.username}
                            className="w-8 h-8 rounded-full object-cover"
                        />
                    ) : (
                        <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs font-semibold text-gray-600 dark:text-gray-200">
                            {user.username.slice(0, 1).toUpperCase()}
                        </div>
                    )}
                    <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">@{user.username}</p>
                        {(user.first_name || user.last_name) && (
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                                {[user.first_name, user.last_name].filter(Boolean).join(' ')}
                            </p>
                        )}
                    </div>
                </button>
            ))}
            {!mentionsLoading && mentionsError && (
                <p className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">{mentionsError}</p>
            )}
        </>
    );

    return (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center px-4">
            <div className="w-full max-w-xl bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white">New post</h3>
                    <button
                        className="text-gray-500 hover:text-gray-800 dark:text-gray-300 dark:hover:text-white text-lg"
                        onClick={onCancel}
                        aria-label="Close"
                    >
                        <X />
                    </button>
                </div>
                <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
                    <div className="p-5 space-y-4 overflow-y-auto flex-1">
                        {previewUrl && (
                            <div className="space-y-3">
                                <div className="flex justify-center">
                                    <div className="relative" ref={photoAreaRef} style={previewFrameStyle}>
                                        <div className="pointer-events-none absolute top-3 left-3 z-20">
                                            <span className="inline-flex items-center gap-1 rounded-full bg-black/70 text-white text-xs font-semibold px-3 py-1 shadow-lg">
                                                Click the photo to tag friends
                                            </span>
                                        </div>
                                        <div
                                            ref={cropPreviewRef}
                                            className={`relative w-full h-full overflow-hidden rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 cursor-pointer ${!isNormalMode ? (isDraggingCrop ? 'cursor-grabbing' : 'cursor-grab') : ''}`}
                                            onClick={startPhotoTagging}
                                            onMouseDown={startCropDrag}
                                            onMouseMove={moveCropDrag}
                                            onMouseUp={endCropDrag}
                                            onMouseLeave={endCropDrag}
                                        >
                                            <img
                                                src={previewUrl}
                                                alt="Preview"
                                                className="block w-full h-full"
                                                onLoad={(event) => {
                                                    const img = event.currentTarget;
                                                    if (img.naturalWidth > 0 && img.naturalHeight > 0) {
                                                        setOriginalAspectRatio(img.naturalWidth / img.naturalHeight);
                                                    }
                                                }}
                                                style={{
                                                    objectFit: isNormalMode ? 'contain' : 'cover',
                                                    objectPosition: `${effectiveCenterX}% ${effectiveCenterY}%`,
                                                    transform: `scale(${effectiveCropZoom})`,
                                                    transformOrigin: `${effectiveCenterX}% ${effectiveCenterY}%`,
                                                    filter: getFilterCSS(selectedFilter),
                                                    pointerEvents: 'none',
                                                }}
                                            />
                                        </div>
                                        {selectedMentions
                                            .filter((mention) => mention.tagPosition)
                                            .map((mention) => (
                                                <div
                                                    key={`photo-tag-${mention.id}`}
                                                    className="absolute z-10"
                                                    style={{
                                                        left: `${mention.tagPosition!.xPercent}%`,
                                                        top: `${mention.tagPosition!.yPercent}%`,
                                                        transform: 'translate(-50%, -100%)',
                                                    }}
                                                >
                                                    <span className="inline-flex items-center gap-1 rounded-full bg-black/70 text-white text-xs font-semibold px-2 py-1">
                                                        <span className="w-1.5 h-1.5 rounded-full bg-lime-400"></span>
                                                        @{mention.username}
                                                        <button
                                                            type="button"
                                                            className="text-white/70 hover:text-white"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleMentionRemove(mention.id);
                                                            }}
                                                            aria-label={`Remove ${mention.username} tag`}
                                                        >
                                                            <X size={16} />
                                                        </button>
                                                    </span>
                                                </div>
                                            ))}
                                        {activeMentionOrigin === 'photo' && tagPopover && (
                                            <div
                                                className="absolute z-20"
                                                style={{
                                                    left: `${tagPopover.xPercent}%`,
                                                    top: `${tagPopover.yPercent}%`,
                                                    transform: 'translate(-50%, 10%)',
                                                }}
                                            >
                                                <div className="w-60 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-xl p-3 space-y-2">
                                                    <input
                                                        ref={photoMentionInputRef}
                                                        type="text"
                                                        value={mentionQuery}
                                                        onChange={(e) => setMentionQuery(e.target.value)}
                                                        onFocus={() => setActiveMentionOrigin('photo')}
                                                        onKeyDown={handleMentionKeyDown}
                                                        placeholder="Who is this?"
                                                        className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-700 text-gray-900 dark:text-gray-100"
                                                    />
                                                    <div className="max-h-48 overflow-y-auto">
                                                        {shouldShowSuggestions ? (
                                                            renderSuggestions((user) => handleMentionSelect(user, tagPopover))
                                                        ) : (
                                                            <p className="px-1 text-xs text-gray-500 dark:text-gray-400">Type a username…</p>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 mt-3 px-3 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
                                    <button
                                        type="button"
                                        onClick={handleFilterPrev}
                                        className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                                        aria-label="Previous filter"
                                    >
                                        <ChevronLeft size={18} className="text-gray-600 dark:text-gray-300" />
                                    </button>

                                    <div className="flex-1 text-center">
                                        <p className="text-xs font-medium text-gray-900 dark:text-white">
                                            {currentFilterName}
                                        </p>
                                    </div>

                                    <button
                                        type="button"
                                        onClick={handleFilterNext}
                                        className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                                        aria-label="Next filter"
                                    >
                                        <ChevronRight size={18} className="text-gray-600 dark:text-gray-300" />
                                    </button>
                                </div>

                                <div className="mt-3 rounded-lg border border-gray-200 dark:border-gray-700 p-3 bg-white dark:bg-gray-900">
                                    <div className="flex items-center justify-between gap-2 mb-2">
                                        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                            Framing
                                        </p>
                                        <select
                                            value={cropMode}
                                            onChange={(event) => handleCropModeChange(event.target.value as CropMode)}
                                            className="rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1 text-xs text-gray-900 dark:text-gray-100"
                                        >
                                            <option value="normal">Normal</option>
                                            <option value="zoom">Zoom</option>
                                        </select>
                                    </div>

                                    {cropMode === 'zoom' && (
                                        <div className="space-y-2">
                                            <label className="block text-xs text-gray-500 dark:text-gray-400">
                                                Zoom: {cropZoom.toFixed(1)}x
                                                <input
                                                    type="range"
                                                    min={1}
                                                    max={3}
                                                    step={0.1}
                                                    value={cropZoom}
                                                    onChange={(event) => setCropZoom(Number(event.target.value))}
                                                    className="w-full"
                                                />
                                            </label>
                                            <p className="text-xs text-gray-500 dark:text-gray-400">
                                                Drag on the image above to move framing. Use the zoom slider to zoom in/out.
                                            </p>
                                        </div>
                                    )}
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
                        <div className="space-y-2" ref={mentionSectionRef}>
                            <label className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Mentions</label>
                            {selectedMentions.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                    {selectedMentions.map((mention) => (
                                        <span
                                            key={mention.id}
                                            className="inline-flex items-center gap-1 rounded-full bg-sky-50 dark:bg-sky-900/30 text-sky-700 dark:text-sky-300 text-xs font-medium px-3 py-1"
                                        >
                                            @{mention.username}
                                            <button
                                                type="button"
                                                className="text-sky-500 hover:text-sky-700 dark:text-sky-300 dark:hover:text-white"
                                                onClick={() => handleMentionRemove(mention.id)}
                                                aria-label={`Remove mention for @${mention.username}`}
                                            >
                                                <X size={12} />
                                            </button>
                                        </span>
                                    ))}
                                </div>
                            )}
                            <p className="text-xs text-gray-400 dark:text-gray-500">
                                Tap anywhere on the photo above to place tags, then pick a username in the pop-up.
                            </p>
                        </div>
                        {uploadError && (
                            <p className="text-sm text-red-500">{uploadError}</p>
                        )}
                    </div>
                    <div className="flex justify-end gap-3 px-5 py-4 border-t border-gray-100 dark:border-gray-800 flex-shrink-0">
                        <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={uploading}>
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={uploading}
                        >
                            {uploading ? 'Posting…' : 'Post'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
