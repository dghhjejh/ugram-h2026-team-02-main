import { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { apiClient } from '../../services/api';
import { useAuth } from '../../context/AuthContext.tsx';
import type { Image, MentionTagPosition } from '../../types/api';
import EditImageModal from './EditImageModal';
import ImagePostModal, { type ImagePostModalItem } from './ImagePostModal';

interface ProfileImageTileProps {
    image: Image;
    onImageDeleted: (imageId: string) => void;
    onDeleteComplete?: () => void;
    onImageUpdated?: (updatedImage: Image) => void;
    openOnMount?: boolean;
}

export default function ProfileImageTile({
                                             image,
                                             onImageDeleted,
                                             onDeleteComplete,
                                             onImageUpdated,
                                             openOnMount = false,
                                         }: ProfileImageTileProps) {
    const { user, token } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [selectedImage, setSelectedImage] = useState<Image | null>(openOnMount ? image : null);
    const [editModalOpen, setEditModalOpen] = useState(false);
    const [updating, setUpdating] = useState(false);
    const [updateError, setUpdateError] = useState<string | null>(null);
    const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
    const [profilePhotoUrl, setProfilePhotoUrl] = useState<string | null>(null);
    const [photoError, setPhotoError] = useState(false);
    const latestOpenRequestImageId = useRef<string | null>(null);

    useEffect(() => {
        if (!selectedImage || !token) return;

        setProfilePhotoUrl(null);
        setPhotoError(false);

        const fetchPhoto = async () => {
            try {
                const res = await apiClient.getProfilePhotoUrl(selectedImage.owner_user_id, token);
                setProfilePhotoUrl(res.signed_url);
            } catch {
                setPhotoError(true);
            }
        };

        void fetchPhoto();
    }, [selectedImage, token]);

    const close = () => {
        latestOpenRequestImageId.current = null;
        setSelectedImage(null);
        setEditModalOpen(false);
        setConfirmDeleteOpen(false);
        const params = new URLSearchParams(location.search);
        if (params.has('openImage')) {
            params.delete('openImage');
            navigate({ search: params.toString() }, { replace: true });
        }
    };

    const isOwner = Boolean(user && selectedImage && user.id === selectedImage.owner_user_id);
    const ownerUsername = selectedImage?.mentions?.find((mention) => mention.id === selectedImage?.owner_user_id)?.username
        ?? (isOwner && user?.username ? user.username : null);
    const fallbackAvatar = `https://ui-avatars.com/api/?name=${encodeURIComponent(`${user?.first_name ?? ''} ${user?.last_name ?? ''}`.trim() || 'user')}&size=64&background=10b981&color=white&font-size=0.4`;
    const avatarSrc = photoError || !profilePhotoUrl ? fallbackAvatar : profilePhotoUrl;

    const handleDelete = async () => {
        if (!selectedImage || !isOwner) return;
        setSelectedImage(null);
        onImageDeleted(selectedImage.id);
        await apiClient.deleteImage(selectedImage.id, token);
        onDeleteComplete?.();
    };

    useEffect(() => {
        if (openOnMount) setSelectedImage(image);
    }, [openOnMount]);

    const handleOpenImage = (imageToOpen: Image) => {
        if (!token) {
            setSelectedImage(imageToOpen);
            return;
        }

        latestOpenRequestImageId.current = imageToOpen.id;

        void Promise.all([
            apiClient.getImage(imageToOpen.id, token),
            apiClient.getImageLikeStats(imageToOpen.id, token),
            apiClient.listImageComments(imageToOpen.id, 1, token),
        ])
            .then(([detailedImage, likeStats, commentList]) => {
                if (latestOpenRequestImageId.current !== imageToOpen.id) {
                    return;
                }

                setSelectedImage({
                    ...detailedImage,
                    like_count: likeStats.total_likes,
                    comment_count: commentList.total,
                });
            })
            .catch((error) => {
                console.error('Failed to load detailed image for profile modal', error);

                if (latestOpenRequestImageId.current !== imageToOpen.id) {
                    return;
                }

                setSelectedImage(imageToOpen);
            });
    };

    const handleEditOpen = () => {
        setEditModalOpen(true);
        setConfirmDeleteOpen(false);
    };

    const handleEditSubmit = async (
        description: string,
        hashtags: string,
        mentionsUserIds: string[],
        mentionTags: MentionTagPosition[],
    ) => {
        if (!selectedImage || !isOwner) return;
        setUpdating(true);
        setUpdateError(null);
        try {
            const updated = await apiClient.updateImageMetadata(
                selectedImage.id,
                {
                    description,
                    hashtags: hashtags
                        .split(/[,\s]+/)
                        .map((tag) => tag.replace(/^#/, '').trim())
                        .filter(Boolean),
                    mentions_user_ids: mentionsUserIds,
                    mention_tags: mentionTags,
                },
                token,
            );
            onImageUpdated?.(updated);
            setEditModalOpen(false);
            setSelectedImage(updated);
        } catch (error) {
            setUpdateError(error instanceof Error ? error.message : 'Failed to update image');
        } finally {
            setUpdating(false);
        }
    };

    const modalItem: ImagePostModalItem | null = selectedImage
        ? {
            id: selectedImage.id,
            owner_user_id: selectedImage.owner_user_id,
            owner_username: ownerUsername ?? 'user',
            owner_profile_photo_url: avatarSrc,
            description: selectedImage.description,
            hashtags: selectedImage.hashtags,
            mentions: selectedImage.mentions ?? [],
            mention_tags: selectedImage.mention_tags ?? [],
            image_url: selectedImage.image_url,
            view_url: selectedImage.view_url,
            created_at: selectedImage.created_at,
            updated_at: selectedImage.updated_at,
            like_count: selectedImage.like_count,
            comment_count: selectedImage.comment_count,
        }
        : null;

    return (
        <>
            <button
                className="relative aspect-square overflow-hidden rounded-lg cursor-pointer bg-gray-100 group"
                onClick={() => handleOpenImage(image)}
                type="button"
            >
                <img
                    src={image.thumbnail_view_url || image.view_url || image.image_url}
                    alt={image.description || 'Image'}
                    className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-250">
                    <span className="text-white font-semibold text-base line-clamp-2 text-center px-3">
                        {image.description || 'View photo'}
                    </span>
                </div>
            </button>

            <ImagePostModal
                key={modalItem?.id ?? 'closed'}
                item={modalItem}
                onClose={close}
                ownerActions={isOwner ? { onEdit: handleEditOpen, onDelete: () => setConfirmDeleteOpen(true) } : undefined}
            />

            {confirmDeleteOpen ? (
                <div
                    className="fixed inset-0 z-[60] bg-black/60 flex items-center justify-center px-4"
                    onClick={() => setConfirmDeleteOpen(false)}
                >
                    <div
                        className="bg-white dark:bg-neutral-800 rounded-xl shadow-xl p-6 w-full max-w-sm"
                        onClick={(event) => event.stopPropagation()}
                    >
                        <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-2">Delete this image?</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mb-5">This action cannot be undone.</p>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setConfirmDeleteOpen(false)}
                                className="px-4 py-2 text-sm rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-gray-700 dark:text-gray-200"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => {
                                    setConfirmDeleteOpen(false);
                                    void handleDelete();
                                }}
                                className="px-4 py-2 text-sm rounded-lg bg-red-600 hover:bg-red-700 text-white"
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            ) : null}

            {selectedImage !== null && editModalOpen ? (
                <div className="fixed inset-0 z-[60]" onClick={(event) => event.stopPropagation()}>
                    <EditImageModal
                        image={selectedImage}
                        open={editModalOpen}
                        onCancel={() => setEditModalOpen(false)}
                        onSubmit={handleEditSubmit}
                        updating={updating}
                        updateError={updateError}
                    />
                </div>
            ) : null}
        </>
    );
}
