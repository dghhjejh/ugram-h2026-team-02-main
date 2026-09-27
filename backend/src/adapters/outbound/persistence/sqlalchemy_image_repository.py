from collections import Counter
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import and_, cast, func, or_, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from src.adapters.outbound.persistence.mappers.image_mapper import ImageMapper
from src.adapters.outbound.persistence.models import (
    CommentORM,
    ImageORM,
    ReactionORM,
    SearchEventORM,
    SearchTrendDailyORM,
    UserORM,
)
from src.domain.images.entities import FeedImageItem, Image, SearchTrendStat
from src.domain.images.repositories import IImageRepository


class SQLAlchemyImageRepository(IImageRepository):
    """SQLAlchemy adapter for Image persistence."""

    def __init__(self, session: Session, mapper: ImageMapper | None = None) -> None:
        self._session = session
        self._mapper = mapper or ImageMapper()

    def save(self, image: Image) -> Image:
        orm_image = self._session.query(ImageORM).filter_by(id=image.id).first()
        if orm_image:
            mapped_image = self._mapper.to_orm(image)
            orm_image.description = image.description
            orm_image.hashtags = image.hashtags
            orm_image.mentions_user_ids = mapped_image.mentions_user_ids
            orm_image.mention_tags = mapped_image.mention_tags
            orm_image.updated_at = image.updated_at
        else:
            orm_image = self._mapper.to_orm(image)
            self._session.add(orm_image)
        self._session.commit()
        self._session.refresh(orm_image)
        return self._mapper.to_entity(orm_image)

    def get_by_id(self, image_id: UUID) -> Image | None:
        stmt = select(ImageORM).where(ImageORM.id == image_id)
        orm = self._session.scalars(stmt).first()
        return self._mapper.to_entity(orm) if orm else None

    def get_all_by_hashtag(self, hashtag: str) -> list[Image]:
        dialect = self._session.bind.dialect.name

        if dialect == "postgresql":
            stmt = select(ImageORM).where(cast(ImageORM.hashtags, JSONB).op("@>")(cast([hashtag], JSONB)))
        else:
            stmt = select(ImageORM).where(
                ImageORM.id.in_(
                    select(ImageORM.id)
                    .select_from(ImageORM)
                    .where(func.json_each(ImageORM.hashtags).table_valued("value").c.value == hashtag)
                )
            )
        return [self._mapper.to_entity(orm) for orm in self._session.scalars(stmt)]

    def get_all_by_description_keyword(self, keyword: str) -> list[Image]:
        stmt = select(ImageORM).where(ImageORM.description.ilike(f"%{keyword}%"))
        return [self._mapper.to_entity(orm) for orm in self._session.scalars(stmt)]

    def get_all_by_owner(self, owner_id: UUID, limit: int, offset: int) -> list[Image]:
        stmt = (
            select(ImageORM)
            .where(ImageORM.owner_user_id == owner_id)
            .order_by(ImageORM.created_at.desc(), ImageORM.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._mapper.to_entity(orm) for orm in self._session.scalars(stmt)]

    def enqueue_search_event(self, keyword: str, trend_type: str, search_date: date, searched_at: datetime) -> None:
        self._session.add(
            SearchEventORM(
                keyword=keyword,
                trend_type=trend_type,
                search_date=search_date,
                searched_at=searched_at,
            )
        )
        self._session.flush()

    def process_pending_search_events(self, batch_size: int, processed_at: datetime) -> int:
        stmt = (
            select(SearchEventORM)
            .where(SearchEventORM.processed_at.is_(None))
            .order_by(SearchEventORM.searched_at.asc(), SearchEventORM.id.asc())
            .limit(batch_size)
        )

        if self._session.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)

        pending_events = list(self._session.scalars(stmt))
        if not pending_events:
            return 0

        grouped_events = Counter((event.keyword, event.trend_type, event.search_date) for event in pending_events)

        for (keyword, trend_type, search_date), count in grouped_events.items():
            trend_stmt = select(SearchTrendDailyORM).where(
                SearchTrendDailyORM.keyword == keyword,
                SearchTrendDailyORM.trend_type == trend_type,
                SearchTrendDailyORM.search_date == search_date,
            )
            trend = self._session.scalars(trend_stmt).first()
            if trend:
                trend.search_count += count
                trend.updated_at = processed_at
            else:
                self._session.add(
                    SearchTrendDailyORM(
                        keyword=keyword,
                        trend_type=trend_type,
                        search_date=search_date,
                        search_count=count,
                        created_at=processed_at,
                        updated_at=processed_at,
                    )
                )

        for event in pending_events:
            event.processed_at = processed_at

        self._session.flush()
        return len(pending_events)

    def list_search_trends(self, search_date: date | None = None) -> list[SearchTrendStat]:
        stmt = select(
            SearchTrendDailyORM.keyword,
            SearchTrendDailyORM.trend_type,
            func.sum(SearchTrendDailyORM.search_count).label("total_searches"),
        ).group_by(SearchTrendDailyORM.keyword, SearchTrendDailyORM.trend_type)

        if search_date is not None:
            stmt = stmt.where(SearchTrendDailyORM.search_date == search_date)

        rows = self._session.execute(stmt).all()
        return [
            SearchTrendStat(
                keyword=keyword,
                trend_type=trend_type,
                count=total_searches,
                search_date=search_date,
            )
            for keyword, trend_type, total_searches in rows
        ]

    def delete(self, image_id: UUID) -> bool:
        orm = self._session.get(ImageORM, image_id)
        if orm is None:
            return False
        self._session.delete(orm)
        self._session.flush()
        return True

    def get_feed(
        self,
        limit: int,
        cursor_created_at: datetime | None = None,
        cursor_image_id: UUID | None = None,
    ) -> list[FeedImageItem]:
        likes_subquery = (
            select(
                ReactionORM.image_id.label("image_id"),
                func.count(ReactionORM.id).label("like_count"),
            )
            .where(ReactionORM.type == "like")
            .group_by(ReactionORM.image_id)
            .subquery()
        )

        comments_subquery = (
            select(
                CommentORM.image_id.label("image_id"),
                func.count(CommentORM.id).label("comment_count"),
            )
            .group_by(CommentORM.image_id)
            .subquery()
        )

        stmt = (
            select(
                ImageORM,
                UserORM.username,
                UserORM.profile_photo_url,
                func.coalesce(likes_subquery.c.like_count, 0).label("like_count"),
                func.coalesce(comments_subquery.c.comment_count, 0).label("comment_count"),
            )
            .join(UserORM, UserORM.id == ImageORM.owner_user_id)
            .outerjoin(likes_subquery, likes_subquery.c.image_id == ImageORM.id)
            .outerjoin(comments_subquery, comments_subquery.c.image_id == ImageORM.id)
            .order_by(ImageORM.created_at.desc(), ImageORM.id.desc())
            .limit(limit)
        )

        if cursor_created_at and cursor_image_id:
            stmt = stmt.where(
                or_(
                    ImageORM.created_at < cursor_created_at,
                    and_(
                        ImageORM.created_at == cursor_created_at,
                        ImageORM.id < cursor_image_id,
                    ),
                )
            )

        rows = self._session.execute(stmt).all()
        return [
            FeedImageItem(
                image=self._mapper.to_entity(image_orm),
                owner_username=username,
                owner_profile_photo_url=profile_photo_url,
                like_count=like_count,
                comment_count=comment_count,
            )
            for image_orm, username, profile_photo_url, like_count, comment_count in rows
        ]

    def get_autocomplete_descriptions(self, partial: str) -> list[str]:
        stmt = (
            select(ImageORM.description)
            .where(ImageORM.description.ilike(f"%{partial}%"))
            .group_by(ImageORM.description)
            .order_by(func.count().desc())
            .limit(10)
        )
        return [row[0] for row in self._session.execute(stmt).all()]

    def get_autocomplete_hashtags(self, partial: str) -> list[str]:
        dialect = self._session.bind.dialect.name

        if dialect == "postgresql":
            stmt = text(
                "SELECT tag"
                " FROM images, jsonb_array_elements_text(images.hashtags) AS tag"
                " WHERE tag ILIKE :partial"
                " GROUP BY tag ORDER BY count(*) DESC LIMIT 10"
            )
            return [row[0] for row in self._session.execute(stmt, {"partial": f"%{partial}%"}).all()]
        else:
            tag_col = func.json_each(ImageORM.hashtags).table_valued("value")
            stmt = (
                select(tag_col.c.value)
                .select_from(ImageORM, tag_col)
                .where(tag_col.c.value.ilike(f"%{partial}%"))
                .group_by(tag_col.c.value)
                .order_by(func.count().desc())
                .limit(10)
            )
        return [row[0] for row in self._session.execute(stmt).all()]
