import logging

from sqlalchemy.exc import SQLAlchemyError

from src.repository.repository import AnimeRepository, UsersRepository, AdminRepository
from repository.orm_models import DubbedSeason, Origin, Season, User
from src.tasks.scrapping_task.modelsDTO import AnimeEpisode


class Service:
    def __init__(self, repository: AdminRepository):
        self._repo = repository
    
    # user repository
    async def add_user_if_not_exists(self, user_id):
        ...
    
    # admin repository
    async def dubbed_seasons_factory(self, season_name: str, studios: list[str]):
        ...
