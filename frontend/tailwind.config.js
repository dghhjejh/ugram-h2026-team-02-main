/** @type {import('tailwindcss').Config} */
export default {
    darkMode: 'class',
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                // Green plant vibe color palette
                primary: {
                    50: '#f0fdf4',
                    100: '#dcfce7',
                    200: '#bbf7d0',
                    300: '#86efac',
                    400: '#4ade80',
                    500: '#22c55e',
                    600: '#16a34a',
                    700: '#15803d',
                    800: '#166534',
                    900: '#14532d',
                },
                forest: {
                    50: '#f5f8f5',
                    100: '#e8f0e8',
                    200: '#d1e2d1',
                    300: '#a8c9a8',
                    400: '#7aad7a',
                    500: '#5a9359',
                    600: '#457845',
                    700: '#366036',
                    800: '#2d4e2d',
                    900: '#264026',
                },
                sage: {
                    50: '#f6f7f6',
                    100: '#e3e8e3',
                    200: '#c7d1c7',
                    300: '#a0b3a0',
                    400: '#7a947a',
                    500: '#5f7a5f',
                    600: '#4a614a',
                    700: '#3d4f3d',
                    800: '#334133',
                    900: '#2b362b',
                },
                mint: {
                    50: '#f0fdf9',
                    100: '#ccfbef',
                    200: '#99f6e0',
                    300: '#5fe9ce',
                    400: '#2dd4b8',
                    500: '#14b8a0',
                    600: '#0d9488',
                    700: '#0f766e',
                    800: '#115e59',
                    900: '#134e4a',
                },
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
            },
            boxShadow: {
                'soft': '0 2px 8px rgba(34, 197, 94, 0.08)',
                'soft-md': '0 4px 12px rgba(34, 197, 94, 0.12)',
                'soft-lg': '0 8px 24px rgba(34, 197, 94, 0.15)',
                'soft-xl': '0 16px 48px rgba(34, 197, 94, 0.2)',
            },
            backgroundImage: {
                'gradient-primary': 'linear-gradient(135deg, #22c55e 0%, #15803d 100%)',
                'gradient-forest': 'linear-gradient(135deg, #5a9359 0%, #366036 100%)',
                'gradient-mint': 'linear-gradient(135deg, #14b8a0 0%, #0d9488 100%)',
                'gradient-nature': 'linear-gradient(135deg, #86efac 0%, #22c55e 50%, #15803d 100%)',
            },
            animation: {
                'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
                'fade-in': 'fade-in 0.35s ease-out',
            },
            keyframes: {
                'pulse-soft': {
                    '0%, 100%': { boxShadow: '0 0 0 0 rgba(34, 197, 94, 0.4)' },
                    '50%': { boxShadow: '0 0 0 8px rgba(34, 197, 94, 0)' },
                },
                'fade-in': {
                    '0%': { opacity: '0', transform: 'translateY(20px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
            },
        },
    },
    plugins: [],
}
