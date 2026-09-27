export type FilterType = 'none' | 'bw' | 'sepia' | 'saturated' | 'cool' | 'warm' | 'vintage' | 'noir';

export interface FilterDefinition {
    id: FilterType;
    name: string;
    filter: string;
}

const IMAGE_COMPRESSION_CONFIG = {
    quality: 0.95,
    description: 'High quality with minimal file size.',
} as const;

export const FILTERS: FilterDefinition[] = [
    { id: 'none', name: 'Original', filter: 'none' },
    { id: 'bw', name: 'Black & White', filter: 'grayscale(100%)' },
    { id: 'sepia', name: 'Sepia', filter: 'sepia(100%)' },
    { id: 'saturated', name: 'Vibrant', filter: 'saturate(1.5) contrast(1.1)' },
    { id: 'cool', name: 'Cool', filter: 'hue-rotate(200deg) saturate(1.1) brightness(0.95)' },
    { id: 'warm', name: 'Warm', filter: 'hue-rotate(15deg) saturate(1.2) brightness(1.05)' },
    { id: 'vintage', name: 'Vintage', filter: 'sepia(70%) saturate(0.8) contrast(0.9)' },
    { id: 'noir', name: 'Noir', filter: 'grayscale(100%) contrast(1.8) brightness(0.8)' },
];

export function getFilterCSS(filterType: FilterType): string {
    const filterDef = FILTERS.find((f) => f.id === filterType);
    return filterDef?.filter || 'none';
}

export async function applyFilterToImage(
    imageFile: File,
    filterType: FilterType,
): Promise<File> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = (e) => {
            const img = new Image();
            img.onload = async () => {
                const canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;

                const ctx = canvas.getContext('2d');
                if (!ctx) {
                    reject(new Error('Failed to get canvas context'));
                    return;
                }

                ctx.filter = getFilterCSS(filterType);
                ctx.drawImage(img, 0, 0);

                canvas.toBlob(
                    (blob) => {
                        if (!blob) {
                            reject(new Error('Failed to convert canvas to blob'));
                            return;
                        }
                        const filename = imageFile.name;
                        const filteredFile = new File([blob], filename, { type: imageFile.type });
                        resolve(filteredFile);
                    },
                    imageFile.type,
                    IMAGE_COMPRESSION_CONFIG.quality,
                );
            };

            img.onerror = () => {
                reject(new Error('Failed to load image'));
            };

            img.src = e.target?.result as string;
        };

        reader.onerror = () => {
            reject(new Error('Failed to read file'));
        };

        reader.readAsDataURL(imageFile);
    });
}
