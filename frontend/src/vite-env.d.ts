/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_API_URL?: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}

declare const __SENTRY_FRONTEND_DSN__: string;
declare const __SENTRY_ENVIRONMENT__: string;
declare const __SENTRY_RELEASE__: string;
declare const __SENTRY_TRACES_SAMPLE_RATE__: string;
declare const __SENTRY_REPLAYS_SESSION_SAMPLE_RATE__: string;
declare const __SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE__: string;
