"""SQLAlchemy implementation of comment repository."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.adapters.outbound.persistence.models import CommentORM
from src.domain.social.entities import Comment
from src.domain.social.repositories import ICommentRepository


class SQLAlchemyCommentRepository(ICommentRepository):
    """SQLAlchemy implementation of comment repository."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def add_comment(self, comment: Comment) -> Comment:
        """Create and persist a new comment."""
        orm = self._to_orm(comment)
        self.db.add(orm)
        self.db.commit()
        self.db.refresh(orm)
        return self._to_entity(orm)

    def get_comments_for_target(self, target_id: UUID) -> list[Comment]:
        """Get all comments for a target (image)."""
        query = select(CommentORM).where(CommentORM.image_id == target_id).order_by(CommentORM.created_at.desc())
        orms = self.db.scalars(query).all()
        return [self._to_entity(orm) for orm in orms]

    def get_comments_for_image(self, image_id: UUID, limit: int = 50) -> list[Comment]:
        """Get comments for an image, ordered by most recent first."""
        query = (
            select(CommentORM)
            .where(CommentORM.image_id == image_id)
            .order_by(CommentORM.created_at.desc())
            .limit(limit)
        )
        orms = self.db.scalars(query).all()
        return [self._to_entity(orm) for orm in orms]

    def get_comment_count_for_image(self, image_id: UUID) -> int:
        """Get total number of comments for an image."""
        query = select(func.count()).select_from(CommentORM).where(CommentORM.image_id == image_id)
        count = self.db.scalar(query) or 0
        return int(count)

    def get_comment_by_id(self, comment_id: UUID) -> Comment | None:
        """Get one comment by ID."""
        query = select(CommentORM).where(CommentORM.id == comment_id)
        orm = self.db.scalar(query)
        if orm is None:
            return None
        return self._to_entity(orm)

    def delete_comment(self, comment_id: UUID) -> bool:
        """Delete one comment by ID. Returns True if deleted."""
        orm = self.db.get(CommentORM, comment_id)
        if orm is None:
            return False
        self.db.delete(orm)
        self.db.commit()
        return True

    def _to_entity(self, orm: CommentORM) -> Comment:
        """Map ORM model to domain entity."""
        return Comment(
            id=orm.id,
            user_id=orm.user_id,
            target_id=orm.image_id,
            content=orm.content,
            created_at=orm.created_at,
        )

    def _to_orm(self, comment: Comment) -> CommentORM:
        """Map domain entity to ORM model."""
        return CommentORM(
            id=comment.id,
            user_id=comment.user_id,
            image_id=comment.target_id,
            content=comment.content,
            created_at=comment.created_at,
        )
