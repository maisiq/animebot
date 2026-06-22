from typing import Self

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from repository import AdminRepository, AnimeRepository, UsersRepository


class UnitOfWork:
    users: UsersRepository | None = None
    admin: AdminRepository | None = None
    anime: AnimeRepository | None = None

    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def __aenter__(self) -> Self:
        self.users = UsersRepository(self._session)
        self.admin = AdminRepository(self._session)
        self.anime = AnimeRepository(self._session)
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is not None:
            try:
                await self._session.rollback()
            except Exception as e:
                raise e from exc
            finally:
                await self._session.close()
                raise exc
        await self._session.close()

    async def commit(self):
        await self._session.commit()
