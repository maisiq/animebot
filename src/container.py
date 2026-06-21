from dependency_injector import containers, providers

from config import DB_DSN, DEBUG
from logger.config import setup_logger
from repository.config import get_session_di, init_db
from repository.repository import AdminRepository, AnimeRepository, UsersRepository


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=[
            "routers",
            "tasks.notification_task"
        ],
        modules=["tasks.scrapping_task.utils"]
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

    session = providers.Factory(get_session_di)

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
