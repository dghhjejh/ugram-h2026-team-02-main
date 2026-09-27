from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.social.entities import Comment, Reaction


class ICommentRepository(ABC):
    """Interface for comment persistence."""

    @abstractmethod
    def add_comment(self, comment: Comment) -> Comment:
        """Create and persist a new comment."""
        pass

    @abstractmethod
    def get_comments_for_target(self, target_id: UUID) -> list[Comment]:
        """Get all comments for a target (image)."""
        pass

    @abstractmethod
    def get_comments_for_image(self, image_id: UUID, limit: int) -> list[Comment]:
        """Get paginated comments for an image."""
        pass

    @abstractmethod
    def get_comment_count_for_image(self, image_id: UUID) -> int:
        """Get total comment count for an image."""
        pass

    @abstractmethod
    def get_comment_by_id(self, comment_id: UUID) -> Comment | None:
        """Get one comment by ID."""
        pass

    @abstractmethod
    def delete_comment(self, comment_id: UUID) -> bool:
        """Delete one comment by ID. Returns True when deleted."""
        pass


class IReactionRepository(ABC):
    """Interface for reaction (like) persistence."""

    @abstractmethod
    def add_reaction(self, reaction: Reaction) -> Reaction:
        """Create and persist a new reaction (like)."""
        pass

    @abstractmethod
    def remove_reaction(self, user_id: UUID, target_id: UUID, reaction_type: str) -> bool:
        """Remove a reaction. Returns True if removed, False if not found."""
        pass

    @abstractmethod
    def get_reaction(self, user_id: UUID, target_id: UUID, reaction_type: str) -> Reaction | None:
        """Get a specific reaction. Returns None if not found."""
        pass

    @abstractmethod
    def get_reactions_for_target(self, target_id: UUID, reaction_type: str) -> list[Reaction]:
        """Get all reactions of a specific type for a target."""
        pass

    @abstractmethod
    def get_reaction_count_for_target(self, target_id: UUID, reaction_type: str) -> int:
        """Count reactions of a specific type for a target."""
        pass

    @abstractmethod
    def user_has_reacted(self, user_id: UUID, target_id: UUID, reaction_type: str) -> bool:
        """Check if user has already reacted."""
        pass
