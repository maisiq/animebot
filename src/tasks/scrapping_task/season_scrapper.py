"""Фоновая задача автодобавления сезонов с animego.me.

Скрапит страницу сезона (например, /anime/season/2026/fall), собирает ссылки
на карточки аниме и для каждой новой позиции заносит в базу Origin и Season.
Пока что первоисточник дублирует сезон: title_en = title_ru, недостающие
поля заполняются русским названием.

Также со страницы каждой карточки аниме считывается блок «Озвучка» — найденные
студии озвучки привязываются к сезону (DubbedSeason / seasons_with_studio),
чтобы пользователи могли подписаться на выход серий конкретной озвучки.
"""

import asyncio
from datetime import datetime
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from dependency_injector.providers import Factory
from dependency_injector.wiring import Provide, inject
from sqlalchemy.exc import SQLAlchemyError

from config import SCRAPPING_TASK_URL
from container import Container
from logger import get_logger
from tasks.scrapping_task.dub_list import DUB_LIST
from tasks.scrapping_task.dub_scraper import extract_dubbed_studios
from tasks.scrapping_task.utils import get_html_from_website
from uow import UnitOfWork

log = get_logger(__name__)

MAX_PAGES = 15
SEASONS = ('winter', 'spring', 'summer', 'fall')
SUBSCRIBE_ON_FIRST_STUDIO = '#subscribe_on_first'


def season_base_url() -> str:
    """Базовый URL сайта из SCRAPPING_TASK_URL (для обеих задач).

    SCRAPPING_TASK_URL указывает на страницу обновлений, например
    https://animego.me/anime/new_seasons — берём только scheme + host.
    """
    parsed = urlsplit(SCRAPPING_TASK_URL)
    return f"{parsed.scheme}://{parsed.netloc}"


def current_season_path(now: datetime | None = None) -> str:
    now = now or datetime.now()
    month = now.month
    if month <= 2:
        season = 'winter'
    elif month <= 5:
        season = 'spring'
    elif month <= 8:
        season = 'summer'
    else:
        season = 'fall'
    return f'/anime/season/{now.year}/{season}'


def extract_anime_links(soup: BeautifulSoup, base_url: str) -> dict[str, str | None]:
    """Возвращает {URL карточки: URL обложки со страницы списка} .

    Обложка со списка — черновик (thumbnail); финальную берём со страницы
    карточки в блоке .fancybox-trigger-cover (см. _fetch_cover).
    """
    links: dict[str, str | None] = {}
    for item in soup.select('.ani-list__item'):
        if 'entity-list-skeleton' in ' '.join(item.get('class', [])):
            continue
        anchor = item.select_one('.ani-list__item-title a.text-line-clamp')
        if not (anchor and anchor.get('href')):
            continue
        picture = item.select_one('.ani-list__item-picture img')
        cover = (picture.get('src') or picture.get('data-src')) if picture else None
        links[urljoin(base_url, anchor['href'])] = cover
    return links


def _fetch_cover(soup: BeautifulSoup) -> str | None:
    """Обложка со страницы карточки: блок .fancybox-trigger-cover > img."""
    block = soup.select_one('.fancybox-trigger-cover')
    img = block.find('img') if block else None
    if not img:
        return None
    return img.get('src') or img.get('data-src')


def next_page_url(soup: BeautifulSoup, base_url: str) -> str | None:
    navigation = soup.select_one('[data-infinite-scroll-target="navigation"]')
    if not navigation:
        return None
    anchor = navigation.find('a', href=True)
    if not anchor:
        return None
    return urljoin(base_url, anchor['href'])


async def collect_anime_urls(season_list_url: str, base_url: str) -> dict[str, str | None]:
    all_urls: dict[str, str | None] = {}
    url = season_list_url

    for _ in range(MAX_PAGES):
        content = await get_html_from_website(url)
        if not content:
            break

        soup = BeautifulSoup(content, features='html.parser')
        all_urls |= extract_anime_links(soup, base_url)

        url = next_page_url(soup, base_url)
        if not url:
            break
        await asyncio.sleep(1)

    return all_urls


