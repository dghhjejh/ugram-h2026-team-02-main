import type {
    UserProfile,
    PrivateUserProfile,
    UserStats,
    FeedResponse,
    ImagesResponse,
    PresignResponse,
    Image,
    TrendingKeywordsResponse,
    CreateUserRequest,
    UserAuthenticationRequest,
    GoogleRegisterRequest,
    UserListResponse,
    ImageUploadRequest,
    UpdateUserProfileRequest,
    AutoCompleteImageResponse,
    CommentListResponse,
    CommentResponse,
    CreateCommentRequest,
    ImageLikeStatsResponse,
    LikeResponse,
    NotificationListResponse,
    Notification,
} from '../types/api';
import { extractErrorMessage } from '../utils/errors';

export interface TokenResponse {
    access_token: string;
    token_type: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';
const DEFAULT_LIMIT = 50;
const USER_SEARCH_CACHE_TTL_MS = 30_000;
const USER_SEARCH_CACHE_MAX_ENTRIES = 50;

type CachedUserSearch = {
    users: UserProfile[];
    expiresAt: number;
};

export function getApiOrigin(baseUrl: string = API_BASE_URL): string | null {
    try {
        return new URL(baseUrl).origin;
    } catch {
        return null;
    }
}

export function getTracePropagationTargets(baseUrl: string = API_BASE_URL): Array<string | RegExp> {
    const targets: Array<string | RegExp> = ['localhost', /^\//];
    const apiOrigin = getApiOrigin(baseUrl);

    if (apiOrigin && !targets.some((target) => typeof target === 'string' && target === apiOrigin)) {
        targets.push(apiOrigin);
    }

    return targets;
}

class ApiClient {
    private baseUrl: string;
    private userSearchCache = new Map<string, CachedUserSearch>();
    private pendingUserSearches = new Map<string, Promise<UserProfile[]>>();
    private pendingImageSearches = new Map<string, Promise<ImagesResponse>>();

    constructor(baseUrl: string = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    private async request<T>(
        endpoint: string,
        options?: RequestInit,
        authToken?: string,
    ): Promise<T> {
        const headers: Record<string, string> = { ...(options?.headers as Record<string, string>) };

        const hasContentType = Object.keys(headers).some((k) => k.toLowerCase() === 'content-type');
        if (options?.method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method.toUpperCase()) && !hasContentType) {
            headers['Content-Type'] = 'application/json';
        }

        if (authToken) {
            headers.Authorization = `Bearer ${authToken}`;
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
            let errorMessage: string;

            try {
                const errorResponse = await response.json();
                errorMessage = extractErrorMessage(errorResponse);
            } catch {
                errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            }

            throw new Error(errorMessage);
        }

        if (response.status === 204) {
            return undefined as T;
        }

        return response.json();
    }

    async getUserProfile(userId: string, token?: string): Promise<UserProfile> {
        return this.request<UserProfile>(`/users/${userId}`, undefined, token);
    }

    async getUserStats(userId: string, token?: string): Promise<UserStats> {
        return this.request<UserStats>(`/social/stats/${userId}`, undefined, token);
    }

    async getUserImages(userId: string, limit = DEFAULT_LIMIT, offset = 0, token?: string): Promise<ImagesResponse> {
        return this.request<ImagesResponse>(
            `/images/user/${userId}?limit=${limit}&offset=${offset}`,
            undefined,
            token,
        );
    }

    async getFeed(limit = 12, cursor?: string, token?: string): Promise<FeedResponse> {
        const params = new URLSearchParams({ limit: String(limit) });
        if (cursor) {
            params.set('cursor', cursor);
        }
        return this.request<FeedResponse>(`/images/feed?${params.toString()}`, undefined, token);
    }

    async presignImage(
        params: {
            owner_user_id: string;
            filename: string;
            content_type: string;
            content_length: number;
        },
        token?: string,
    ): Promise<PresignResponse> {
        return this.request<PresignResponse>(
            '/images/presign',
            {
                method: 'POST',
                body: JSON.stringify(params),
            },
            token,
        );
    }

    async createImage(
        payload: {
            owner_user_id: string;
            description: string;
            hashtags: string[];
            mentions_user_ids: string[];
            mention_tags: { user_id: string; x_percent: number; y_percent: number }[];
            image_url: string;
            crop_aspect_ratio?: number;
            crop_zoom?: number;
            crop_center_x_percent?: number;
            crop_center_y_percent?: number;
        },
        token?: string,
    ): Promise<Image> {
        return this.request<Image>(
            '/images',
            {
                method: 'POST',
                body: JSON.stringify(payload),
            },
            token,
        );
    }

    async deleteImage(imageId: string, token?: string): Promise<void> {
        return this.request<void>(
            `/images/${imageId}`,
            {
                method: 'DELETE',
            },
            token,
        );
    }

    async getImage(imageId: string, token?: string): Promise<Image> {
        return this.request<Image>(`/images/${imageId}`, undefined, token);
    }

    async registerUser(userData: CreateUserRequest): Promise<PrivateUserProfile> {
        return this.request<PrivateUserProfile>('/users/register', {
            method: 'POST',
            body: JSON.stringify(userData),
        });
    }

    async createUser(userData: CreateUserRequest): Promise<PrivateUserProfile> {
        return this.registerUser(userData);
    }

    async login(payload: UserAuthenticationRequest): Promise<TokenResponse> {
        const form = new URLSearchParams();
        form.append('username', payload.username);
        form.append('password', payload.user_password);
        form.append('scope', payload.scope ?? '');
        if (payload.grant_type) form.append('grant_type', payload.grant_type);
        if (payload.client_id) form.append('client_id', payload.client_id);
        if (payload.client_secret) form.append('client_secret', payload.client_secret);

        return this.request<TokenResponse>('/users/token', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: form.toString(),
        });
    }

    async getCurrentUser(token?: string): Promise<PrivateUserProfile> {
        return this.request<PrivateUserProfile>('/users/me', undefined, token);
    }

    async listUsers(limit = DEFAULT_LIMIT, offset = 0, token?: string, keyword?: string): Promise<UserListResponse> {
        const params = new URLSearchParams({
            limit: String(limit),
            offset: String(offset),
        });
        if (keyword) {
            params.set('keyword', keyword);
        }
        return this.request<UserListResponse>(`/users?${params.toString()}`, undefined, token);
    }

    async searchUsers(keyword: string, limit = 10, token?: string): Promise<UserProfile[]> {
        const normalizedKeyword = keyword.trim().toLowerCase();
        if (!normalizedKeyword) {
            return [];
        }

        const authScope = token ?? 'anonymous';
        const cacheKey = `${authScope}:${normalizedKeyword}:${limit}`;
        const cached = this.getCachedUserSearch(cacheKey);
        if (cached) {
            return cached;
        }

        const pending = this.pendingUserSearches.get(cacheKey);
        if (pending) {
            return pending;
        }

        const searchPromise = this.listUsers(limit, 0, token, normalizedKeyword)
            .then((response) => {
                this.setCachedUserSearch(cacheKey, response.users);
                return response.users;
            })
            .finally(() => {
                this.pendingUserSearches.delete(cacheKey);
            });

        this.pendingUserSearches.set(cacheKey, searchPromise);
        return searchPromise;
    }

    private getCachedUserSearch(cacheKey: string): UserProfile[] | null {
        const cached = this.userSearchCache.get(cacheKey);
        if (!cached) {
            return null;
        }
        if (cached.expiresAt <= Date.now()) {
            this.userSearchCache.delete(cacheKey);
            return null;
        }
        return cached.users;
    }

    private setCachedUserSearch(cacheKey: string, users: UserProfile[]): void {
        if (this.userSearchCache.size >= USER_SEARCH_CACHE_MAX_ENTRIES) {
            const oldestKey = this.userSearchCache.keys().next().value;
            if (oldestKey) {
                this.userSearchCache.delete(oldestKey);
            }
        }
        this.userSearchCache.set(cacheKey, {
            users,
            expiresAt: Date.now() + USER_SEARCH_CACHE_TTL_MS,
        });
    }

    private async requestImageSearch(
        mode: 'hashtag' | 'description',
        term: string,
        token?: string,
    ): Promise<ImagesResponse> {
        const normalizedTerm = term.trim().toLowerCase();
        if (!normalizedTerm) {
            return { images: [], total: 0, limit: 0, offset: 0 };
        }

        const authScope = token ?? 'anonymous';
        const cacheKey = `${authScope}:${mode}:${normalizedTerm}`;

        const pending = this.pendingImageSearches.get(cacheKey);
        if (pending) {
            return pending;
        }

        const endpoint = mode === 'hashtag'
            ? `/images/hashtags/${encodeURIComponent(normalizedTerm)}`
            : `/images/description/${encodeURIComponent(normalizedTerm)}`;

        const requestPromise = this.request<ImagesResponse>(endpoint, undefined, token)
            .finally(() => {
                this.pendingImageSearches.delete(cacheKey);
            });

        this.pendingImageSearches.set(cacheKey, requestPromise);
        return requestPromise;
    }

    async uploadImage(userId: string, request: ImageUploadRequest, token?: string): Promise<Image> {
        const contentType = request.file.type || 'application/octet-stream';

        const presign = await this.presignImage(
            {
                owner_user_id: userId,
                filename: request.file.name,
                content_type: contentType,
                content_length: request.file.size,
            },
            token,
        );

        const uploadResp = await fetch(presign.upload_url, {
            method: 'PUT',
            headers: { 'Content-Type': contentType },
            body: request.file,
        });

        if (!uploadResp.ok) {
            throw new Error(`Upload failed with status ${uploadResp.status}`);
        }

        const parsedHashtags = request.hashtags
            .split(/[,\s]+/)
            .map((t) => t.replace(/^#/, '').trim().toLowerCase())
            .filter(Boolean);

        const mentionIds = Array.from(
            new Set(
                (request.mentions_user_ids ?? [])
                    .map((id) => id.trim())
                    .filter((id) => id.length > 0),
            ),
        );
        const mentionTags = (request.mention_tags ?? [])
            .filter((tag) => mentionIds.includes(tag.user_id));

        return this.createImage(
            {
                owner_user_id: userId,
                description: request.description.trim(),
                hashtags: parsedHashtags,
                mentions_user_ids: mentionIds,
                mention_tags: mentionTags,
                image_url: presign.image_url,
                crop_aspect_ratio: request.crop_aspect_ratio,
                crop_zoom: request.crop_zoom,
                crop_center_x_percent: request.crop_center_x_percent,
                crop_center_y_percent: request.crop_center_y_percent,
            },
            token,
        );
    }

    async updateImageMetadata(
        imageId: string,
        metadata: {
            description?: string;
            hashtags?: string[];
            mentions_user_ids?: string[];
            mention_tags?: { user_id: string; x_percent: number; y_percent: number }[];
        },
        token?: string,
    ): Promise<Image> {
        return this.request<Image>(
            `/images/${imageId}`,
            {
                method: 'PATCH',
                body: JSON.stringify(metadata),
            },
            token,
        );
    }

    async completeGoogleRegistration(payload: GoogleRegisterRequest): Promise<TokenResponse> {
        return this.request<TokenResponse>('/auth/google/register', {
            method: 'POST',
            credentials: 'include',
            body: JSON.stringify(payload),
        });
    }

    async refreshToken(): Promise<TokenResponse> {
        return this.request<TokenResponse>('/users/refresh', {
            method: 'POST',
            credentials: 'include',
        });
    }

    async logout(): Promise<void> {
        return this.request<void>('/users/logout', {
            method: 'POST',
            credentials: 'include',
        });
    }

    async updateUserProfile(userId: string, userData: UpdateUserProfileRequest, token?: string): Promise<PrivateUserProfile> {
        return this.request<PrivateUserProfile>(`/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(userData),
        }, token);
    }

    async getProfilePhotoUrl(userId: string, token?: string): Promise<{signed_url: string}> {
        return this.request<{signed_url: string}>(`/users/${userId}/profile-photo`, undefined, token);
    }

    async getImagesByHashtag(hashtag: string, token?: string): Promise<ImagesResponse> {
        return this.requestImageSearch('hashtag', hashtag, token);
    }

    async getImageByDescriptionKeyword(keyword: string, token?: string): Promise<ImagesResponse> {
        return this.requestImageSearch('description', keyword, token);
    }

    async getImageLikeStats(imageId: string, token?: string): Promise<ImageLikeStatsResponse> {
        return this.request<ImageLikeStatsResponse>(`/images/${imageId}/likes/stats`, undefined, token);
    }

    async likeImage(imageId: string, token?: string): Promise<LikeResponse> {
        return this.request<LikeResponse>(
            `/images/${imageId}/likes`,
            {
                method: 'POST',
            },
            token,
        );
    }

    async unlikeImage(imageId: string, token?: string): Promise<void> {
        return this.request<void>(
            `/images/${imageId}/likes`,
            {
                method: 'DELETE',
            },
            token,
        );
    }

    async listImageComments(imageId: string, limit = 20, token?: string): Promise<CommentListResponse> {
        return this.request<CommentListResponse>(`/images/${imageId}/comments?limit=${limit}`, undefined, token);
    }

    async createImageComment(
        imageId: string,
        payload: CreateCommentRequest,
        token?: string,
    ): Promise<CommentResponse> {
        return this.request<CommentResponse>(
            `/images/${imageId}/comments`,
            {
                method: 'POST',
                body: JSON.stringify(payload),
            },
            token,
        );
    }

    async getTrendingKeywords(limit = 10, window: 'all_time' | 'today' = 'all_time', token?: string): Promise<TrendingKeywordsResponse> {
        return this.request<TrendingKeywordsResponse>(
            `/images/trending-keywords?limit=${limit}&window=${window}`,
            undefined,
            token,
        );
    }

    async deleteAccount(userId: string, confirmation: string, token?: string): Promise<void> {
        return this.request<void>(
            `/users/${userId}`,
            {
                method: 'DELETE',
                body: JSON.stringify({ confirmation }),
            },
            token,
        );
    }

    async getAutoCompleteImageMetadata(partial: string, searchType: 'description' | 'hashtag', token?: string): Promise<AutoCompleteImageResponse> {
        const params = new URLSearchParams({
            partial,
            search_type: searchType,
        });
        return this.request<AutoCompleteImageResponse>(`/images/autocomplete?${params.toString()}`, undefined, token);
    }

    async getNotifications(limit = 50, token?: string): Promise<NotificationListResponse> {
        return this.request<NotificationListResponse>(`/notifications/?limit=${limit}`, undefined, token);
    }

    async markNotificationRead(notificationId: string, token?: string): Promise<Notification> {
        return this.request<Notification>(
            `/notifications/${notificationId}/read`,
            { method: 'PATCH' },
            token,
        );
    }
}

export const apiClient = new ApiClient();

export const API_BASE = API_BASE_URL;
