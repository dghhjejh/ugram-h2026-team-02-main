import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { X } from 'lucide-react';
import type { Image } from '../../types/api';

type EditImageModalProps = {
    image: Image;
    open: boolean;
    onCancel: () => void;
    onSubmit: (description: string, hashtags: string) => Promise<void>;
    updating: boolean;
    updateError: string | null;
};

export default function EditImageModal({
    image,
    open,
    onCancel,
    onSubmit,
    updating,
    updateError,
}: EditImageModalProps) {
    const [descriptionInput, setDescriptionInput] = useState('');
    const [hashtagsInput, setHashtagsInput] = useState('');

    useEffect(() => {
        if (!open) {
            return;
        }
        setDescriptionInput(image.description || '');
        setHashtagsInput(image.hashtags.join(' '));
    }, [image, open]);

    const mentionLabels = useMemo(
        () =>
            (image.mention_tags ?? []).map((tag) => {
                const mention = image.mentions?.find((item) => item.id === tag.user_id);
                return {
                    ...tag,
                    username: mention?.username ?? null,
                };
            }),
        [image],
    );

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        if (!descriptionInput.trim()) return; // Prevent empty description
        onSubmit(descriptionInput, hashtagsInput);
    };

    if (!open) return null;
    return (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center px-4">
            <div className="w-full max-w-xl bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden">
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
                                className="w-full rounded-xl border border-gray-100 dark:border-gray-800 max-h-72 object-cover"
                            />
                            {mentionLabels.map((tag) => (
                                <span
                                    key={`edit-image-tag-${tag.user_id}`}
                                    className="absolute z-10 inline-flex items-center gap-1 rounded-full bg-black/75 text-white text-xs font-semibold px-2 py-1"
                                    style={{
                                        left: `${tag.x_percent}%`,
                                        top: `${tag.y_percent}%`,
                                        transform: 'translate(-50%, -100%)',
                                    }}
                                >
                                    <span className="w-1.5 h-1.5 rounded-full bg-lime-400" />
                                    @{tag.username ?? 'user'}
                                </span>
                            ))}
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Description</label>
                            <textarea
                                value={descriptionInput}
                                onChange={(e) => setDescriptionInput(e.target.value)}
                                placeholder="Write a caption…"
                                className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-700 text-gray-900 dark:text-gray-100"
                                rows={3}
                                required
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
                            disabled={updating || !descriptionInput.trim()}
                        >
                            {updating ? 'Saving…' : 'Save'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
