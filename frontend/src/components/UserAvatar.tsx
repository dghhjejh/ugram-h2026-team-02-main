import { useState, useEffect } from 'react';
import { apiClient } from '../services/api';
import type { UserProfile } from '../types/api';

interface UserAvatarProps {
    user: UserProfile;
    token?: string;
    size?: 'sm' | 'md' | 'lg';
    className?: string;
}

const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16'
};

export default function UserAvatar({ user, token, size = 'md', className = '' }: UserAvatarProps) {
    const [imageError, setImageError] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [signedUrl, setSignedUrl] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;

        const fetchSignedUrl = async () => {
            setImageError(false);
            setIsLoading(true);
            setSignedUrl(null);

            if (user.profile_photo_url && user.profile_photo_url.includes('amazonaws.com') && token) {
                try {
                    const response = await apiClient.getProfilePhotoUrl(user.id, token);
                    if (isMounted) {
                        setSignedUrl(response.signed_url);
                    }
                } catch {
                    if (isMounted) {
                        setImageError(true);
                    }
                }
            }

            if (isMounted) {
                setIsLoading(false);
            }
        };

        fetchSignedUrl();

        return () => {
            isMounted = false;
        };
    }, [user.profile_photo_url, user.id, token]);

    const handleImageLoad = () => {
        setIsLoading(false);
    };

    const handleImageError = () => {
        setImageError(true);
        setIsLoading(false);
    };

    const getAvatarUrl = () => {
        const defaultAvatar = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.first_name + ' ' + user.last_name)}&size=150&background=10b981&color=white&font-size=0.4`;

        if (imageError) {
            return defaultAvatar;
        }

        if (user.profile_photo_url && user.profile_photo_url.includes('amazonaws.com')) {
            if (signedUrl) {
                return signedUrl;
            }
            return defaultAvatar;
        }

        return user.profile_photo_url || defaultAvatar;
    };

    return (
        <div className={`relative ${sizeClasses[size]} ${className}`}>
            {isLoading && (
                <div className={`${sizeClasses[size]} rounded-full border border-gray-100 dark:border-gray-800 bg-gray-200 dark:bg-gray-700 animate-pulse`} />
            )}
            <img
                key={user.profile_photo_url}
                src={getAvatarUrl()}
                alt={user.username}
                className={`${sizeClasses[size]} rounded-full object-cover border border-gray-100 dark:border-gray-800 ${isLoading ? 'hidden' : ''}`}
                onLoad={handleImageLoad}
                onError={handleImageError}
            />
        </div>
    );
}
