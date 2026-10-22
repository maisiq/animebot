from asyncio import Queue

from bs4 import BeautifulSoup
from bs4.element import Tag

from config import SCRAPPING_TASK_URL
from logger import get_logger
from tasks.scrapping_task.modelsDTO import AnimeEpisode
from tasks.scrapping_task.utils import (
    get_html_from_website,
    get_saved_episode_list,
    retrieve_data_from_last_update_item,
    update_storage_list,
)

log = get_logger(__name__)


async def scrapper(queue: Queue):
    log.info("scrapping_started", url=SCRAPPING_TASK_URL)
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
        for episode in new_series:
            await queue.put(episode)

        # сохранить новые эпизоды в локальный файл
        update_storage_list(current_episode_list)
        log.info(
            "new_episodes_found",
            count=len(new_series),
            episodes=[f"{e.title_ru} #{e.episode_number} [{e.studio_name}]" for e in new_series],
        )
