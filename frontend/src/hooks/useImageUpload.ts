import { useState, useCallback, useEffect } from 'react';
import { apiClient } from '../services/api';
import { applyFilterToImage, type FilterType } from '../utils/imageFilters';

export function useImageUpload(userId: string | undefined, token: string | undefined, onUploadSuccess: () => Promise<void>) {
    const [uploading, setUploading] = useState(false);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const [pendingFile, setPendingFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);

    const setPendingUpload = useCallback((file: File) => {
        setPendingFile(file);
        setPreviewUrl((currentPreviewUrl) => {
            if (currentPreviewUrl) {
                URL.revokeObjectURL(currentPreviewUrl);
            }
            return URL.createObjectURL(file);
        });
        setUploadError(null);
    }, []);

    const handleFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
        if (!event.target.files || event.target.files.length === 0 || !userId) return;
        const file = event.target.files[0];
        setPendingUpload(file);
        event.target.value = '';
    }, [setPendingUpload, userId]);

    const cancelUpload = useCallback(() => {
        setPendingFile(null);
        setPreviewUrl((currentPreviewUrl) => {
            if (currentPreviewUrl) {
                URL.revokeObjectURL(currentPreviewUrl);
            }
            return null;
        });
        setUploadError(null);
    }, []);

    useEffect(() => {
        return () => {
            if (previewUrl) {
                URL.revokeObjectURL(previewUrl);
            }
        };
    }, [previewUrl]);

    const submitUpload = useCallback(async (
        description: string,
        hashtags: string,
        mentionIds: string[],
        mentionTags: { user_id: string; x_percent: number; y_percent: number }[],
        selectedFilter: FilterType = 'none',
        cropSettings?: {
            aspectRatio?: number;
            zoom?: number;
            centerXPercent?: number;
            centerYPercent?: number;
        },
    ) => {
        if (!pendingFile || !userId) return;

        setUploading(true);
        setUploadError(null);

        try {
            const fileToUpload = selectedFilter !== 'none'
                ? await applyFilterToImage(pendingFile, selectedFilter)
                : pendingFile;

            await apiClient.uploadImage(userId, {
                file: fileToUpload,
                description,
                hashtags,
                mentions_user_ids: mentionIds,
                mention_tags: mentionTags,
                crop_aspect_ratio: cropSettings?.aspectRatio,
                crop_zoom: cropSettings?.zoom,
                crop_center_x_percent: cropSettings?.centerXPercent,
                crop_center_y_percent: cropSettings?.centerYPercent,
            }, token ?? undefined);

            await onUploadSuccess();
            cancelUpload();
        } catch (err) {
            setUploadError(err instanceof Error ? err.message : 'Upload failed');
        } finally {
            setUploading(false);
        }
    }, [pendingFile, userId, token, onUploadSuccess, cancelUpload]);

    return {
        uploading,
        uploadError,
        pendingFile,
        previewUrl,
        handleFileChange,
        setPendingUpload,
        cancelUpload,
        submitUpload
    };
}
