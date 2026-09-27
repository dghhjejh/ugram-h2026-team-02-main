"""SQLAlchemy implementation of reaction (like) repository."""

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from src.adapters.outbound.persistence.models import ReactionORM
from src.domain.social.entities import Reaction
from src.domain.social.repositories import IReactionRepository


class SQLAlchemyReactionRepository(IReactionRepository):
    """SQLAlchemy implementation of reaction repository."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def add_reaction(self, reaction: Reaction) -> Reaction:
        """Create and persist a new reaction (like).

        Args:
            reaction: Reaction entity to persist

        Returns:
            The persisted Reaction entity
        """
        orm = self._to_orm(reaction)
        self.db.add(orm)
        self.db.commit()
        self.db.refresh(orm)
        return self._to_entity(orm)

    def remove_reaction(self, user_id: UUID, target_id: UUID, reaction_type: str) -> bool:
        """Remove a reaction. Returns True if removed, False if not found."""
        query = select(ReactionORM).where(
            and_(
                ReactionORM.user_id == user_id,
                ReactionORM.image_id == target_id,
                ReactionORM.type == reaction_type,
            )
        )
        orm = self.db.scalar(query)
        if orm is None:
            return False

        self.db.delete(orm)
        self.db.commit()
        return True

    def get_reaction(self, user_id: UUID, target_id: UUID, reaction_type: str) -> Reaction | None:
        """Get a specific reaction. Returns None if not found."""
        query = select(ReactionORM).where(
            and_(
                ReactionORM.user_id == user_id,
                ReactionORM.image_id == target_id,
                ReactionORM.type == reaction_type,
            )
        )
        orm = self.db.scalar(query)
        if orm is None:
            return None
        return self._to_entity(orm)

    def get_reactions_for_target(self, target_id: UUID, reaction_type: str) -> list[Reaction]:
        """Get all reactions of a specific type for a target."""
        query = (
            select(ReactionORM)
            .where(
                and_(
                    ReactionORM.image_id == target_id,
                    ReactionORM.type == reaction_type,
                )
            )
            .order_by(ReactionORM.created_at.desc())
        )
        orms = self.db.scalars(query).all()
        return [self._to_entity(orm) for orm in orms]

    def get_reaction_count_for_target(self, target_id: UUID, reaction_type: str) -> int:
        """Count reactions of a specific type for a target."""
        query = (
            select(func.count())
            .select_from(ReactionORM)
            .where(
                and_(
                    ReactionORM.image_id == target_id,
                    ReactionORM.type == reaction_type,
                )
            )
        )
        count = self.db.scalar(query) or 0
        return int(count)

    def user_has_reacted(self, user_id: UUID, target_id: UUID, reaction_type: str) -> bool:
        """Check if user has already reacted."""
        query = (
            select(func.count())
            .select_from(ReactionORM)
            .where(
                and_(
                    ReactionORM.user_id == user_id,
                    ReactionORM.image_id == target_id,
                    ReactionORM.type == reaction_type,
                )
            )
        )
        count = self.db.scalar(query) or 0
        return int(count) > 0

    def _to_entity(self, orm: ReactionORM) -> Reaction:
        """Map ORM model to domain entity."""
        return Reaction(
            id=orm.id,
            user_id=orm.user_id,
            target_id=orm.image_id,
            type=orm.type,
            created_at=orm.created_at,
        )

    def _to_orm(self, reaction: Reaction) -> ReactionORM:
        """Map domain entity to ORM model."""
        return ReactionORM(
            id=reaction.id,
            user_id=reaction.user_id,
            image_id=reaction.target_id,
            type=reaction.type,
            created_at=reaction.created_at,
        )
