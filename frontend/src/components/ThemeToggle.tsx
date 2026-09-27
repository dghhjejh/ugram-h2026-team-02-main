import { useTheme } from '../context/ThemeContext';

export default function ThemeToggle() {
    const { theme, toggleTheme } = useTheme();
    const isDark = theme === 'dark';

    return (
        <button
            type="button"
            aria-label="Toggle dark mode"
            onClick={toggleTheme}
            className="p-2 rounded-full border border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-800/80 shadow-sm hover:shadow-md transition-all"
        >
            {isDark ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" strokeWidth="2" />
                </svg>
            ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <circle cx="12" cy="12" r="5" strokeWidth="2" />
                    <path d="M12 1v2M12 21v2M4.22 4.22 5.64 5.64M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78 5.64 18.36M18.36 5.64 19.78 4.22" strokeWidth="2" />
                </svg>
            )}
        </button>
    );
}
