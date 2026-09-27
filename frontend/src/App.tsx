import { BrowserRouter, Navigate, Outlet, Route } from 'react-router-dom';
import FeedPage from './pages/FeedPage';
import ProfilePage from './pages/ProfilePage';
import UsersPage from './pages/UsersPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import GoogleCallbackPage from './pages/GoogleCallbackPage';
import GoogleRegisterPage from './pages/GoogleRegisterPage';
import SearchImagesPage from './pages/SearchImagesPage';
import SearchUsersPage from './pages/SearchUsersPage';
import { useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { SentryRoutes } from './monitoring/sentry';
import './App.css';

function ProtectedRoute() {
    const { user, loading } = useAuth();

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen gap-5">
                <div className="spinner" />
                <p className="text-gray-500 text-sm">Loading…</p>
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/login" replace />;
    }

    return <NotificationProvider><Outlet /></NotificationProvider>;
}

function App() {
    return (
        <BrowserRouter>
            <SentryRoutes>
                <Route element={<ProtectedRoute />}>
                    <Route path="/" element={<FeedPage />} />
                    <Route path="/feed" element={<FeedPage />} />
                    <Route path="/profile" element={<ProfilePage />} />
                    <Route path="/profile/:userId" element={<ProfilePage />} />
                    <Route path="/users" element={<UsersPage />} />
                    <Route path="/search" element={<SearchUsersPage />} />
                    <Route path="/search/images/:hashtag" element={<SearchImagesPage />} />
                    <Route path="/search/description/:keyword" element={<SearchImagesPage />} />
                </Route>

                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
                <Route path="/auth/callback" element={<GoogleCallbackPage />} />
                <Route path="/register" element={<GoogleRegisterPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
            </SentryRoutes>
        </BrowserRouter>
    );
}

export default App;
