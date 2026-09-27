import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { setSentryUser } from '../monitoring/sentry';
import type { PrivateUserProfile, GoogleRegisterRequest } from '../types/api';
import { apiClient, API_BASE } from '../services/api';

const TOKEN_STORAGE_KEY = 'ugram_token';
const REFRESH_BEFORE_EXPIRY_MS = 2 * 60 * 1000; // refresh 2 min before expiry

function getTokenExpiry(token: string): number | null {
    try {
        const base64url = token.split('.')[1];
        const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/').padEnd(
            base64url.length + (4 - (base64url.length % 4)) % 4, '='
        );
        const payload = JSON.parse(atob(base64));
        return typeof payload.exp === 'number' ? payload.exp * 1000 : null;
    } catch {
        return null;
    }
}

type RegisterPayload = {
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    user_password: string;
    phone_number?: string;
    profile_photo_url?: string;
};

type AuthContextValue = {
    user: PrivateUserProfile | null;
    token: string | undefined;
    loading: boolean;
    error: string | null;
    login: (username: string, password: string) => Promise<void>;
    signup: (payload: RegisterPayload) => Promise<void>;
    startGoogleLogin: () => void;
    completeGoogleRegistration: (payload: GoogleRegisterRequest) => Promise<void>;
    acceptExternalToken: (token: string) => Promise<void>;
    updateUser: (updatedUser: PrivateUserProfile) => void;
    logout: () => void;
    clearError: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<PrivateUserProfile | null>(null);
    const [token, setToken] = useState<string | undefined>(() => localStorage.getItem(TOKEN_STORAGE_KEY) ?? undefined);
    const lastFetchedToken = useRef<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setSentryUser(user);
    }, [user]);
    const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const persistToken = useCallback((value: string | undefined) => {
        if (value) {
            localStorage.setItem(TOKEN_STORAGE_KEY, value);
        } else {
            localStorage.removeItem(TOKEN_STORAGE_KEY);
        }
        setToken(value);
    }, []);

    const scheduleRefresh = useCallback((accessToken: string) => {
        if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
        const expiry = getTokenExpiry(accessToken);
        if (!expiry) return;
        const delay = expiry - Date.now() - REFRESH_BEFORE_EXPIRY_MS;
        if (delay <= 0) return;
        refreshTimerRef.current = setTimeout(async () => {
            try {
                const res = await apiClient.refreshToken();
                persistToken(res.access_token);
                scheduleRefresh(res.access_token);
            } catch {
                persistToken(undefined);
                setUser(null);
            }
        }, delay);
    }, [persistToken]);

    const fetchCurrentUser = useCallback(
        async (authToken?: string) => {
            const currentUser = await apiClient.getCurrentUser(authToken);
            setUser(currentUser);
            lastFetchedToken.current = authToken ?? null;
        },
        [],
    );

    useEffect(() => {
        const bootstrap = async () => {
            setLoading(true);
            if (!token) {
                setLoading(false);
                return;
            }
            if (lastFetchedToken.current === token) {
                setLoading(false);
                return;
            }
            try {
                await fetchCurrentUser(token ?? undefined);
                scheduleRefresh(token);
            } catch {
                try {
                    const res = await apiClient.refreshToken();
                    persistToken(res.access_token);
                    await fetchCurrentUser(res.access_token);
                    scheduleRefresh(res.access_token);
                } catch {
                    persistToken(undefined);
                    setUser(null);
                }
            } finally {
                setLoading(false);
            }
        };

        bootstrap();
    }, [token, fetchCurrentUser, persistToken, scheduleRefresh]);

    const login = useCallback(
        async (username: string, password: string) => {
            setError(null);
            setLoading(true);
            try {
                const res = await apiClient.login({ username, user_password: password });
                persistToken(res.access_token);
                await fetchCurrentUser(res.access_token);
                scheduleRefresh(res.access_token);
            } catch (err) {
                setUser(null);
                setError(err instanceof Error ? err.message : 'Login failed');
                throw err;
            } finally {
                setLoading(false);
            }
        },
        [fetchCurrentUser, persistToken, scheduleRefresh],
    );

    const signup = useCallback(
        async (payload: RegisterPayload) => {
            setError(null);
            setLoading(true);
            try {
                await apiClient.registerUser(payload);
                const res = await apiClient.login({
                    username: payload.username,
                    user_password: payload.user_password,
                });
                persistToken(res.access_token);
                await fetchCurrentUser(res.access_token);
                scheduleRefresh(res.access_token);
            } catch (err) {
                setUser(null);
                setError(err instanceof Error ? err.message : 'Signup failed');
                throw err;
            } finally {
                setLoading(false);
            }
        },
        [fetchCurrentUser, persistToken, scheduleRefresh],
    );

    const startGoogleLogin = useCallback(() => {
        window.location.href = `${API_BASE}/auth/google/login`;
    }, []);

    const acceptExternalToken = useCallback(
        async (externalToken: string) => {
            setError(null);
            setLoading(true);
            try {
                persistToken(externalToken);
                await fetchCurrentUser(externalToken);
                scheduleRefresh(externalToken);
            } catch (err) {
                setUser(null);
                setError(err instanceof Error ? err.message : 'Authentication failed');
                throw err;
            } finally {
                setLoading(false);
            }
        },
        [fetchCurrentUser, persistToken, scheduleRefresh],
    );

    const completeGoogleRegistration = useCallback(
        async (payload: GoogleRegisterRequest) => {
            setError(null);
            setLoading(true);
            try {
                const res = await apiClient.completeGoogleRegistration(payload);
                persistToken(res.access_token);
                await fetchCurrentUser(res.access_token);
                scheduleRefresh(res.access_token);
            } catch (err) {
                setUser(null);
                setError(err instanceof Error ? err.message : 'Google registration failed');
                throw err;
            } finally {
                setLoading(false);
            }
        },
        [fetchCurrentUser, persistToken, scheduleRefresh],
    );

    const logout = useCallback(() => {
        if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
        persistToken(undefined);
        setUser(null);
        apiClient.logout().catch(() => undefined);
    }, [persistToken]);

    const updateUser = useCallback((updatedUser: PrivateUserProfile) => {
        setUser(updatedUser);
    }, []);

    const clearError = useCallback(() => setError(null), []);

    const value = useMemo(
        () => ({
            user,
            token,
            loading,
            error,
            login,
            signup,
            startGoogleLogin,
            completeGoogleRegistration,
            acceptExternalToken,
            updateUser,
            logout,
            clearError,
        }),
        [
            user,
            token,
            loading,
            error,
            login,
            signup,
            startGoogleLogin,
            completeGoogleRegistration,
            acceptExternalToken,
            updateUser,
            logout,
            clearError,
        ],
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
    const ctx = useContext(AuthContext);
    if (!ctx) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return ctx;
}
