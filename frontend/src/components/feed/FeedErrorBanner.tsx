interface FeedErrorBannerProps {
    message: string;
    onRetry: () => void;
}

export default function FeedErrorBanner({ message, onRetry }: FeedErrorBannerProps) {
    return (
        <div className="bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 p-4 rounded-xl mb-6 text-sm flex items-center justify-between gap-3">
            <span>{message}</span>
            <button type="button" className="btn btn-secondary text-xs" onClick={onRetry}>
                Retry
            </button>
        </div>
    );
}