async def save_season_if_new(uow: UnitOfWork, title_ru: str, cover: str | None) -> bool:
    """Добавляет Origin + Season, если такой позиции ещё нет в базе.

    Возвращает True, если запись создана.
    """
    if await uow.anime.season_exists(title_ru):
        return False

    origin = await uow.anime.get_origin_by_title_ru(title_ru)
    if not origin:
        # по условию задачи первоисточник дублирует название сезона,
        # английское название подставляем то же самое
        origin = uow.admin.add_origin(title_ru=title_ru, title_en=title_ru)
        await uow._session.flush()

    uow.admin.add_season(
        origin_id=origin.id,
        title_ru=title_ru,
        title_en=title_ru,
        cover=cover,
        status='ongoing',
    )
    return True


async def sync_dubbed_studios(uow: UnitOfWork, season, dub_names: list[str]) -> list[str]:
    """Привязывает озвучки со страницы карточки к сезону (DubbedSeason).

    Добавляет только те студии, которых у сезона ещё нет; существующие записи
    не удаляются и не трогаются. В voiceover_studios заносятся неизвестные
    названия (кроме служебной '#subscribe_on_first').

    Возвращает список реально добавленных названий.
    """
    existing = await uow.anime.get_dubbed_seasons_names(season.id)
    known_studios = await uow.admin.get_studio_names()
    added: list[str] = []

    for studio_name in dub_names:
        if not studio_name or studio_name in existing:
            continue
        # служебную студию '#subscribe_on_first' не заводим в справочнике,
        # но DubbedSeason с ней создаём (подписка на самую первую озвучку)
        if studio_name != SUBSCRIBE_ON_FIRST_STUDIO and studio_name not in known_studios:
            uow.admin.add_studio(studio_name)
            known_studios.add(studio_name)
        uow.admin.add_dubbed_season(season.id, season.title_ru, studio_name)
        existing.add(studio_name)
        added.append(studio_name)

    return added


@inject
async def season_scrapper(
    uow_factory: Factory[UnitOfWork] = Provide[Container.uow.provider],
):
    base_url = season_base_url()
    list_url = urljoin(base_url, current_season_path().lstrip('/'))
    log.info("season_scrapping_started", url=list_url)

    uow: UnitOfWork = uow_factory()

    added_titles: list[str] = []
    dubbed_added: dict[str, list[str]] = {}

    async with uow:
        anime_pages = await collect_anime_urls(list_url, base_url)
        for page_url, list_cover in sorted(anime_pages.items()):
            content = await get_html_from_website(page_url)
            if not content:
                continue

            soup = BeautifulSoup(content, features='html.parser')
            title_tag = soup.find('h1')
            if not title_tag:
                log.warning("season_card_title_not_found", url=page_url)
                continue

            title_ru = title_tag.get_text(strip=True)
            # обложку берём со страницы карточки, fallback — thumbnail из списка
            cover = _fetch_cover(soup) or list_cover or ''

            # блок «Озвучка» со страницы карточки: словарь DUB_LIST пополняем
            # известными студиями из БД, чтобы распознавать новые названия
            known_studios = set(DUB_LIST) | await uow.admin.get_studio_names()
            dub_names = extract_dubbed_studios(soup, known_studios)

            try:
                is_new = await save_season_if_new(uow, title_ru, cover)
                if is_new:
                    # Season ещё не в сессии как persistent-объект — достаём его,
                    # чтобы получить id для привязки озвучек
                    await uow._session.flush()
                    added_titles.append(title_ru)

                season = await uow.anime.get_season_by_name(title_ru)
                if season is not None and dub_names:
                    added_studios = await sync_dubbed_studios(uow, season, dub_names)
                    if added_studios:
                        dubbed_added.setdefault(title_ru, []).extend(added_studios)

                await uow.commit()
            except SQLAlchemyError as e:
                await uow._session.rollback()
                log.error(
                    "season_save_failed",
                    title=title_ru,
                    url=page_url,
                    dubs=dub_names,
                    exc_info=e,
                )

            await asyncio.sleep(1)

    if added_titles:
        log.info("seasons_added", count=len(added_titles), titles=added_titles)
    else:
        log.info("no_new_seasons_found", url=list_url)

    if dubbed_added:
        log.info(
            "dubbed_seasons_added",
            count=sum(len(v) for v in dubbed_added.values()),
            items={title: studios for title, studios in dubbed_added.items()},
        )
