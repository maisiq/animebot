import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .orm_models import Base


class DatabaseManager:
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._db_session: async_sessionmaker[AsyncSession] | None = None

    def init(self, url=None):
        if url:
            self._engine = create_async_engine(url, echo=True)
        else:
            self._engine = create_async_engine(os.getenv('DB_URI'))
        self._db_session = async_sessionmaker(self._engine, expire_on_commit=False)

    async def create_all(self):
        if self._engine is None:
            raise NotImplementedError

        async with self._engine.connect() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.commit()

    async def drop_all(self):
        if self._engine is None:
            raise NotImplementedError

        async with self._engine.connect() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.commit()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._db_session() as session:
            yield session


sessionmanager = DatabaseManager()


@asynccontextmanager
async def get_session():
    async with sessionmanager.session() as session:
        yield session


async def get_session_di():
    async with sessionmanager.session() as session:
        yield session
