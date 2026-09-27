import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useUsers } from '../hooks/useUsers';
import Header from '../components/profile/Header';
import UserAvatar from '../components/UserAvatar';

const USERS_PER_PAGE = 10;

export default function UsersPage() {
    const { token, loading: authLoading } = useAuth();
    const {
        users,
        postsCountByUserId,
        loading,
        error,
        total,
        handleNextPage,
        handlePrevPage,
        currentPage,
        totalPages,
        offset
    } = useUsers(token, USERS_PER_PAGE);

    if (authLoading || (loading && users.length === 0)) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen gap-5">
                <div className="spinner"></div>
                <p className="text-gray-500 text-sm">Loading users...</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 dark:text-gray-100 fade-in">
            <Header appName="uGram" />

            <main className="container-custom py-8">
                <div className="max-w-2xl mx-auto">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Discover Users</h2>
                        {total > 0 && (
                            <span className="text-xs font-medium text-gray-500 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded-full">
                                {total} users
                            </span>
                        )}
                    </div>

                    {error && (
                        <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-4 rounded-xl mb-6 text-sm">
                            {error}
                        </div>
                    )}

                    <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-soft-sm border border-gray-100 dark:border-gray-800 overflow-hidden mb-6">
                        {users.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">
                                No users found.
                            </div>
                        ) : (
                            <ul className={`divide-y divide-gray-100 dark:divide-gray-800 ${loading ? 'opacity-50 pointer-events-none' : ''} transition-opacity`}>
                                {users.map((u) => (
                                    <li key={u.id} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                                        <Link to={`/profile/${u.id}`} className="flex items-center gap-4">
                                            <UserAvatar
                                                user={u}
                                                token={token}
                                                size="md"
                                            />
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                                                    {u.username}
                                                </p>
                                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                                    {postsCountByUserId[u.id] ?? 0} posts
                                                </p>
                                                {u.bio && (
                                                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                                        {u.bio}
                                                    </p>
                                                )}
                                            </div>
                                            <div className="text-xs font-medium text-indigo-600 dark:text-indigo-400">
                                                View Profile
                                            </div>
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    {totalPages > 1 && (
                        <div className="flex items-center justify-between px-2">
                            <button
                                onClick={handlePrevPage}
                                disabled={offset === 0 || loading}
                                className="btn btn-secondary text-sm disabled:opacity-50"
                            >
                                Previous
                            </button>
                            <span className="text-xs text-gray-500 font-medium">
                                Page {currentPage} of {totalPages}
                            </span>
                            <button
                                onClick={handleNextPage}
                                disabled={offset + USERS_PER_PAGE >= total || loading}
                                className="btn btn-secondary text-sm disabled:opacity-50"
                            >
                                Next
                            </button>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
