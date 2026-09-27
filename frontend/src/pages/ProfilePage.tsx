import { useState, useMemo } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useProfile } from '../hooks/useProfile';
import { useImageUpload } from '../hooks/useImageUpload';
import Header from '../components/profile/Header';
import ProfileInfo from '../components/profile/Info';
import ImagesGrid from '../components/profile/ImagesGrid';
import Tabs from '../components/profile/Tabs';
import NewPostModal from '../components/profile/NewPostModal';
import EditProfileModal from '../components/profile/EditProfileModal';
import WebcamCaptureModal from '../components/profile/WebcamCaptureModal';
import type { Image, PrivateUserProfile, UserProfile } from '../types/api';

export default function ProfilePage() {
    const { userId } = useParams<{ userId: string }>();
    const [searchParams] = useSearchParams();
    const { user, token, logout, updateUser, loading: authLoading } = useAuth();

    const effectiveUserId = userId || user?.id;
    const isOwnProfile = !userId || userId === user?.id;

    const {
        profile,
        stats,
        images,
        loading,
        error,
        refresh,
        refreshImages,
    } = useProfile(effectiveUserId, token, isOwnProfile, logout);

    const {
        uploading,
        uploadError,
        pendingFile,
        previewUrl,
        handleFileChange,
        setPendingUpload,
        cancelUpload,
        submitUpload,
    } = useImageUpload(profile?.id, token, refreshImages);

    const [deletedImageIds, setDeletedImageIds] = useState<string[]>([]);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [isCameraModalOpen, setIsCameraModalOpen] = useState(false);
    const [currentProfile, setCurrentProfile] = useState<UserProfile | null>(profile);
    const [updatedImages, setUpdatedImages] = useState<Image[]>([]);

    const handleImageDeleted = (imageId: string) => {
        setDeletedImageIds((ids) => [...ids, imageId]);
    };

    const visibleImages = useMemo(() => {
        const deletedSet = new Set(deletedImageIds);
        const updatedMap = new Map(updatedImages.map((img) => [img.id, img]));
        return images
            .filter((img) => !deletedSet.has(img.id))
            .map((img) => updatedMap.get(img.id) || img);
    }, [images, deletedImageIds, updatedImages]);

    const handleEditProfile = () => {
        setIsEditModalOpen(true);
    };

    const handleProfileUpdate = (updatedProfile: PrivateUserProfile) => {
        setCurrentProfile(updatedProfile);
        if (isOwnProfile && user?.id === updatedProfile.id) {
            updateUser(updatedProfile);
        }
        refresh();
    };

    const handleImageUpdated = (updatedImage: Image) => {
        setUpdatedImages((prev) => {
            const filtered = prev.filter((img) => img.id !== updatedImage.id);
            return [...filtered, updatedImage];
        });
    };

    const [activeTab, setActiveTab] = useState<'posts' | 'saved'>('posts');
    const [keyword, setKeyword] = useState('');
    const openImageId = searchParams.get('openImage');

    if (authLoading || loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen gap-5">
                <div className="spinner"></div>
                <p className="text-gray-500 text-sm">Loading profile...</p>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="flex items-center justify-center min-h-screen p-5">
                <div className="bg-white p-12 rounded-2xl shadow-soft-lg text-center max-w-md">
                    <h2 className="text-2xl mb-3 text-gray-900">You&apos;re not signed in</h2>
                    <p className="text-gray-500 mb-6 text-sm">Please log in to view your profile.</p>
                </div>
            </div>
        );
    }

    if (error || !profile || !stats) {
        return (
            <div className="flex items-center justify-center min-h-screen p-5">
                <div className="bg-white p-12 rounded-2xl shadow-soft-lg text-center max-w-md">
                    <h2 className="text-2xl mb-3 text-gray-900">Oops! Something went wrong</h2>
                    <p className="text-gray-500 mb-6 text-sm">{error || 'Failed to load profile data'}</p>
                    <button className="btn btn-primary" onClick={refresh}>
                        Try Again
                    </button>
                </div>
            </div>
        );
    }

    const displayProfile = currentProfile || profile;

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 dark:text-gray-100 fade-in">
            <Header appName="uGram" keyword={keyword} setKeyword={setKeyword} />
            <ProfileInfo
                profile={displayProfile}
                stats={stats}
                isOwnProfile={isOwnProfile}
                onEditProfile={handleEditProfile}
            />

            {isOwnProfile && (
                <section className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
                    <div className="container-custom">
                        <Tabs activeTab={activeTab} setActiveTab={setActiveTab} />
                        <div className="mt-5 flex justify-center gap-3 flex-wrap">
                            <label className="inline-flex items-center gap-2 rounded-full border border-dashed border-gray-300 dark:border-gray-700 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-200 hover:border-gray-400 dark:hover:border-gray-500 hover:text-gray-900 dark:hover:text-gray-100 transition-all cursor-pointer">
                                <input
                                    type="file"
                                    accept="image/*"
                                    className="hidden"
                                    onChange={handleFileChange}
                                    disabled={uploading}
                                />
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" className="opacity-70">
                                    <path d="M12 5v14M5 12h14" strokeWidth="2" strokeLinecap="round" />
                                </svg>
                                {uploading ? 'Uploading…' : 'Upload photo'}
                            </label>
                            <button
                                type="button"
                                className="inline-flex items-center gap-2 rounded-full border border-gray-300 dark:border-gray-700 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-200 hover:border-gray-400 dark:hover:border-gray-500 hover:text-gray-900 dark:hover:text-gray-100 transition-all"
                                onClick={() => setIsCameraModalOpen(true)}
                                disabled={uploading}
                            >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" className="opacity-70">
                                    <path d="M4 7a2 2 0 0 1 2-2h3l1.5 2h4L16 5h2a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7Z" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                    <circle cx="12" cy="12" r="3.5" strokeWidth="2" />
                                </svg>
                                Take photo
                            </button>
                        </div>
                        {uploadError && (
                            <p className="text-center text-xs text-red-600 mt-2">{uploadError}</p>
                        )}
                    </div>
                </section>
            )}

            {pendingFile && previewUrl && (
                <NewPostModal
                    previewUrl={previewUrl}
                    onCancel={cancelUpload}
                    onSubmit={submitUpload}
                    uploading={uploading}
                    uploadError={uploadError}
                    token={token}
                />
            )}

            <WebcamCaptureModal
                open={isCameraModalOpen}
                onClose={() => setIsCameraModalOpen(false)}
                onUsePhoto={setPendingUpload}
            />

            {isOwnProfile && displayProfile && token && displayProfile.email && (
                <EditProfileModal
                    profile={displayProfile as PrivateUserProfile}
                    token={token}
                    isOpen={isEditModalOpen}
                    onClose={() => setIsEditModalOpen(false)}
                    onUpdate={handleProfileUpdate}
                />
            )}

            <ImagesGrid
                images={visibleImages}
                activeTab={activeTab}
                onImageDeleted={handleImageDeleted}
                onDeleteComplete={refreshImages}
                onImageUpdated={handleImageUpdated}
                openImageId={openImageId}
            />
        </div>
    );
}
