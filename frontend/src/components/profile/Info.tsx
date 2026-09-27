import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import type { UserProfile, UserStats } from "../../types/api";
import { apiClient } from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import { formatErrorMessage } from "../../utils/errors";

export interface ProfileInfoProps {
    profile: UserProfile;
    stats: UserStats;
    isOwnProfile?: boolean;
    onEditProfile?: () => void;
}

function formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function Bio({ first_name, last_name, email, phone_number, registration_date, isOwnProfile }: UserProfile & {
    isOwnProfile?: boolean;
}) {
    return (
        <div className="flex flex-col gap-4">
            <p className="font-semibold text-gray-900 dark:text-gray-100">
                {first_name} {last_name}
            </p>

            <div className="space-y-2 text-sm">
                {isOwnProfile && email && (
                    <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                        <span>{email}</span>
                    </div>
                )}

                {isOwnProfile && phone_number && (
                    <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                        <span>{phone_number}</span>
                    </div>
                )}

                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                    <span>Joined {formatDate(registration_date)}</span>
                </div>
            </div>
        </div>
    );
}

function StatItem({ value, label }: { value: number; label: string }) {
    return (
        <div className="flex flex-col items-center md:items-start gap-1">
            <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {value.toLocaleString()}
            </span>
            <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
        </div>
    );
}

function Stats({ posts_count, followers_count, following_count }: UserStats) {
    return (
        <div className="flex gap-10 justify-center md:justify-start">
            <StatItem value={posts_count} label="posts" />
            <StatItem value={followers_count} label="followers" />
            <StatItem value={following_count} label="following" />
        </div>
    );
}

