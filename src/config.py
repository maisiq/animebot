from os import getenv
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from dependency_injector import providers, containers

from src.repository.config import get_session_di
from src.repository.repository import UsersRepository, AdminRepository, AnimeRepository

# load env variables
load_dotenv()

TOKEN = getenv("TOKEN")

dp = Dispatcher()
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=[
            "src.routers",
            "src.tasks.notification_task"
        ],
    )

    session = providers.Resource(get_session_di)

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
