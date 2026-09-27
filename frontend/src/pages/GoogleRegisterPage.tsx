import { useMemo, useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function useRegistrationToken(): string | null {
    const { hash, search } = useLocation();
    return useMemo(() => {
        const rawParams = hash.startsWith('#') ? hash.slice(1) : search;
        const params = new URLSearchParams(rawParams);
        const token = params.get('token');
        return token;
    }, [hash, search]);
}

export default function GoogleRegisterPage() {
    const navigate = useNavigate();
    const registrationToken = useRegistrationToken();
    const { completeGoogleRegistration, loading, error, clearError } = useAuth();
    const [username, setUsername] = useState('');
    const [submitting, setSubmitting] = useState(false);

    if (!registrationToken) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen gap-3">
                <p className="text-sm text-red-500">Missing Google registration data.</p>
                <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => navigate('/login')}
                >
                    Back to login
                </button>
            </div>
        );
    }

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        clearError();
        setSubmitting(true);
        try {
            await completeGoogleRegistration({
                registration_token: registrationToken,
                username: username.trim(),
            });
            navigate('/');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#fafafa] dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex items-center justify-center px-6 py-10">
            <div className="max-w-sm w-full space-y-4">
                <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg px-10 py-8 text-center shadow-sm space-y-4">
                    <h1 className="text-3xl font-black gradient-text">Choose a username</h1>
                    <p className="text-sm text-gray-500">
                        We found your Google account. Pick a username to finish creating your profile.
                    </p>
                    <form className="space-y-3" onSubmit={handleSubmit}>
                        <input
                            type="text"
                            placeholder="Username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="input"
                            required
                            minLength={3}
                        />
                        {error && <p className="text-xs text-red-500">{error}</p>}
                        <button
                            type="submit"
                            className="btn btn-primary w-full"
                            disabled={submitting || loading}
                        >
                            {submitting || loading ? 'Creating account…' : 'Continue'}
                        </button>
                    </form>
                </div>
                <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg px-10 py-4 text-center shadow-sm text-sm">
                    Not you? <button className="text-[#0095f6] font-semibold hover:text-[#0077c7]" onClick={() => navigate('/login')}>Log in</button>
                </div>
            </div>
        </div>
    );
}
