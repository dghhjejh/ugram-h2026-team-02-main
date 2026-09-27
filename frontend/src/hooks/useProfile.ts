import { useState, useEffect, useCallback } from 'react';
import type { UserProfile, UserStats, Image } from '../types/api';
import { apiClient } from '../services/api';

const PROFILE_IMAGES_LIMIT = 50;

export function useProfile(
    userId: string | undefined,
    token: string | undefined,
    isOwnProfile = false,
    onLogout?: () => void,
) {
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [stats, setStats] = useState<UserStats | null>(null);
    const [images, setImages] = useState<Image[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadProfileData = useCallback(async () => {
        if (!userId) return;
        try {
            setLoading(true);
            setError(null);

            const [freshProfile, userStats, userImages] = await Promise.all([
                isOwnProfile
                    ? apiClient.getCurrentUser(token ?? undefined)
                    : apiClient.getUserProfile(userId, token ?? undefined),
                apiClient.getUserStats(userId, token ?? undefined),
                apiClient.getUserImages(userId, PROFILE_IMAGES_LIMIT, 0, token ?? undefined),
            ]);

            setProfile(freshProfile);
            setStats(userStats);
            setImages(userImages.images);
        } catch (err) {
            if (err instanceof Error && err.message.includes('401') && onLogout) {
                onLogout();
            }
            setError(err instanceof Error ? err.message : 'Failed to load profile');
        } finally {
            setLoading(false);
        }
    }, [isOwnProfile, userId, token, onLogout]);

    useEffect(() => {
        if (userId) {
            loadProfileData();
        }
    }, [userId, token, loadProfileData]);

    const refreshImages = async () => {
        if (!userId) return;

        const [userImages, userStats] = await Promise.all([
            apiClient.getUserImages(userId, PROFILE_IMAGES_LIMIT, 0, token ?? undefined),
            apiClient.getUserStats(userId, token ?? undefined),
        ]);

        setImages(userImages.images);
        setStats(userStats);
    };

    return {
        profile,
        stats,
        images,
        loading,
        error,
        refresh: loadProfileData,
        refreshImages
    };
}
