export default function AppErrorFallback() {
    return (
        <div className="min-h-screen bg-[#fafafa] dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex items-center justify-center px-6">
            <div className="max-w-md w-full rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-8 shadow-sm text-center space-y-4">
                <h1 className="text-2xl font-black">Something went wrong</h1>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                    The error has been captured. Reload the page to retry.
                </p>
                <button className="btn btn-primary w-full" onClick={() => window.location.reload()} type="button">
                    Reload
                </button>
            </div>
        </div>
    );
}
