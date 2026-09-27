import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import GoogleButton from '../components/GoogleButton';
import ThemeToggle from '../components/ThemeToggle';
import type { UserAuthenticationRequest } from '../types/api';

export default function LoginPage() {
    const navigate = useNavigate();
    const { login, loading, error, clearError, user } = useAuth();
    const [form, setForm] = useState<UserAuthenticationRequest>({
        username: '',
        user_password: '',
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (user) {
            navigate('/');
        }
    }, [user, navigate]);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        clearError();
        setSubmitting(true);
        try {
            await login(form.username.trim(), form.user_password);
            navigate('/');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#fafafa] dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex items-center justify-center px-6 py-10 relative">
            <div className="absolute top-4 right-4">
                <ThemeToggle />
            </div>
            <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                <div className="hidden lg:block">
                    <div className="relative w-[360px] h-[640px] mx-auto drop-shadow-2xl">
                        <div className="absolute inset-0 bg-gradient-to-tr from-[#f58529] via-[#dd2a7b] to-[#515bd4] rounded-[40px] opacity-80" />
                        <div className="absolute inset-[14px] bg-black rounded-[32px] overflow-hidden border-4 border-black/40">
                            <div className="absolute top-0 inset-x-0 h-10 bg-black/60 backdrop-blur" />
                            <img
                                src="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=800&q=80"
                                alt="Stories preview"
                                className="w-full h-full object-cover"
                            />
                        </div>
                    </div>
                </div>

                <div className="max-w-sm w-full mx-auto space-y-4">
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg px-10 py-8 text-center shadow-sm">
                        <h1 className="text-4xl font-black gradient-text mb-6">uGram</h1>
                        <form className="space-y-3" onSubmit={handleSubmit}>
                            <input
                                type="text"
                                placeholder="Username"
                                value={form.username}
                                onChange={(e) => setForm((prev) => ({ ...prev, username: e.target.value }))}
                                className="input"
                                required
                                autoFocus
                            />
                            <input
                                type="password"
                                placeholder="Password"
                                value={form.user_password}
                                onChange={(e) => setForm((prev) => ({ ...prev, user_password: e.target.value }))}
                                className="input"
                                required
                            />
                            {error && <p className="text-xs text-red-500">{error}</p>}
                            <button
                                type="submit"
                                className="btn btn-primary w-full"
                                disabled={submitting || loading}
                            >
                                {submitting || loading ? 'Logging in…' : 'Log In'}
                            </button>
                        </form>
                        <div className="mt-6 text-sm text-gray-500 dark:text-gray-400">OR</div>
                        <GoogleButton text="Continue with Google" />
                        <button
                            type="button"
                            className="mt-2 text-xs text-gray-500 dark:text-gray-400 underline underline-offset-4 hover:text-gray-700 dark:hover:text-gray-200"
                        >
                            Forgot password?
                        </button>
                    </div>

                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg px-10 py-4 text-center shadow-sm text-sm">
                        Don&apos;t have an account?{' '}
                        <Link to="/signup" className="text-[#0095f6] font-semibold hover:text-[#0077c7]">
                            Sign up
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
