from dependency_injector import containers, providers

from config import DB_DSN, DEBUG
from logger.config import setup_logger
from repository import AdminRepository, AnimeRepository, UsersRepository
from repository.config import get_session, init_db
from uow import UnitOfWork


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=[
            "routers",
            "tasks.notification_task"
        ],
        modules=[
            "tasks.scrapping_task.utils",
            "tasks.scrapping_task.season_scrapper",
        ]
    )

    logger = providers.Resource(
        setup_logger,
        file_logger=False,
    )

    db = providers.Resource(
        init_db,
        url=DB_DSN,
        echo=DEBUG,
    )

    session = providers.Factory(get_session)

    uow = providers.Factory(
        UnitOfWork,
        session=session,
    )

    anime_repository = providers.Factory(
        AnimeRepository,
        session=session
    )
    user_repository = providers.Factory(
        UsersRepository,
        session=session
    )
    admin_repository = providers.Factory(
        AdminRepository,
        session=session
    )
