import { useState, useEffect } from 'react';
import type { PrivateUserProfile, UpdateUserProfileRequest } from '../../types/api';
import { apiClient } from '../../services/api';
import { formatErrorMessage } from '../../utils/errors';

interface EditProfileModalProps {
    profile: PrivateUserProfile;
    token: string;
    isOpen: boolean;
    onClose: () => void;
    onUpdate: (updatedProfile: PrivateUserProfile) => void;
}

export default function EditProfileModal({ profile, token, isOpen, onClose, onUpdate }: EditProfileModalProps) {
    const [formData, setFormData] = useState({
        username: profile.username,
        email: profile.email,
        first_name: profile.first_name,
        last_name: profile.last_name,
        phone_number: profile.phone_number || '',
    });

    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [signedUrl, setSignedUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen) {
            setFormData({
                username: profile.username,
                email: profile.email,
                first_name: profile.first_name,
                last_name: profile.last_name,
                phone_number: profile.phone_number || '',
            });
            setSelectedFile(null);
            setPreviewUrl(null);
            setSignedUrl(null);
            setError(null);

            if (profile.profile_photo_url && profile.profile_photo_url.includes('amazonaws.com')) {
                apiClient.getProfilePhotoUrl(profile.id, token)
                    .then(response => {
                        setSignedUrl(response.signed_url);
                    })
                    .catch(() => {
                    });
            }
        }
    }, [isOpen, profile, token]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value,
        }));
    };

    const validateFormData = (): string | null => {
        if (formData.username && formData.username.length < 3) {
            return 'Username must be at least 3 characters long';
        }
        if (formData.username && formData.username.length > 50) {
            return 'Username must be no more than 50 characters long';
        }
        if (formData.username && !/^[a-zA-Z0-9_]+$/.test(formData.username)) {
            return 'Username can only contain letters, numbers, and underscores';
        }

        if (formData.email && !/\S+@\S+\.\S+/.test(formData.email)) {
            return 'Please enter a valid email address';
        }

        if (formData.first_name && (formData.first_name.length < 1 || formData.first_name.length > 100)) {
            return 'First name must be between 1 and 100 characters';
        }
        if (formData.last_name && (formData.last_name.length < 1 || formData.last_name.length > 100)) {
            return 'Last name must be between 1 and 100 characters';
        }

        if (formData.phone_number && formData.phone_number.trim()) {
            const phoneRegex = /^\+?[1-9]\d{1,14}$/;
            const cleanPhone = formData.phone_number.replace(/[\s-()]/g, '');
            if (!phoneRegex.test(cleanPhone)) {
                return 'Phone number must start with 1-9 and contain 2-15 digits total (e.g., +1234567890)';
            }
        }

        return null;
    };

    const resetForm = () => {
        setFormData({
            username: profile.username,
            email: profile.email,
            first_name: profile.first_name,
            last_name: profile.last_name,
            phone_number: profile.phone_number || '',
        });
        setSelectedFile(null);
        setPreviewUrl(null);
        setError(null);

        if (profile.profile_photo_url && profile.profile_photo_url.includes('amazonaws.com')) {
            apiClient.getProfilePhotoUrl(profile.id, token)
                .then(response => {
                    setSignedUrl(response.signed_url);
                })
                .catch(() => {

                });
        } else {
            setSignedUrl(null);
        }
    };

    const getDisplayPhotoUrl = () => {
        if (previewUrl) {
            return previewUrl;
        }
        if (signedUrl) {
            return signedUrl;
        }
        if (profile.profile_photo_url && !profile.profile_photo_url.includes('amazonaws.com')) {
            return profile.profile_photo_url;
        }
        return `https://ui-avatars.com/api/?name=${encodeURIComponent(profile.first_name + ' ' + profile.last_name)}&size=300&background=10b981&color=white&font-size=0.4`;
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            const url = URL.createObjectURL(file);
            setPreviewUrl(url);
        }
    };

    const uploadProfilePhoto = async (file: File): Promise<string> => {
        const contentType = file.type || 'application/octet-stream';

        const presign = await apiClient.presignImage(
            {
                owner_user_id: profile.id,
                filename: `profile_${Date.now()}_${file.name}`,
                content_type: contentType,
                content_length: file.size,
            },
            token
        );

        const uploadResp = await fetch(presign.upload_url, {
            method: 'PUT',
            headers: { 'Content-Type': contentType },
            body: file,
        });

        if (!uploadResp.ok) {
            throw new Error(`Upload failed with status ${uploadResp.status}`);
        }

        await fetch(presign.image_url, { method: 'HEAD' }).catch(() => {
        });

        return presign.image_url;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        const validationError = validateFormData();
        if (validationError) {
            setError(validationError);
            setLoading(false);
            return;
        }

        try {
            const updateData: UpdateUserProfileRequest = {};
            if (formData.username !== profile.username) {
                updateData.username = formData.username.trim() || undefined;
            }
            if (formData.email !== profile.email) {
                updateData.email = formData.email.trim() || undefined;
            }
            if (formData.first_name !== profile.first_name) {
                updateData.first_name = formData.first_name.trim() || undefined;
            }
            if (formData.last_name !== profile.last_name) {
                updateData.last_name = formData.last_name.trim() || undefined;
            }

            const currentPhone = profile.phone_number || '';
            const newPhone = formData.phone_number.trim();
            if (newPhone !== currentPhone) {
                if (newPhone) {
                    const cleanPhone = newPhone.replace(/[\s-()]/g, '');
                    updateData.phone_number = cleanPhone;
                } else {
                    updateData.phone_number = undefined;
                }
            }

            if (selectedFile) {
                try {
                    const uploadedPhotoUrl = await uploadProfilePhoto(selectedFile);
                    updateData.profile_photo_url = uploadedPhotoUrl;
                } catch (uploadError) {
                    setError(formatErrorMessage(uploadError, 'Failed to upload profile photo'));
                    setLoading(false);
                    return;
                }
            }

            if (Object.keys(updateData).length === 0) {
                onClose();
                return;
            }

            const updatedProfile = await apiClient.updateUserProfile(profile.id, updateData, token);

            onUpdate(updatedProfile);

            onClose();
        } catch (err) {
            setError(formatErrorMessage(err, 'Failed to update profile'));
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
                <div className="p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Edit Profile</h2>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                        >
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path d="M18 6L6 18M6 6l12 12" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                        </button>
                    </div>

                    {error && (
                        <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-3 rounded-lg mb-4 text-sm">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Username
                            </label>
                            <input
                                type="text"
                                name="username"
                                value={formData.username}
                                onChange={handleInputChange}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                required
                                minLength={3}
                                maxLength={50}
                                pattern="^[a-zA-Z0-9_]+$"
                                title="Username can only contain letters, numbers, and underscores"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Email
                            </label>
                            <input
                                type="email"
                                name="email"
                                value={formData.email}
                                onChange={handleInputChange}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                required
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                First Name
                            </label>
                            <input
                                type="text"
                                name="first_name"
                                value={formData.first_name}
                                onChange={handleInputChange}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                required
                                minLength={1}
                                maxLength={100}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Last Name
                            </label>
                            <input
                                type="text"
                                name="last_name"
                                value={formData.last_name}
                                onChange={handleInputChange}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                required
                                minLength={1}
                                maxLength={100}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Phone Number
                            </label>
                            <input
                                type="tel"
                                name="phone_number"
                                value={formData.phone_number}
                                onChange={handleInputChange}
                                placeholder="+1234567890"
                                pattern="^\+?[1-9]\d{1,14}$"
                                title="Phone number must start with 1-9 and contain 2-15 digits total (e.g., +1234567890)"
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                            />
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                International format recommended (e.g., +1234567890)
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Profile Photo
                            </label>
                            <div className="space-y-3">
                                <div className="flex justify-center">
                                    <img
                                        src={getDisplayPhotoUrl()}
                                        alt="Profile preview"
                                        className="w-24 h-24 rounded-full object-cover border-4 border-gray-200 dark:border-gray-600"
                                    />
                                </div>
                                <div>
                                    <label className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
                                        <input
                                            type="file"
                                            accept="image/*"
                                            onChange={handleFileChange}
                                            className="hidden"
                                        />
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                        </svg>
                                        Choose New Photo
                                    </label>
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-3 pt-4">
                            <button
                                type="button"
                                onClick={onClose}
                                className="flex-1 px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={resetForm}
                                className="flex-1 px-4 py-2 text-gray-700 dark:text-gray-300 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg hover:bg-yellow-200 dark:hover:bg-yellow-900/50 transition-colors"
                                title="Reset to original values"
                            >
                                Reset
                            </button>
                            <button
                                type="submit"
                                disabled={loading}
                                className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                {loading ? 'Saving...' : 'Save Changes'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}
