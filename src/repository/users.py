import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .orm_models import (
    DubbedSeason,
    User,
)


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

    async def get_admins(self) -> list[User]:
        users = await self._session.execute(select(User).where(User.is_admin.is_(True)))
        return users.scalars().all()

    def add(self, user_id):
        user = User(id=user_id)
        self._session.add(user)
