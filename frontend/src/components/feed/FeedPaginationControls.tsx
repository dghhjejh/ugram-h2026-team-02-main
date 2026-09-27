interface FeedPaginationControlsProps {
    hasMore: boolean;
    isFetchingNextPage: boolean;
    onLoadMore: () => void;
}

export default function FeedPaginationControls({
    hasMore,
    isFetchingNextPage,
    onLoadMore,
}: FeedPaginationControlsProps) {
    return (
        <>
            {isFetchingNextPage && (
                <div className="flex justify-center py-6">
                    <div className="spinner" />
                </div>
            )}

            {hasMore && !isFetchingNextPage && (
                <div className="flex justify-center py-6">
                    <button type="button" className="btn btn-secondary" onClick={onLoadMore}>
                        Load more
                    </button>
                </div>
            )}
        </>
    );
}
