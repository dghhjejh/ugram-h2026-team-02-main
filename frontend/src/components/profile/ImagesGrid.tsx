import type { Image } from '../../types/api';
import ProfileImageTile from './ProfileImageTile';

interface ImageGridProps {
    images: Image[];
    activeTab: 'posts' | 'saved';
    onImageDeleted: (imageId: string) => void;
    onDeleteComplete?: () => void;
    onImageUpdated?: (updatedImage: Image) => void;
    openImageId?: string | null;
}

export default function ImagesGrid({
    images,
    activeTab,
    onImageDeleted,
    onDeleteComplete,
    onImageUpdated,
    openImageId,
}: ImageGridProps) {
    return (
        <section className="py-7 pb-20">
            <div className="container-custom">
                {activeTab === 'posts' ? (
                    <div className="grid grid-cols-3 gap-7">
                        {images.map((image) => (
                            <ProfileImageTile
                                key={image.id}
                                image={image}
                                onImageDeleted={onImageDeleted}
                                onDeleteComplete={onDeleteComplete}
                                onImageUpdated={onImageUpdated}
                                openOnMount={openImageId === image.id}
                            />
                        ))}
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center py-20 text-gray-400 dark:text-gray-500">
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" className="mb-4 opacity-50">
                            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" strokeWidth="1" />
                        </svg>
                        <h3 className="text-2xl font-semibold mb-2 text-gray-900">No saved posts yet</h3>
                        <p className="text-sm">Save posts to see them here</p>
                    </div>
                )}
            </div>
        </section>
    );
}
