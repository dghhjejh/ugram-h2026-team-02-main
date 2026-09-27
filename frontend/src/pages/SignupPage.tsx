import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import GoogleButton from '../components/GoogleButton';
import ThemeToggle from '../components/ThemeToggle';
import type { CreateUserRequest } from '../types/api';

export default function SignupPage() {
    const navigate = useNavigate();
    const { signup, loading, error, clearError, user } = useAuth();
    const [form, setForm] = useState<Pick<CreateUserRequest, 'email' | 'username' | 'user_password'> & { fullName: string; phone_number?: string; profile_photo_url?: string }>({
        email: '',
        fullName: '',
        username: '',
        user_password: '',
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (user) {
            navigate('/');
        }
    }, [user, navigate]);

    const handleChange = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => {
        setForm((prev) => ({ ...prev, [field]: e.target.value }));
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        clearError();
        setSubmitting(true);
        const [first_name, ...rest] = form.fullName.trim().split(' ');
        const last_name = rest.join(' ') || 'User';
        try {
            await signup({
                email: form.email.trim(),
                username: form.username.trim(),
                first_name,
                last_name,
                user_password: form.user_password,
            });
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
                                src="https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?auto=format&fit=crop&w=800&q=80"
                                alt="Social preview"
                                className="w-full h-full object-cover"
                            />
                        </div>
                    </div>
                </div>

                <div className="max-w-sm w-full mx-auto space-y-4">
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg px-10 py-8 text-center shadow-sm space-y-4">
                        <h1 className="text-4xl font-black gradient-text">uGram</h1>
                        <p className="text-sm text-gray-500">
                            Sign up to see photos and videos from your friends.
                        </p>
                        <form className="space-y-3" onSubmit={handleSubmit}>
                            <input
                                type="email"
                                placeholder="Email"
                                value={form.email}
                                onChange={handleChange('email')}
                                className="input"
                                required
                            />
                            <input
                                type="text"
                                placeholder="Full Name"
                                value={form.fullName}
                                onChange={handleChange('fullName')}
                                className="input"
                                required
                            />
                            <input
                                type="text"
                                placeholder="Username"
                                value={form.username}
                                onChange={handleChange('username')}
                                className="input"
                                required
                            />
                            <input
                                type="password"
                                placeholder="Password"
                                value={form.user_password}
                                onChange={handleChange('user_password')}
                                className="input"
                                required
                                minLength={8}
                            />
                            {error && <p className="text-xs text-red-500">{error}</p>}
                            <p className="text-[11px] text-gray-500 dark:text-gray-400 leading-relaxed">
                                People who use our service may have uploaded your contact information to
                                uGram. By signing up, you agree to our Terms, Privacy Policy and Cookies.
                            </p>
                            <button
                                type="submit"
                                className="btn btn-primary w-full"
                                disabled={submitting || loading}
                            >
                                {submitting || loading ? 'Signing up…' : 'Sign Up'}
                            </button>
                        </form>
                        <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">OR</div>
                        <GoogleButton text="Sign up with Google" />
                    </div>
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg px-10 py-4 text-center shadow-sm text-sm">
                        Have an account?{' '}
                        <Link to="/login" className="text-[#0095f6] font-semibold hover:text-[#0077c7]">
                            Log in
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
