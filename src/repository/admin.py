import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .orm_models import (
    DubbedSeason,
    Episode,
    Origin,
    Season,
    VoiceoverStudio,
)


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def commit(self):
        try:
            await self._session.commit()
        except Exception as e:
            await self._session.rollback()
            logging.error(str(e))
            raise

    def add_origin(self, title_ru: str, title_en: str):
        new_origin = Origin(title_ru=title_ru, title_en=title_en)
        self._session.add(new_origin)

    def add_season(self, origin_id: int, title_ru: str, title_en: str, cover: str, status: str):
        new_season = Season(
            origin_id=origin_id,
            title_ru=title_ru,
            title_en=title_en,
            cover=cover,
            status=status,
        )
        self._session.add(new_season)

    def add_studio(self, studio_name):
        new_season = VoiceoverStudio(name=studio_name)
        self._session.add(new_season)

    def add_dubbed_season(self, season_id, season_name, studio_name):
        season_with_studio = DubbedSeason(season_id=season_id, studio_name=studio_name, season_name=season_name)
        self._session.add(season_with_studio)
        return season_with_studio

    def add_episode(self, episode_number: int, season_id: int, name: str | None = None):
        episode = Episode(episode_number=episode_number, season_id=season_id, name=name)
        self._session.add(episode)
        return episode

    async def update_season_status(self, season_name, status):
        stmt = update(Season).where(Season.title_ru == season_name).values(status=status)
        await self._session.execute(stmt)

    async def get_season_by_name(self, season_name: str):
        res = await self._session.execute(
            select(Season)
            .where(Season.title_ru == season_name)
        )
        return res.scalar_one_or_none()

    async def get_dubbed_season_by_season_and_studio_name(
        self,
        season_name: str,
        studio_name: str
    ) -> DubbedSeason | None:
        res = await self._session.execute(
            select(DubbedSeason)
            .where(
                DubbedSeason.season.has(title_ru=season_name),
                DubbedSeason.studio_name == studio_name
            )
        )
        return res.scalar_one_or_none()

    async def get_origin_by_name(self, origin_name: str):
        res = await self._session.execute(
            select(Origin).where(Origin.title_ru == origin_name)
        )
        return res.scalar_one()

    async def origin_list(self) -> list[Origin]:
        response = await self._session.execute(select(Origin))
        return response.scalars().all()

    async def studios_list(self) -> list[VoiceoverStudio]:
        response = await self._session.execute(select(VoiceoverStudio))
        return response.scalars().all()
