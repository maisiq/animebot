import json
import logging
import os

import aiohttp
from bs4.element import Tag
from dependency_injector.wiring import Provide, inject

from config import Container, bot
from repository.repository import UsersRepository
from tasks.scrapping_task.modelsDTO import AnimeEpisode


def retrieve_data_from_last_update_item(item: Tag):
    title_ru = item.find('span', class_='last-update-title').text
    episode_number, _ = item.find('div', class_='text-truncate').text.split(' ')
    studio_name = item.find('div', class_='text-gray-dark-6').text.strip('()')

    return {
        'title_ru': title_ru,
        'episode_number': int(episode_number),
        'studio_name': studio_name
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
async def get_html_from_website(url: str, repo: UsersRepository = Provide[Container.user_repository]):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.text()
    except aiohttp.ClientConnectionError as e:
        logging.error(e)
        admins = await repo.get_admins()

        for a in admins:
            await bot.send_message(
                a.id,
                f'Ошибка подключения к источнику парсинга - {url}\n'
                f'Подробнее: {str(e)}'
            )
