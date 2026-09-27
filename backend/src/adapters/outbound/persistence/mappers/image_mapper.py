"""Mapping between Image domain entities and ORM models."""

import uuid
from typing import Any

from src.adapters.outbound.persistence.models import ImageORM
from src.domain.images.entities import Image, MentionTag


class ImageMapper:
    """Convert between Image domain entity and ImageORM."""

    @staticmethod
    def to_entity(orm: ImageORM) -> Image:
        mention_tags = []
        for raw in orm.mention_tags or []:
            try:
                mention_tags.append(
                    MentionTag(
                        user_id=uuid.UUID(str(raw.get("user_id"))),
                        x_percent=float(raw.get("x_percent", 0)),
                        y_percent=float(raw.get("y_percent", 0)),
                    )
                )
            except Exception:
                continue

        return Image(
            id=orm.id,
            owner_user_id=orm.owner_user_id,
            description=orm.description,
            hashtags=list(orm.hashtags or []),
            mentions_user_ids=[uuid.UUID(u) for u in orm.mentions_user_ids or []],
            mention_tags=mention_tags,
            image_url=orm.image_url,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def to_orm(entity: Image) -> ImageORM:
        def _tag_to_dict(tag: MentionTag) -> dict[str, Any]:
            return {
                "user_id": str(tag.user_id),
                "x_percent": tag.x_percent,
                "y_percent": tag.y_percent,
            }

        return ImageORM(
            id=entity.id,
            owner_user_id=entity.owner_user_id,
            description=entity.description,
            hashtags=entity.hashtags,
            mentions_user_ids=[str(u) for u in entity.mentions_user_ids],
            mention_tags=[_tag_to_dict(tag) for tag in entity.mention_tags],
            image_url=entity.image_url,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
