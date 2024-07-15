import asyncio
import logging

from sqlalchemy.exc import SQLAlchemyError
from dependency_injector.wiring import Provide, inject

from aiogram.utils.markdown import hide_link
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError


from src.tasks.scrapping_task.modelsDTO import AnimeEpisode
from src.repository.repository import AdminRepository, AnimeRepository, UsersRepository
from src.repository.orm_models import DubbedSeason, Season
from src.config import bot, Container


@inject
async def new_episode_worker(
    queue: asyncio.Queue,
    anime_repo: AnimeRepository = Provide[Container.anime_repository],
):
    while True:
        new_episode: AnimeEpisode = await queue.get()

        season = await anime_repo.get_season_by_name(new_episode.title_ru)
        if not season:
            queue.task_done()
            logging.warning(f'Нет сезона с именем {new_episode.title_ru}')
            continue

        try:
            dubbed_season = await anime_repo.get_dubbed_season_by_season_and_studio_name(season.title_ru, new_episode.studio_name)
            if dubbed_season:
                await notify_users(season, new_episode, dubbed_season)
                # заменить коммит на флаш и вынести коммит и добавлять эпизод до уведомлений?
                await add_new_episode(dubbed_season, new_episode)
            else:
                await create_dubbed_season(season, new_episode)
        except SQLAlchemyError as e:
            logging.error(new_episode)

        queue.task_done()


@inject
async def create_dubbed_season(
    season: Season,
    episode: AnimeEpisode,
    admin_repo: AdminRepository = Provide[Container.admin_repository],
):
    admin_repo.add_dubbed_season(season.id, episode.title_ru, episode.studio_name)
    await admin_repo.commit()


@inject
async def add_new_episode(
    dubbed_season: DubbedSeason,
    episode: AnimeEpisode,
    admin_repo: AdminRepository = Provide[Container.admin_repository],
):
    admin_repo.add_episode(episode_number=episode.episode_number, season_id=dubbed_season.id)
    await admin_repo.commit()
    logging.info('Эпизод ({}) {} [{}] добавлен'.format(episode.episode_number, episode.title_ru, episode.studio_name))


@inject
async def notify_users(
    season: Season, 
    new_episode: AnimeEpisode,
    dubbed_season: DubbedSeason,
    anime_repo: AnimeRepository = Provide[Container.anime_repository],
    user_repo: UsersRepository = Provide[Container.user_repository],
):
    users_ids = await user_repo.subscribed_on_season_users_ids(dubbed_season)

    # check if it first studio dubbed this episode; if so, add users subsribed for it
    if not await anime_repo.check_if_new_episodes_exist(season.title_ru, new_episode.episode_number):
        new = await user_repo.subscribed_on_first_dubb_users_ids(season.title_ru)
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
            logging.error(e)
            continue
