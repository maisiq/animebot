from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .orm_models import Base


class DatabaseManager:
    _engine: AsyncEngine | None = None
    _db_session: async_sessionmaker[AsyncSession] | None = None

    def __init__(self, url, echo=False):
        self._engine = create_async_engine(url, echo=echo)
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

    def get_session(self) -> AsyncSession:
       return self._db_session()  


_sessionmanager: DatabaseManager | None = None


async def init_db(url, echo=False):
    global _sessionmanager
    _sessionmanager = DatabaseManager(url, echo)
    yield _sessionmanager
    await _sessionmanager._engine.dispose()
    _sessionmanager = None


def get_session():
    if _sessionmanager is None:
        raise RuntimeError("db is not initialized")
    return _sessionmanager.get_session()
