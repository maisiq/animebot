"""Фоновая задача автодобавления сезонов с animego.me.

Скрапит страницу сезона (например, /anime/season/2026/fall), собирает ссылки
на карточки аниме и для каждой новой позиции заносит в базу Origin и Season.
Пока что первоисточник дублирует сезон: title_en = title_ru, недостающие
поля заполняются русским названием.
"""

import asyncio
from datetime import datetime
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from sqlalchemy.exc import SQLAlchemyError

from config import SCRAPPING_TASK_URL
from logger import get_logger
from tasks.scrapping_task.utils import get_html_from_website
from uow import UnitOfWork

log = get_logger(__name__)

MAX_PAGES = 15
SEASONS = ('winter', 'spring', 'summer', 'fall')


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


async def season_scrapper():
    base_url = season_base_url()
    list_url = urljoin(base_url, current_season_path().lstrip('/'))
    log.info("season_scrapping_started", url=list_url)

    from dependency_injector.wiring import Provide
    from container import Container
    uow_factory = Provide[Container.uow.provider]
    uow: UnitOfWork = uow_factory()

    added_titles: list[str] = []

    async with uow:
        anime_pages = await collect_anime_urls(list_url, base_url)
        for page_url, cover in sorted(anime_pages.items()):
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
            cover = _fetch_cover(soup) or cover or ''

            try:
                if await save_season_if_new(uow, title_ru, cover):
                    added_titles.append(title_ru)
                    await uow.commit()
                else:
                    await uow._session.rollback()
            except SQLAlchemyError as e:
                await uow._session.rollback()
                log.error("season_save_failed", title=title_ru, url=page_url, exc_info=e)

            await asyncio.sleep(1)

    if added_titles:
        log.info("seasons_added", count=len(added_titles), titles=added_titles)
    else:
        log.info("no_new_seasons_found", url=list_url)
