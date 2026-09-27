import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useNotificationContext } from '../../context/NotificationContext';
import ThemeToggle from '../ThemeToggle';
import SearchBar from '../SearchBar';
import HeaderAvatar from './HeaderAvatar';
import NotificationPanel from '../notifications/NotificationPanel';

type HeaderProps = {
    appName: string;
    keyword?: string;
    setKeyword?: (keyword: string) => void;
    defaultSearchType?: 'people' | 'images';
};

export default function Header({ appName, keyword, setKeyword, defaultSearchType }: HeaderProps) {
    const { user, logout } = useAuth();
    const { notifications, unreadCount, markAsRead } = useNotificationContext();
    const [menuOpen, setMenuOpen] = React.useState(false);
    const [searchOpen, setSearchOpen] = React.useState(false);
    const [isNotificationPanelOpen, setIsNotificationPanelOpen] = React.useState(false);
    const menuRef = React.useRef<HTMLDivElement>(null);
    const notificationPanelRef = React.useRef<HTMLDivElement>(null);

    React.useEffect(() => {
        if (!menuOpen) return;
        const onClick = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setMenuOpen(false);
            }
        };
        document.addEventListener('mousedown', onClick);
        return () => document.removeEventListener('mousedown', onClick);
    }, [menuOpen]);

    React.useEffect(() => {
        if (!isNotificationPanelOpen) return;
        const onClick = (e: MouseEvent) => {
            if (notificationPanelRef.current && !notificationPanelRef.current.contains(e.target as Node)) {
                setIsNotificationPanelOpen(false);
            }
        };
        document.addEventListener('mousedown', onClick);
        return () => document.removeEventListener('mousedown', onClick);
    }, [isNotificationPanelOpen]);

    return (
        <header className="bg-white/95 dark:bg-gray-900/90 backdrop-blur-md border-b border-gray-200 dark:border-gray-800 py-4 sticky top-0 z-50">
            <div className="container-custom">
                <div className="flex justify-between items-center gap-4">
                    <div className="flex items-center gap-8 flex-1 min-w-0">
                        <Link to="/" className="shrink-0">
                            <h1 className="text-3xl font-bold gradient-text tracking-tight">{appName}</h1>
                        </Link>
                        <SearchBar
                            value={keyword}
                            onChange={setKeyword}
                            onExpandChange={setSearchOpen}
                            defaultSearchType={defaultSearchType}
                        />
                    </div>
                    <div className={`flex-1 items-center gap-3 ${searchOpen ? 'hidden sm:flex' : 'flex'}`}>
                        <nav className="flex gap-2">
                            <div className="hidden sm:block">
                                <ThemeToggle />
                            </div>
                            <Link to="/" className="p-2 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all hover:scale-105" aria-label="Home">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            </Link>
                            <Link to="/users" className="p-2 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all hover:scale-105" aria-label="Users">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                    <circle cx="9" cy="7" r="4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M23 21v-2a4 4 0 0 0-3-3.87" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                    <path d="M16 3.13a4 4 0 0 1 0 7.75" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                </svg>
                            </Link>
                            {user ? (
                                <div className="relative" ref={notificationPanelRef}>
                                    <button
                                        className="p-2 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all hover:scale-105 relative"
                                        aria-label="Notifications"
                                        onClick={() => setIsNotificationPanelOpen((isOpen) => !isOpen)}
                                    >
                                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                            <path d="M13.73 21a2 2 0 0 1-3.46 0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                        </svg>
                                        {unreadCount > 0 ? (
                                            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500" />
                                        ) : null}
                                    </button>
                                    {isNotificationPanelOpen ? (
                                        <NotificationPanel
                                            notifications={notifications}
                                            onMarkAsRead={markAsRead}
                                            onClose={() => setIsNotificationPanelOpen(false)}
                                        />
                                    ) : null}
                                </div>
                            ) : null}
                        </nav>
                        {user ? (
                            <div className="flex items-center gap-1" ref={menuRef}>
                                <Link to={`/profile/${user.id}`} className="transition-transform hover:scale-105 shrink-0">
                                    <HeaderAvatar user={user} />
                                </Link>
                                <div className="relative sm:hidden">
                                    <button
                                        className="p-2 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all"
                                        aria-label="Open menu"
                                        aria-haspopup="menu"
                                        aria-expanded={menuOpen}
                                        onClick={() => setMenuOpen((v) => !v)}
                                    >
                                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                            <line x1="3" y1="6" x2="21" y2="6" strokeWidth="2" strokeLinecap="round" />
                                            <line x1="3" y1="12" x2="21" y2="12" strokeWidth="2" strokeLinecap="round" />
                                            <line x1="3" y1="18" x2="21" y2="18" strokeWidth="2" strokeLinecap="round" />
                                        </svg>
                                    </button>
                                    {menuOpen ? (
                                        <div
                                            role="menu"
                                            className="absolute right-0 mt-2 w-44 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-lg p-2 z-50"
                                        >
                                            <div className="px-2 py-1">
                                                <ThemeToggle />
                                            </div>
                                            <button
                                                className="w-full text-left px-3 py-2 rounded-lg text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                                                onClick={() => {
                                                    setMenuOpen(false);
                                                    logout();
                                                }}
                                            >
                                                Log out
                                            </button>
                                        </div>
                                    ) : null}
                                </div>
                                <button className="btn btn-secondary text-sm hidden sm:block" onClick={logout}>
                                    Log out
                                </button>
                            </div>
                        ) : null}
                    </div>
                </div>
            </div>
        </header>
    );
}
