from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from transliterate import translit

from .orm_models import (
    DubbedSeason,
    Episode,
    Origin,
    Season,
    SeasonStatus,
)


class AnimeRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_origin_by_title_ru(self, title_ru: str) -> Origin | None:
        result = await self._session.execute(
            select(Origin).where(Origin.title_ru == title_ru)
        )
        return result.scalar_one_or_none()

    async def season_exists(self, title_ru: str) -> bool:
        result = await self._session.execute(
            select(Season.id).where(Season.title_ru == title_ru).limit(1)
        )
        return result.first() is not None

    async def get_dubbed_seasons_by_season_id(self, season_id: int):
        result = await self._session.execute(
            select(DubbedSeason)
            .where(DubbedSeason.season.has(id=season_id))
        )
        return result.scalars().all()

    async def get_season_by_name(self, season_name: str):
        res = await self._session.execute(
            select(Season)
            .where(Season.title_ru == season_name)
        )
        return res.scalar_one_or_none()

    async def get_dubbed_seasons_names(self, season_id: int) -> set[str]:
        """Названия озвучек (studio_name), уже привязанные к сезону."""
        res = await self._session.execute(
            select(DubbedSeason.studio_name).where(DubbedSeason.season_id == season_id)
        )
        return set(res.scalars().all())

    async def get_season_by_id(self, season_id: int) -> Season:
        return await self._session.get(Season, season_id)

    async def get_dubbed_season_by_season_and_studio_name(self, season_name: str, studio_name: str) -> DubbedSeason:
        res = await self._session.execute(
            select(DubbedSeason)
            .where(
                DubbedSeason.season.has(title_ru=season_name),
                DubbedSeason.studio_name == studio_name
            )
        )
        return res.scalar_one_or_none()

    async def get_dubbed_season_by_id(self, season_studio_id: int) -> DubbedSeason:
        return await self._session.get(DubbedSeason, season_studio_id)

    async def get_seasons_by_query(self, user_query: str) -> list[Season]:

        def make_query(user_query):
            return (
                select(Season)
                .where(
                    or_(
                        func.ts_rank(
                            func.to_tsvector('russian', Season.title_ru),
                            # user_query is auto-escaping
                            func.websearch_to_tsquery('russian', user_query)
                        ) >= 0.001,
                        func.ts_rank(
                            func.to_tsvector('english', Season.title_en),
                            func.websearch_to_tsquery('english', user_query)
                        ) >= 0.001
                    ),
                    Season.status != SeasonStatus.RELEASED
                )
            )

        query = make_query(user_query)
        result = await self._session.execute(query)
        frozen = result.freeze()

        # если пользователь
        if not frozen().scalars().all():
            query = make_query(translit(user_query, language_code='ru', reversed=True))
            result = await self._session.execute(query)
            return result.scalars().all()
        return frozen().scalars().all()

    async def check_if_new_episodes_exist(self, season_name: str, episode_number: int):
        query = (
            select(Episode.id)
            .join(DubbedSeason)
            .where(Episode.episode_number == episode_number,
                   DubbedSeason.season_name == season_name)
            .limit(1)
        )
        res = await self._session.execute(query)
        if res.scalar():
            return True
        return False
