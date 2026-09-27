export default function FeedSkeleton() {
    return (
        <div className="space-y-6">
            {Array.from({ length: 3 }).map((_, idx) => (
                <div
                    key={idx}
                    className="bg-white dark:bg-gray-900 rounded-2xl shadow-soft-sm border border-gray-100 dark:border-gray-800 overflow-hidden animate-pulse"
                >
                    <div className="p-4 flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700" />
                        <div className="flex-1">
                            <div className="h-3 w-28 bg-gray-200 dark:bg-gray-700 rounded" />
                            <div className="h-2 w-20 bg-gray-200 dark:bg-gray-700 rounded mt-2" />
                        </div>
                    </div>
                    <div className="aspect-square bg-gray-200 dark:bg-gray-700" />
                    <div className="p-4">
                        <div className="h-3 w-full bg-gray-200 dark:bg-gray-700 rounded" />
                        <div className="h-3 w-2/3 bg-gray-200 dark:bg-gray-700 rounded mt-2" />
                    </div>
                </div>
            ))}
        </div>
    );
}
