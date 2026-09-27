export interface UserProfile {
    id: string;
    username: string;
    first_name: string;
    last_name: string;
    bio?: string | null;
    profile_photo_url?: string | null;
    phone_number?: string | null;
    email?: string;
    registration_date: string;
}

export interface PrivateUserProfile extends UserProfile {
    email: string;
    phone_number?: string | null;
}

export interface CreateUserRequest {
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    user_password: string;
    profile_photo_url?: string;
}

export interface UpdateUserProfileRequest {
    username?: string;
    email?: string;
    first_name?: string;
    last_name?: string;
    profile_photo_url?: string;
    phone_number?: string | undefined;
}

export interface UserListResponse {
    users: UserProfile[];
    total: number;
    limit: number;
    offset: number;
}

export interface UserAuthenticationRequest {
    username: string;
    user_password: string;
    scope?: string;
    grant_type?: string | null;
    client_id?: string | null;
    client_secret?: string | null;
}

export interface GoogleRegisterRequest {
    username: string;
    registration_token: string;
}

export interface UserStats {
    posts_count: number;
    followers_count: number;
    following_count: number;
}

export interface MentionTagPosition {
    user_id: string;
    x_percent: number;
    y_percent: number;
}

export interface MentionedUser {
    id: string;
    username: string;
    profile_photo_url?: string | null;
    first_name?: string | null;
    last_name?: string | null;
    tag_position?: MentionTagPosition | null;
}

export interface Image {
    id: string;
    owner_user_id: string;
    description: string;
    hashtags: string[];
    mentions_user_ids: string[];
    mentions: MentionedUser[];
    mention_tags: MentionTagPosition[];
    image_url: string;
    thumbnail_view_url?: string | null;
    view_url: string;
    created_at: string;
    updated_at: string;
    like_count?: number;
    comment_count?: number;
}

export interface ImagesResponse {
    images: Image[];
    total: number;
    limit: number;
    offset: number;
}

export interface TrendingKeywordItem {
    keyword: string;
    count: number;
}

export interface TrendingKeywordsGeneratedFrom {
    source_fields: string[];
    window: string;
    count_unit: string;
    aggregation_mode: string;
}

export interface TrendingKeywordsResponse {
    hashtags: TrendingKeywordItem[];
    description_keywords: TrendingKeywordItem[];
    generated_from: TrendingKeywordsGeneratedFrom;
}

// Global Feed Response (from GET /images/feed)
export interface FeedItem {
    id: string;
    owner_user_id: string;
    owner_username: string;
    owner_profile_photo_url: string | null;
    description: string;
    hashtags: string[];
    mentions_user_ids: string[];
    mentions: MentionedUser[];
    mention_tags: MentionTagPosition[];
    image_url: string;
    feed_view_url?: string | null;
    view_url: string;
    like_count: number;
    comment_count: number;
    created_at: string;
    updated_at: string;
}

export interface FeedResponse {
    items: FeedItem[];
    next_cursor: string | null;
    has_more: boolean;
}

export interface ImageLikeStatsResponse {
    total_likes: number;
    user_has_liked: boolean;
}

export interface CreateCommentRequest {
    content: string;
}

export interface CommentResponse {
    id: string;
    user_id: string;
    image_id: string;
    content: string;
    created_at: string;
    author?: UserProfile | null;
}

export interface CommentListResponse {
    comments: CommentResponse[];
    total: number;
    limit: number;
}

export interface LikeResponse {
    id: string;
    user_id: string;
    image_id: string;
    created_at: string;
}

export interface PresignResponse {
    upload_url: string;
    storage_key: string;
    image_url: string;
    expires_in: number;
}

export interface ImageUploadRequest {
    file: File;
    description: string;
    hashtags: string;
    mentions_user_ids: string[];
    mention_tags: MentionTagPosition[];
    crop_aspect_ratio?: number;
    crop_zoom?: number;
    crop_center_x_percent?: number;
    crop_center_y_percent?: number;
}

export interface AutoCompleteImageRequest {
    partial: string;
    searchType: 'description' | 'hashtag';
}

export interface AutoCompleteImageResponse {
    suggestions: string[];
}

export type NotificationType = 'comment' | 'like';

export interface Notification {
    id: string;
    actor_user_id: string;
    image_id: string;
    notification_type: NotificationType;
    is_read: boolean;
    created_at: string;
    actor?: UserProfile | null;
}

export interface NotificationListResponse {
    notifications: Notification[];
    unread_count: number;
    total: number;
}
