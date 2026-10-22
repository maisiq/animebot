import json
import os

import aiohttp
from bs4.element import Tag
from dependency_injector.wiring import Provide, inject

from bot import bot
from container import Container
from logger import get_logger
from tasks.scrapping_task.modelsDTO import AnimeEpisode
from uow import UnitOfWork


def retrieve_data_from_last_update_item(item: Tag):
    log = get_logger()

    title_ru: str = item.find('div', class_='aw-name').text.strip()
    meta_info: str = item.find('div', class_='aw-meta').text.strip()

    if not meta_info.startswith(("Серия", "Серии")):
        log.warning("unexpected_meta_line", meta=meta_info)
        return
    episode_info_raw, studio_date_raw = meta_info.split("·")

    episode_number_str = (
        episode_info_raw
        .removeprefix("Серия")
        .removeprefix("Серии")
        .strip()
    )
    studio_name, _ = studio_date_raw.split("—")

    return {
        'title_ru': title_ru,
        'episode_number': episode_number_str,
        'studio_name': studio_name.strip(),
    }


def update_storage_list(current_episode_list: list[AnimeEpisode]):
    with open('src/tasks/scrapping_task/last_updated.json', 'w+', encoding='utf-8') as f:
        python_data = [episode.model_dump() for episode in current_episode_list]
        json.dump(python_data, f, indent=3, ensure_ascii=False)


def get_saved_episode_list():
    with open('src/tasks/scrapping_task/last_updated.json', 'r', encoding='utf-8') as f:
        # check whether file is empty
        if os.stat(f.name).st_size != 0:
            saved_episode_list = {AnimeEpisode.model_validate(item) for item in json.load(f)}
        else:
            saved_episode_list = set()
        return saved_episode_list


@inject
async def get_html_from_website(url: str, uow: UnitOfWork = Provide[Container.uow]):
    log = get_logger()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    log.error(
                        "scrapping_http_error",
                        url=url,
                        status=resp.status,
                        body=await resp.text(),
                    )
                    return
                return await resp.text()
    except aiohttp.ClientConnectionError as e:
        log.error("scrapping_connection_failed", url=url, exc_info=e)
        async with uow:
            admins = await uow.users.get_admins()

        for a in admins:
            await bot.send_message(
                a.id,
                f'Ошибка подключения к источнику парсинга - {url}\n'
                f'Подробнее: {str(e)}'
            )
