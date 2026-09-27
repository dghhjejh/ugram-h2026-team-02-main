from uuid import UUID, uuid4

from src.domain.social.entities import Comment, Reaction
from src.domain.social.repositories import ICommentRepository, IReactionRepository
from src.domain.time_provider import ITimeProvider


class CommentNotFoundError(Exception):
    """Raised when a comment does not exist."""

    pass


class InvalidCommentContentError(Exception):
    """Raised when comment content is empty or invalid."""

    pass


class ImageNotFoundError(Exception):
    """Raised when an image does not exist."""

    pass


class ReactionAlreadyExistsError(Exception):
    """Raised when user has already reacted to a target."""

    pass


class SocialService:
    """Service for managing social features like comments on images."""

    def __init__(
        self,
        comment_repo: ICommentRepository,
        reaction_repo: IReactionRepository,
        time_provider: ITimeProvider,
    ) -> None:
        self.comment_repo = comment_repo
        self.reaction_repo = reaction_repo
        self.time_provider = time_provider

    def post_comment(self, user_id: UUID, image_id: UUID, content: str) -> Comment:
        """Post a comment on an image."""
        if not content or not content.strip():
            raise InvalidCommentContentError("Comment content cannot be empty or whitespace-only")

        comment = Comment(
            id=uuid4(),
            user_id=user_id,
            target_id=image_id,
            content=content.strip(),
            created_at=self.time_provider.now(),
        )

        return self.comment_repo.add_comment(comment)

    def get_image_comments(self, image_id: UUID, limit: int = 50) -> list[Comment]:
        """Get paginated comments for an image."""
        return self.comment_repo.get_comments_for_image(image_id, limit=limit)

    def get_image_comment_count(self, image_id: UUID) -> int:
        """Get total number of comments on an image."""
        return self.comment_repo.get_comment_count_for_image(image_id)

    def get_comment(self, comment_id: UUID) -> Comment:
        """Get one comment by ID."""
        comment = self.comment_repo.get_comment_by_id(comment_id)
        if comment is None:
            raise CommentNotFoundError("Comment not found")
        return comment

    def delete_comment(self, comment_id: UUID) -> None:
        """Delete one comment by ID."""
        deleted = self.comment_repo.delete_comment(comment_id)
        if not deleted:
            raise CommentNotFoundError("Comment not found")

    def add_like(self, user_id: UUID, image_id: UUID) -> Reaction:
        """Add a like reaction to an image."""
        if self.reaction_repo.user_has_reacted(user_id, image_id, "like"):
            raise ReactionAlreadyExistsError(f"User {user_id} has already liked image {image_id}")

        reaction = Reaction(
            id=uuid4(),
            user_id=user_id,
            target_id=image_id,
            type="like",
            created_at=self.time_provider.now(),
        )

        return self.reaction_repo.add_reaction(reaction)

    def remove_like(self, user_id: UUID, image_id: UUID) -> bool:
        """Remove a like reaction from an image."""
        return self.reaction_repo.remove_reaction(user_id, image_id, "like")

    def get_image_like_count(self, image_id: UUID) -> int:
        """Get total number of likes on an image."""
        return self.reaction_repo.get_reaction_count_for_target(image_id, "like")

    def user_has_liked(self, user_id: UUID, image_id: UUID) -> bool:
        """Check if a user has liked an image."""
        return self.reaction_repo.user_has_reacted(user_id, image_id, "like")
