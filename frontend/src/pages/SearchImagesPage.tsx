import { useNavigate, useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { apiClient } from '../services/api';
import type { Image } from '../types/api';
import Header from '../components/profile/Header';
import ImagesGrid from "../components/profile/ImagesGrid.tsx";
import { useAuth } from '../context/AuthContext';
import { X } from 'lucide-react';

export default function SearchImagesPage() {
    const { token } = useAuth();
    const navigate = useNavigate();
    const { hashtag, keyword } = useParams<{ hashtag?: string; keyword?: string }>();

    const isHashtagSearch = !!hashtag;
    const searchTerm = hashtag ?? keyword ?? '';
    const title = isHashtagSearch ? `#${searchTerm}` : `"${searchTerm}"`;

    const [images, setImages] = useState<Image[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!searchTerm) return;
        let cancelled = false;

        const request = isHashtagSearch
            ? apiClient.getImagesByHashtag(searchTerm, token)
            : apiClient.getImageByDescriptionKeyword(searchTerm, token);

        request
            .then((data) => {
                if (!cancelled) {
                    setImages(data.images);
                    setError(null);
                    setLoading(false);
                }
            })
            .catch(() => {
                if (!cancelled) {
                    setError('Failed to load images');
                    setLoading(false);
                }
            });

        return () => {
            cancelled = true;
        };
    }, [searchTerm, isHashtagSearch, token]);
    return (
        <>
            <Header appName="uGram" />
            <div className="min-h-screen bg-gray-50 dark:bg-gray-950 dark:text-gray-100 fade-in">
                <div className="container-custom py-10">
                    <div className="flex items-center gap-2 mb-6">
                        <h2 className="text-2xl font-bold">
                            Search results for {title}
                        </h2>
                        <button
                            onClick={() => navigate(-1)}
                            className="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors"
                            aria-label="Back"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                    {loading && (
                        <div className="flex flex-col items-center justify-center py-20 gap-4">
                            <div className="spinner" />
                            <p className="text-gray-500 text-sm">Searching…</p>
                        </div>
                    )}
                    {error && (
                        <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-4 rounded-xl text-sm">
                            {error}
                        </div>
                    )}
                    {!loading && !error && (
                        images.length === 0
                            ? <p className="text-gray-500 text-sm">No images found.</p>
                            : <ImagesGrid images={images} activeTab={"posts"} onImageDeleted={() => {}}/>
                    )}
                </div>
            </div>
        </>
    );
}
