from os import getenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dependency_injector import containers, providers
from dotenv import load_dotenv

from repository.config import get_session_di
from repository.repository import AdminRepository, AnimeRepository, UsersRepository

# load env variables
load_dotenv()

TOKEN = getenv("TELEGRAM_TOKEN")

dp = Dispatcher()
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=[
            "routers",
            "tasks.notification_task"
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
