interface FeedHeaderProps {
    count: number;
}

export default function FeedHeader({ count }: FeedHeaderProps) {
    return (
        <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Feed</h2>
            <span className="text-xs font-medium text-gray-500 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded-full">
                {count} posts
            </span>
        </div>
    );
}
