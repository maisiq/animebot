import logging
from asyncio import Queue

from bs4 import BeautifulSoup
from bs4.element import Tag

from config import SCRAPPING_TASK_URL
from tasks.scrapping_task.modelsDTO import AnimeEpisode
from tasks.scrapping_task.utils import (
    get_html_from_website,
    get_saved_episode_list,
    retrieve_data_from_last_update_item,
    update_storage_list,
)


async def scrapper(log: logging.Logger, queue: Queue):
    log.info("Starting scrapping %s", SCRAPPING_TASK_URL)
    content = await get_html_from_website(SCRAPPING_TASK_URL)

    if not content:
        return

    soup = BeautifulSoup(content, features="html.parser")

    # get episode list with recently updated anime
    last_updated_blocks: list[Tag] = (
        soup
        .find('div', class_='updates-body')
        .find_all('a', class_='aw-item')
    )

    current_episode_list = set()

    for block in last_updated_blocks:
        data = retrieve_data_from_last_update_item(block)
        if not data:
            continue
        new_episode = AnimeEpisode.model_validate(data)
        current_episode_list.add(new_episode)

    # get saved scrapped data from last time
    saved_episode_list = get_saved_episode_list()

    # check whether new scrapped data differ from saved data
    new_series: set[AnimeEpisode] = current_episode_list.difference(saved_episode_list)

    if new_series:
        # добавить новые эпизоды в очередь на рассылку уведомлений
        [await queue.put(episode) for episode in new_series]

        # сохранить новые эпизоды в локальный файл
        update_storage_list(current_episode_list)
        log.info(f'Найдены новые серии: {new_series}')
    else:
        log.info("Новые эпизоды не найдены")
