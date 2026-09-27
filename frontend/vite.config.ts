import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { sentryVitePlugin } from '@sentry/vite-plugin'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const frontendDir = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(frontendDir, '..')

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, repoRoot, '')
  const sentryFrontendDsn = env.SENTRY_FRONTEND_DSN || env.VITE_SENTRY_DSN || ''
  const sentryEnvironment = env.SENTRY_ENVIRONMENT || env.VITE_SENTRY_ENVIRONMENT || ''
  const sentryTracesSampleRate =
    env.SENTRY_TRACES_SAMPLE_RATE || env.VITE_SENTRY_TRACES_SAMPLE_RATE || ''
  const sentryReplaysSessionSampleRate =
    env.SENTRY_REPLAYS_SESSION_SAMPLE_RATE || env.VITE_SENTRY_REPLAYS_SESSION_SAMPLE_RATE || ''
  const sentryReplaysOnErrorSampleRate =
    env.SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE || env.VITE_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE || ''
  const sentryAuthToken = env.SENTRY_AUTH_TOKEN
  const sentryOrg = env.SENTRY_ORG
  const sentryProject = env.SENTRY_PROJECT
  const sentryRelease = env.SENTRY_RELEASE || env.VITE_SENTRY_RELEASE
  const hasSentryBuildConfig = Boolean(sentryAuthToken && sentryOrg && sentryProject)

  return {
    envDir: repoRoot,
    build: {
      sourcemap: hasSentryBuildConfig ? 'hidden' : false,
    },
    define: {
      __SENTRY_FRONTEND_DSN__: JSON.stringify(sentryFrontendDsn),
      __SENTRY_ENVIRONMENT__: JSON.stringify(sentryEnvironment),
      __SENTRY_RELEASE__: JSON.stringify(sentryRelease || ''),
      __SENTRY_TRACES_SAMPLE_RATE__: JSON.stringify(sentryTracesSampleRate),
      __SENTRY_REPLAYS_SESSION_SAMPLE_RATE__: JSON.stringify(sentryReplaysSessionSampleRate),
      __SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE__: JSON.stringify(sentryReplaysOnErrorSampleRate),
    },
    plugins: [
      react(),
      ...(hasSentryBuildConfig
        ? [
            sentryVitePlugin({
              authToken: sentryAuthToken,
              org: sentryOrg!,
              project: sentryProject!,
              ...(sentryRelease ? { release: { name: sentryRelease } } : {}),
              sourcemaps: {
                filesToDeleteAfterUpload: ['./dist/**/*.map'],
              },
            }),
          ]
        : []),
    ],
  }
})
