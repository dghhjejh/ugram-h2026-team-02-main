import type { SetStateAction } from 'react';

interface TabsProps {
    activeTab: 'posts' | 'saved';
    setActiveTab: (value: SetStateAction<'posts' | 'saved'>) => void;
}

export default function Tabs({activeTab, setActiveTab}:TabsProps){
    return (
        <div className="flex justify-center gap-16">
            <button
                className={`flex items-center gap-2 py-4 border-t -mt-px text-xs font-semibold tracking-wider transition-all ${activeTab === 'posts'
                    ? 'text-gray-900 dark:text-gray-50 border-gray-900 dark:border-gray-200'
                    : 'text-gray-400 dark:text-gray-500 border-transparent hover:text-gray-700 dark:hover:text-gray-200'
                    }`}
                onClick={() => setActiveTab('posts')}
            >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="3" y="3" width="7" height="7" />
                    <rect x="14" y="3" width="7" height="7" />
                    <rect x="3" y="14" width="7" height="7" />
                    <rect x="14" y="14" width="7" height="7" />
                </svg>
                <span>POSTS</span>
            </button>
            <button
                className={`flex items-center gap-2 py-4 border-t -mt-px text-xs font-semibold tracking-wider transition-all ${activeTab === 'saved'
                    ? 'text-gray-900 dark:text-gray-50 border-gray-900 dark:border-gray-200'
                    : 'text-gray-400 dark:text-gray-500 border-transparent hover:text-gray-700 dark:hover:text-gray-200'
                    }`}
                onClick={() => setActiveTab('saved')}
            >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" strokeWidth="2" />
                </svg>
                <span>SAVED</span>
            </button>
        </div>
    )
}
