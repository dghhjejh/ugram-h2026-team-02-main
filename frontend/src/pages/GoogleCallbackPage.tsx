import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function GoogleCallbackPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const { clearError, acceptExternalToken } = useAuth();
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const run = async () => {
            clearError();
            const rawParams = location.hash.startsWith('#') ? location.hash.slice(1) : location.search;
            const params = new URLSearchParams(rawParams);
            const token = params.get('token');
            if (!token) {
                setError('Missing token from Google callback');
                return;
            }
            try {
                await acceptExternalToken(token);
                navigate('/', { replace: true });
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Sign-in failed');
            }
        };
        void run();
    }, [acceptExternalToken, clearError, location.hash, location.search, navigate]);

    return (
        <div className="flex flex-col items-center justify-center min-h-screen gap-4">
            <div className="spinner" />
            <p className="text-sm text-gray-500">
                {error ?? 'Signing you in…'}
            </p>
        </div>
    );
}
