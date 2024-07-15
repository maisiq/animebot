import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, func, alias, update, or_
from sqlalchemy.orm import joinedload, selectinload

from transliterate import translit

from .orm_models import Origin, User, Season, VoiceoverStudio, DubbedSeason, Episode, SeasonStatus


class UsersRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def commit(self):
        try:
            await self._session.commit()
        except Exception as e:
            await self._session.rollback()
            logging.error(e)
            raise

    async def get_user_by_id(self, user_id: int):
        return await self._session.get(User, user_id)

    async def subscribed_on_season_users_ids(self, season: DubbedSeason) -> list[int]:
        query = select(User.id).where(User.animelist.contains(season))
        result = await self._session.execute(query)

        return result.scalars().all()
    
    async def subscribed_on_first_dubb_users_ids(self, season_name: str) -> list[int]:
        res = await self._session.execute(
            select(User.id)
            .where(User.animelist.any(season_name=season_name, studio_name='#subscribe_on_first'))
        )
        return res.scalars().all()

    async def all(self) -> list[User]:
        users = await self._session.execute(select(User))
        return users.scalars().all()

    def add(self, user_id):
        user = User(id=user_id)
        self._session.add(user)


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
        season_with_studio = DubbedSeason(season_id=season_id, 
                                          studio_name=studio_name, 
                                          season_name=season_name)
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
    
    async def get_dubbed_season_by_season_and_studio_name(self, season_name: str, studio_name: str) -> DubbedSeason:
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


class AnimeRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def commit(self):
        await self._session.commit()

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
    
    async def get_season_by_id(self, season_id: int) -> Season:
        return await self._session.get(Season, season_id)

    #change name
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
        # print(query.compile()) # 
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