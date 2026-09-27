import { useEffect } from 'react';
import * as Sentry from '@sentry/react';
import {
    Routes,
    createRoutesFromChildren,
    matchRoutes,
    useLocation,
    useNavigationType,
} from 'react-router-dom';
import type { PrivateUserProfile } from '../types/api';
import { API_BASE, getTracePropagationTargets } from '../services/api';

const DEFAULT_DEV_TRACES_SAMPLE_RATE = 1.0;
const DEFAULT_PROD_TRACES_SAMPLE_RATE = 0.1;
const DEFAULT_DEV_REPLAYS_SESSION_SAMPLE_RATE = 1.0;
const DEFAULT_PROD_REPLAYS_SESSION_SAMPLE_RATE = 0.0;
const DEFAULT_REPLAYS_ON_ERROR_SAMPLE_RATE = 1.0;
const REDACTED = '[Filtered]';
const SENSITIVE_KEY_TOKENS = [
    'authorization',
    'cookie',
    'apikey',
    'token',
    'secret',
    'password',
    'session',
    'csrf',
    'xsrf',
];
const URL_KEY_TOKENS = ['url', 'href', 'location', 'requesturl'];

let isInitialized = false;

function parseSampleRate(value: string | undefined, fallback: number): number {
    if (!value) {
        return fallback;
    }

    const parsed = Number.parseFloat(value);
    if (Number.isNaN(parsed) || parsed < 0 || parsed > 1) {
        return fallback;
    }

    return parsed;
}

function normalizeKey(key: string): string {
    return key.toLowerCase().replace(/[^a-z0-9]/g, '');
}

function isSensitiveKey(key: string): boolean {
    const normalizedKey = normalizeKey(key);
    return SENSITIVE_KEY_TOKENS.some((token) => normalizedKey.includes(token));
}

function isUrlKey(key: string): boolean {
    const normalizedKey = normalizeKey(key);
    return URL_KEY_TOKENS.some((token) => normalizedKey === token || normalizedKey.endsWith(token));
}

function stripQueryAndFragment(url: string): string {
    try {
        const parsedUrl = new URL(url, window.location.origin);
        parsedUrl.search = '';
        parsedUrl.hash = '';
        return url.startsWith('/') ? parsedUrl.pathname : parsedUrl.toString();
    } catch {
        return url.replace(/[?#].*$/, '');
    }
}

function scrubValue(value: unknown, key?: string): unknown {
    if (key && isSensitiveKey(key)) {
        return REDACTED;
    }

    if (Array.isArray(value)) {
        return value.map((item) => scrubValue(item, key));
    }

    if (value && typeof value === 'object') {
        return Object.fromEntries(
            Object.entries(value as Record<string, unknown>).map(([childKey, childValue]) => {
                if (isSensitiveKey(childKey)) {
                    return [childKey, REDACTED];
                }

                if (typeof childValue === 'string' && isUrlKey(childKey)) {
                    return [childKey, stripQueryAndFragment(childValue)];
                }

                return [childKey, scrubValue(childValue, childKey)];
            }),
        );
    }

    if (typeof value === 'string' && key && isUrlKey(key)) {
        return stripQueryAndFragment(value);
    }

    return value;
}

function scrubSentryPayload<T>(payload: T): T {
    return scrubValue(payload) as T;
}

export function initializeSentry(): void {
    if (isInitialized || !__SENTRY_FRONTEND_DSN__) {
        return;
    }

    Sentry.init({
        dsn: __SENTRY_FRONTEND_DSN__,
        environment: __SENTRY_ENVIRONMENT__ || import.meta.env.MODE,
        release: __SENTRY_RELEASE__ || undefined,
        integrations: [
            Sentry.reactRouterV7BrowserTracingIntegration({
                useEffect,
                useLocation,
                useNavigationType,
                createRoutesFromChildren,
                matchRoutes,
            }),
            Sentry.replayIntegration({
                maskAllText: true,
                blockAllMedia: true,
                beforeAddRecordingEvent: (event) => scrubSentryPayload(event),
            }),
        ],
        tracesSampleRate: parseSampleRate(
            __SENTRY_TRACES_SAMPLE_RATE__,
            import.meta.env.DEV ? DEFAULT_DEV_TRACES_SAMPLE_RATE : DEFAULT_PROD_TRACES_SAMPLE_RATE,
        ),
        replaysSessionSampleRate: parseSampleRate(
            __SENTRY_REPLAYS_SESSION_SAMPLE_RATE__,
            import.meta.env.DEV
                ? DEFAULT_DEV_REPLAYS_SESSION_SAMPLE_RATE
                : DEFAULT_PROD_REPLAYS_SESSION_SAMPLE_RATE,
        ),
        replaysOnErrorSampleRate: parseSampleRate(
            __SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE__,
            DEFAULT_REPLAYS_ON_ERROR_SAMPLE_RATE,
        ),
        tracePropagationTargets: getTracePropagationTargets(API_BASE),
        normalizeDepth: 6,
        beforeSend: (event) => scrubSentryPayload(event),
        beforeSendTransaction: (event) => scrubSentryPayload(event),
        beforeBreadcrumb: (breadcrumb) => scrubSentryPayload(breadcrumb),
    });

    isInitialized = true;
}

export function setSentryUser(user: PrivateUserProfile | null): void {
    Sentry.setUser(
        user
            ? {
                id: user.id,
                username: user.username,
            }
            : null,
    );
}

export const SentryRoutes = Sentry.withSentryReactRouterV7Routing(Routes);
