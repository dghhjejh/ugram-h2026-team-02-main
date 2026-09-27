import * as Sentry from '@sentry/react';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.tsx';
import AppErrorFallback from './components/AppErrorFallback';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { initializeSentry } from './monitoring/sentry';

initializeSentry();

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <Sentry.ErrorBoundary fallback={<AppErrorFallback />}>
            <ThemeProvider>
                <AuthProvider>
                    <App />
                </AuthProvider>
            </ThemeProvider>
        </Sentry.ErrorBoundary>
    </StrictMode>,
);
