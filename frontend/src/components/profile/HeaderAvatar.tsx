import { useState, useEffect } from 'react';
import { apiClient } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import type { UserProfile } from '../../types/api';

interface HeaderAvatarProps {
    user: UserProfile;
}

export default function HeaderAvatar({ user }: HeaderAvatarProps) {
    const { token } = useAuth();
    const [signedUrl, setSignedUrl] = useState<string | null>(null);
    const [imageError, setImageError] = useState(false);

    useEffect(() => {
        const fetchSignedUrl = async () => {
            setSignedUrl(null);
            setImageError(false);

            if (user.profile_photo_url && user.profile_photo_url.includes('amazonaws.com') && token) {
                try {
                    const response = await apiClient.getProfilePhotoUrl(user.id, token);
                    setSignedUrl(response.signed_url);
                } catch {
                    setImageError(true);
                }
            }
        };

        fetchSignedUrl();
    }, [user.profile_photo_url, user.id, token]);

    const getAvatarUrl = () => {
        const defaultAvatar = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.first_name + ' ' + user.last_name)}&size=64&background=10b981&color=white&font-size=0.4`;

        if (imageError || (!user.profile_photo_url && !signedUrl)) {
            return defaultAvatar;
        }

        if (signedUrl) {
            return signedUrl;
        }

        return user.profile_photo_url || defaultAvatar;
    };

    return (
        <img
            src={getAvatarUrl()}
            alt="My profile avatar"
            className="w-9 h-9 rounded-full object-cover border border-gray-200 dark:border-gray-700"
            onError={() => setImageError(true)}
        />
    );
}