function Details({ profile, stats, isOwnProfile, onEditProfile }: {
    profile: UserProfile;
    stats: UserStats;
    isOwnProfile?: boolean;
    onEditProfile?: () => void;
}) {
    const navigate = useNavigate();
    const { token, logout } = useAuth();
    const [menuOpen, setMenuOpen] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [deleteLoading, setDeleteLoading] = useState(false);
    const [deleteError, setDeleteError] = useState<string | null>(null);
    const [confirmation, setConfirmation] = useState('');
    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!menuOpen) return;
        const onClick = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setMenuOpen(false);
                setShowDeleteConfirm(false);
                setConfirmation('');
                setDeleteError(null);
            }
        };
        document.addEventListener('mousedown', onClick);
        return () => document.removeEventListener('mousedown', onClick);
    }, [menuOpen]);

    const handleDeleteAccount = async () => {
        const trimmedConfirmation = confirmation.trim();

        if (!trimmedConfirmation) {
            setDeleteError('Please enter your username');
            return;
        }

        setDeleteLoading(true);
        setDeleteError(null);
        try {
            await apiClient.deleteAccount(profile.id, trimmedConfirmation, token);
            logout();
            navigate('/login');
        } catch (err) {
            setDeleteError(formatErrorMessage(err, 'Failed to delete account'));
        } finally {
            setDeleteLoading(false);
        }
    };

    return (
        <div className="flex flex-col gap-6 text-center md:text-left">
            <div className="flex flex-col md:flex-row items-center gap-6">
                <h2 className="text-3xl font-light text-gray-900 dark:text-gray-100">
                    {profile.username}
                </h2>
                <div className="flex flex-wrap justify-center md:justify-start gap-2 w-full md:w-auto">
                    {isOwnProfile ? (
                        <button onClick={onEditProfile} className="btn btn-primary">
                            Edit Profile
                        </button>
                    ) : (
                        <>
                            <button className="btn btn-primary">Follow</button>
                            <button className="btn btn-secondary">Message</button>
                        </>
                    )}
                    {isOwnProfile && (
                        <div className="relative" ref={menuRef}>
                            <button
                                className="btn btn-secondary px-3"
                                onClick={() => setMenuOpen(!menuOpen)}
                                aria-label="More options"
                            >
                                ⋯
                            </button>
                            {menuOpen && (
                                <>
                                    <div className="fixed inset-0 z-40 md:hidden" onClick={() => setMenuOpen(false)}>
                                        <div className="absolute inset-0 bg-black/50" />
                                    </div>

                                    <div
                                        className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 md:hidden w-[min(22rem,calc(100vw-2rem))] rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xl p-2"
                                        onClick={(e) => e.stopPropagation()}
                                    >
                                        {!showDeleteConfirm ? (
                                            <button
                                                className="w-full text-center px-4 py-3 rounded-lg text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                                                onClick={() => setShowDeleteConfirm(true)}
                                            >
                                                Delete Account
                                            </button>
                                        ) : (
                                            <div className="space-y-3 p-2">
                                                <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded-lg">
                                                    <p className="text-sm text-red-800 dark:text-red-300 font-semibold mb-2">
                                                        Are you sure?
                                                    </p>
                                                    <p className="text-xs text-red-700 dark:text-red-400 mb-3">
                                                        This action cannot be undone. All your data will be permanently deleted.
                                                    </p>
                                                    <p className="text-xs text-red-700 dark:text-red-400 mb-2">
                                                        Type <span className="font-semibold">{profile.username}</span> to confirm:
                                                    </p>
                                                    <input
                                                        type="text"
                                                        placeholder="Type your username"
                                                        value={confirmation}
                                                        onChange={(e) => setConfirmation(e.target.value)}
                                                        className="w-full px-3 py-2 text-sm border border-red-300 dark:border-red-700 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                                        disabled={deleteLoading}
                                                    />
                                                </div>
                                                {deleteError && (
                                                    <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-2 rounded-lg text-xs">
                                                        {deleteError}
                                                    </div>
                                                )}
                                                <div className="flex flex-col gap-2">
                                                    <button
                                                        onClick={() => {
                                                            setShowDeleteConfirm(false);
                                                            setConfirmation('');
                                                            setDeleteError(null);
                                                        }}
                                                        className="flex-1 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                                    >
                                                        Cancel
                                                    </button>
                                                    <button
                                                        onClick={handleDeleteAccount}
                                                        disabled={deleteLoading || confirmation.trim() !== profile.username}
                                                        className="flex-1 px-3 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                                    >
                                                        {deleteLoading ? 'Deleting...' : 'Yes, Delete'}
                                                    </button>
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    <div className="hidden md:block absolute right-0 mt-2 w-72 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-lg p-2 z-50">
                                        {!showDeleteConfirm ? (
                                            <button
                                                className="w-full text-left px-4 py-3 rounded-lg text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                                                onClick={() => setShowDeleteConfirm(true)}
                                            >
                                                Delete Account
                                            </button>
                                        ) : (
                                            <div className="space-y-3 p-2">
                                                <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded-lg">
                                                    <p className="text-sm text-red-800 dark:text-red-300 font-semibold mb-2">
                                                        Are you sure?
                                                    </p>
                                                    <p className="text-xs text-red-700 dark:text-red-400 mb-3">
                                                        This action cannot be undone. All your data will be permanently deleted.
                                                    </p>
                                                    <p className="text-xs text-red-700 dark:text-red-400 mb-2">
                                                        Type <span className="font-semibold">{profile.username}</span> to confirm:
                                                    </p>
                                                    <input
                                                        type="text"
                                                        placeholder="Type your username"
                                                        value={confirmation}
                                                        onChange={(e) => setConfirmation(e.target.value)}
                                                        className="w-full px-3 py-2 text-sm border border-red-300 dark:border-red-700 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                                        disabled={deleteLoading}
                                                    />
                                                </div>
                                                {deleteError && (
                                                    <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-2 rounded-lg text-xs">
                                                        {deleteError}
                                                    </div>
                                                )}
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => {
                                                            setShowDeleteConfirm(false);
                                                            setConfirmation('');
                                                            setDeleteError(null);
                                                        }}
                                                        className="flex-1 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                                    >
                                                        Cancel
                                                    </button>
                                                    <button
                                                        onClick={handleDeleteAccount}
                                                        disabled={deleteLoading || confirmation.trim() !== profile.username}
                                                        className="flex-1 px-3 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                                    >
                                                        {deleteLoading ? 'Deleting...' : 'Yes, Delete'}
                                                    </button>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>
            <Stats {...stats} />
            <Bio {...profile} isOwnProfile={isOwnProfile} />
        </div>
    );
}

function Avatar({ profile_photo_url, username, first_name, last_name, id, token }: {
    profile_photo_url?: string | null;
    username: string;
    first_name: string;
    last_name: string;
    id: string;
    token?: string;
}) {
    const [isLoading, setIsLoading] = useState(true);
    const [signedUrl, setSignedUrl] = useState<string | null>(null);

    useEffect(() => {
        const fetchSignedUrl = async () => {
            if (!profile_photo_url?.includes('amazonaws.com') || !token) {
                setIsLoading(false);
                return;
            }

            try {
                const response = await apiClient.getProfilePhotoUrl(id, token);
                setSignedUrl(response.signed_url);
            } catch {
                setSignedUrl(null);
            } finally {
                setIsLoading(false);
            }
        };

        fetchSignedUrl();
    }, [profile_photo_url, id, token]);

    const getAvatarUrl = () => {
        if (signedUrl) return signedUrl;
        if (profile_photo_url && !profile_photo_url.includes('amazonaws.com')) {
            return profile_photo_url;
        }
        return `https://ui-avatars.com/api/?name=${encodeURIComponent(first_name + ' ' + last_name)}&size=300&background=10b981&color=white&font-size=0.4`;
    };

    return (
        <div className="flex justify-center">
            <div className="p-1 bg-gradient-to-tr from-green-400 to-emerald-500 rounded-full shadow-lg">
                {isLoading ? (
                    <div className="w-36 h-36 md:w-40 md:h-40 rounded-full border-4 border-white bg-gray-200 dark:bg-gray-700 animate-pulse" />
                ) : (
                    <img
                        src={getAvatarUrl()}
                        alt={`${username}'s profile`}
                        className="w-36 h-36 md:w-40 md:h-40 rounded-full border-4 border-white object-cover"
                    />
                )}
            </div>
        </div>
    );
}
export default function ProfileInfo({ profile, stats, isOwnProfile, onEditProfile }: ProfileInfoProps) {
    const { token } = useAuth();

    return (
        <section className="py-16 pb-10">
            <div className="container-custom">
                <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-16 items-start">
                    <Avatar
                        profile_photo_url={profile.profile_photo_url ?? undefined}
                        username={profile.username}
                        first_name={profile.first_name}
                        last_name={profile.last_name}
                        id={profile.id}
                        token={token ?? undefined}
                    />
                    <Details
                        profile={profile}
                        stats={stats}
                        isOwnProfile={isOwnProfile}
                        onEditProfile={onEditProfile}
                    />
                </div>
            </div>
        </section>
    );
}
