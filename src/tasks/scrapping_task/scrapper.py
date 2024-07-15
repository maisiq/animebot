from asyncio import Queue
import logging

from bs4 import BeautifulSoup
from bs4.element import Tag

from src.tasks.scrapping_task.utils import (get_html_from_website,
                                            retrieve_data_from_last_update_item,
                                            get_saved_episode_list,
                                            update_storage_list)
from src.tasks.scrapping_task.modelsDTO import AnimeEpisode


URL = 'https://animego.org/'


async def scrapper(queue: Queue):
    content = await get_html_from_website(URL)

    soup = BeautifulSoup(content, features="html.parser")

    # get episode list with recently updated anime
    last_updated_blocks: list[Tag] = soup.find('div', class_='last-update-container').find_all('div', class_='media-body')

    current_episode_list = set()

    for block in last_updated_blocks:
        info = retrieve_data_from_last_update_item(block)
        new_episode = AnimeEpisode.model_validate(info)
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
        logging.info(f'Найдены новые серии: {new_series}')

