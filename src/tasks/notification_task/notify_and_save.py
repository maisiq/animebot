import asyncio

from aiogram.enums import ParseMode
from aiogram.utils.markdown import hide_link
from dependency_injector.providers import Factory
from dependency_injector.wiring import Provide, inject
from sqlalchemy.exc import SQLAlchemyError

from bot import bot
from config import ADMIN_LIST
from container import Container
from logger import get_logger
from repository.orm_models import DubbedSeason, Season
from tasks.scrapping_task.modelsDTO import AnimeEpisode
from uow import UnitOfWork

log = get_logger(__name__)


@inject
async def new_episode_worker(
    queue: asyncio.Queue,
    uow_factory: Factory[UnitOfWork] = Provide[Container.uow.provider],
):
    while True:
        new_episode: AnimeEpisode = await queue.get()
        uow = uow_factory()

        async with uow:
            season = await uow.anime.get_season_by_name(new_episode.title_ru)
            if not season:
                queue.task_done()
                log.warning("season_not_found", title=new_episode.title_ru)
                for admin_id in ADMIN_LIST:
                    await bot.send_message(
                        admin_id,
                        f'Нет сезона с именем {new_episode.title_ru}',
                    )
                continue

            try:
                dubbed_season = await uow.anime.get_dubbed_season_by_season_and_studio_name(
                    season.title_ru,
                    new_episode.studio_name,
                )
                if dubbed_season:
                    await notify_users(season, new_episode, dubbed_season)
                    await add_new_episode(dubbed_season, new_episode)
                else:
                    await create_dubbed_season(season, new_episode)
            except SQLAlchemyError as e:
                log.error(
                    "db_error_while_processing_episode",
                    episode=new_episode.episode_number,
                    title=new_episode.title_ru,
                    exc_info=e,
                )

        queue.task_done()


@inject
async def create_dubbed_season(
    season: Season,
    episode: AnimeEpisode,
    uow: UnitOfWork = Provide[Container.uow],
):
    async with uow:
        uow.admin.add_dubbed_season(season.id, episode.title_ru, episode.studio_name)
        await uow.commit()


@inject
async def add_new_episode(
    dubbed_season: DubbedSeason,
    episode: AnimeEpisode,
    uow: UnitOfWork = Provide[Container.uow],
):
    async with uow:
        uow.admin.add_episode(episode_number=episode.episode_number, season_id=dubbed_season.id)
        await uow.commit()
        log.info(
            "episode_added",
            episode=episode.episode_number,
            title=episode.title_ru,
            studio=episode.studio_name,
        )


@inject
async def notify_users(
    season: Season,
    new_episode: AnimeEpisode,
    dubbed_season: DubbedSeason,
    uow: UnitOfWork = Provide[Container.uow],
):
    async with uow:
        users_ids = await uow.users.subscribed_on_season_users_ids(dubbed_season)

        # check if it first studio dubbed this episode; if so, add users subsribed for it
        if not await uow.anime.check_if_new_episodes_exist(season.title_ru, new_episode.episode_number):
            new = await uow.users.subscribed_on_first_dubb_users_ids(season.title_ru)
            users_ids.extend(new)

    for user_id in set(users_ids):
        try:
            await bot.send_message(
                user_id,
                f'Вышел новый эпизод аниме:\n'
                f'<b>{season.title_ru}</b>\n'
                f'<b>Эпизод:</b> {new_episode.episode_number}\n'
                f'<b>Озвучка:</b> {new_episode.studio_name}!\n'
                f'{hide_link(season.cover)}',
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            log.warning("notification_failed", user_id=user_id, exc_info=e)
            continue
