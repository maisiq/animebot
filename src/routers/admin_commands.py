import aiohttp
from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.utils.formatting import Bold, as_marked_section
from aiogram.utils.markdown import hide_link
from dependency_injector.wiring import Provide, inject
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError

from config import SCRAPPING_TASK_URL
from container import Container
from repository import AdminRepository
from routers.middleware import IsAdminMiddleware
from uow import UnitOfWork

router = Router()
router.message.middleware(IsAdminMiddleware())


@router.message(F.text.lower() == 'отмена')
async def cancel_current_operation_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer('Отменено.')


# HELPME COMMAND

@router.message(Command("helpme"))
async def list_commands_handler(message: Message):
    '''Команда для вывода всех доступных админу команд'''

    await message.answer(
        "/add_studio NAME - добавление студии озвучки\n"
        "/add_origin - добавить первоисточник\n"
        "/add_season - добавить новый сезон\n"
        "/add_dubbed_season - добавить озвучки для сезона\n"
        "/update_status - обновить статус сезона\n"
        "/origins - список с первоисточниками\n"
        "/studios - список студий озвучки\n"
        "/set_scrapper_url https://new-example.com/ - установить новое значение\n"
        "отмена - для отмены текущей операции"
    )


# ADD STUDIO COMMAND

@router.message(Command('add_studio'))
@inject
async def add_studio_command_handler(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    uow: UnitOfWork = Provide[Container.uow],
) -> None:
    """
    Команда получает название студии озвучки в качестве аргумента и создает объект Studio
    """
    await state.clear()

    async with uow:
        uow.admin.add_studio(command.args)
        try:
            await uow.commit()
            await message.answer('Студия озвучки добавлена')
        except SQLAlchemyError as e:
            await message.answer(f'Ошибка ввода данных.\n {e}')


# ADD ORIGIN COMMAND FLOW

class AddOrigin(StatesGroup):
    adding_title_ru = State()
    adding_title_en = State()
    approve_result = State()


@router.message(Command("add_origin"))
async def add_origin_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Название первоисточника на русском?",)
    await state.set_state(AddOrigin.adding_title_ru)


@router.message(AddOrigin.adding_title_ru)
async def origin_title_ru_added(message: Message, state: FSMContext):
    await state.update_data(title_ru=message.text)
    await message.answer("На английском",)
    await state.set_state(AddOrigin.adding_title_en)


@router.message(AddOrigin.adding_title_en)
async def origin_title_en_added(message: Message, state: FSMContext):
    await state.update_data(title_en=message.text)
    origin = await state.get_data()

    await message.answer(
        text=f"Название[🇷🇺]: {origin['title_ru']}\n"
             f"Название[🇺🇸]: {origin['title_en']}\n"
             f"Добавляю в базу данных? [Да, отмена]",
    )
    await state.set_state(AddOrigin.approve_result)


@router.message(AddOrigin.approve_result, F.text.lower() == 'да')
@inject
async def approve_origin(
    message: Message,
    state: FSMContext,
    uow: UnitOfWork = Provide[Container.uow],
):
    origin = await state.get_data()
    async with uow:
        uow.admin.add_origin(origin['title_ru'], origin['title_en'])
        try:
            await uow.commit()
            await message.answer('Добавлено')
        except SQLAlchemyError:
            await message.answer('Ошибка ввода данных')
    await state.clear()


# ADD SEASON COMMAND flow

class AddSeason(StatesGroup):
    enter_origin_name = State()
    adding_title_ru = State()
    adding_title_en = State()
    season_status = State()
    cover = State()
    approve_result = State()


@router.message(Command("add_season"))
async def add_season_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите точное название первоисточника (/origins для справки)")
    await state.set_state(AddSeason.enter_origin_name)


@router.message(AddSeason.enter_origin_name)
async def enter_origin_name(message: Message, state: FSMContext):
    await state.update_data(origin_name=message.text)
    await message.answer("Название сезона на русском?")
    await state.set_state(AddSeason.adding_title_ru)


@router.message(AddSeason.adding_title_ru)
async def title_ru_added(message: Message, state: FSMContext):
    await state.update_data(title_ru=message.text)
    await message.answer("Теперь на английском",)
    await state.set_state(AddSeason.adding_title_en)


@router.message(AddSeason.adding_title_en)
async def title_en_added(message: Message, state: FSMContext):
    await state.update_data(title_en=message.text)
    await message.answer(
        "В каком статусе находится сезон?\n"
        "Варианты: announced, ongoing, released"
    )
    await state.set_state(AddSeason.season_status)


@router.message(AddSeason.season_status)
async def season_status_added(message: Message, state: FSMContext):
    await state.update_data(season_status=message.text.lower())
    await message.answer("Отправьте ссылку на обложку сезона",)
    await state.set_state(AddSeason.cover)


@router.message(AddSeason.cover)
async def season_cover_added(message: Message, state: FSMContext):
    photo = message.text
    await state.update_data(photo=photo)
    season = await state.get_data()
    await message.answer(
        text=f"<b>Первоисточник:</b> {season['origin_name']}\n"
             f"<b>Название[RU]:</b> {season['title_ru']}\n"
             f"<b>Название[EN]:</b> {season['title_en']}\n"
             f"<b>Статус:</b> {season['season_status']}\n"
             f"{hide_link(season['photo'])}\n"
             f"<b>Добавляю в базу данных? [Да, отмена]</b>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AddSeason.approve_result)


@router.message(AddSeason.approve_result, F.text.lower() == 'да')
@inject
async def approve_season(
    message: Message,
    state: FSMContext,
    uow: UnitOfWork = Provide[Container.uow],
):
    anime = await state.get_data()

    async with uow:
        origin = await uow.admin.get_origin_by_name(anime['origin_name'])
        uow.admin.add_season(
            origin_id=origin.id,
            title_ru=anime['title_ru'],
            title_en=anime['title_en'],
            cover=anime['photo'],
            status=anime['season_status'],
        )
        try:
            await uow.commit()
            await message.answer("Добавлено")
        except SQLAlchemyError:
            await message.answer('Ошибка ввода данных')
    await state.clear()


# ADD DUBBED SEASON COMMAND FLOW

class AddDubbedSeason(StatesGroup):
    season_name = State()
    studio = State()


@router.message(Command("add_dubbed_season"))
async def add_dubbed_season_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(text="Введите точное название сезона аниме на русском")
    await state.set_state(AddDubbedSeason.season_name)


@router.message(AddDubbedSeason.season_name)
async def got_season_name(message: Message, state: FSMContext):
    await state.update_data(season_name=message.text)
    await message.answer(
        text="Студии озвучки, каждую с новой строки:\n"
             "AniLibria, JAM CLUB, SHIZA Project, AnimeVost, Субтитры, "
             "Студийная Банда, Dream Cast, AniDUB, AniRise, #subscribe_on_first"
    )
    await state.set_state(AddDubbedSeason.studio)


@router.message(AddDubbedSeason.studio)
@inject
async def create_dubbed_seasons(
    message: Message,
    state: FSMContext,
    uow: UnitOfWork = Provide[Container.uow],
):
    """
    Получает студии озвучки через запятую и создает DubbedSeason с каждой из них.
    """

    data = await state.get_data()
    studios = message.text.strip().split('\n')

    async with uow:
        season = await uow.admin.get_season_by_name(data['season_name'])
        for studio in studios:
            uow.admin.add_dubbed_season(season.id, season.title_ru, studio)

        try:
            await uow.commit()
            await message.answer('Добавлено')
        except IntegrityError:
            await message.answer('Ошибка. Одной из студий озвучки нет в бд, либо сезон с такой озвучкой уже существует')
        except NoResultFound:
            await message.answer('Ошибка. Сезона с таким названием не существует')

    await state.clear()


class UpdateSeasonStatus(StatesGroup):
    enter_season_name = State()
    update_status = State()
    approve_result = State()


@router.message(Command("update_status"))
async def update_status_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Название сезона на русском?")
    await state.set_state(UpdateSeasonStatus.enter_season_name)


@router.message(UpdateSeasonStatus.enter_season_name)
async def title_ru_entered(message: Message, state: FSMContext):
    await state.update_data(season_name=message.text)
    await message.answer("Статус сезона? announced, ongoing, released")
    await state.set_state(UpdateSeasonStatus.update_status)


@router.message(UpdateSeasonStatus.update_status)
@inject
async def update_season_status(
    message: Message,
    state: FSMContext,
    uow: UnitOfWork = Provide[Container.uow],
):
    data = await state.get_data()
    async with uow:
        await uow.admin.update_season_status(season_name=data['season_name'], status=message.text.lower())
        try:
            await uow.commit()
            await message.answer("Обновлено")
        except SQLAlchemyError:
            await message.answer('Ошибка, проверьте данные')
    await state.clear()


# DB query commands [Origin]

@router.message(Command('origins'))
@inject
async def get_all_origins_handler(
    message: Message,
    state: FSMContext,
    uow: UnitOfWork = Provide[Container.uow],
):
    await state.clear()

    async with uow:
        origins = ['{} ({})'.format(o.title_ru, o.title_en)
                for o in await uow.admin.origin_list()]
    if origins:
        content = as_marked_section(Bold("Список первоисточников:"), *origins, marker="▫️ ")
        await message.answer(**content.as_kwargs())
    else:
        await message.answer("Источники не найдены")


@router.message(Command('studios'))
@inject
async def get_all_studios_handler(
    message: Message,
    state: FSMContext,
    uow: UnitOfWork = Provide[Container.uow],
):
    await state.clear()

    async with uow:
        studios = [o.name for o in await uow.admin.studios_list()]
    content = as_marked_section(Bold("Список студий озвучки:"), *studios, marker="▫️ ")
    await message.answer(**content.as_kwargs())


@router.message(Command('set_scrapper_url'))
async def set_scrapper_url(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    global SCRAPPING_TASK_URL
    _, new_url = message.text.split()

    if not new_url.startswith('https://'):
        await message.answer(f'Ошибка, текущее значение: {SCRAPPING_TASK_URL}')
        return
    async with aiohttp.ClientSession() as session:
        async with session.get(new_url) as response:
            if response.status != 200:
                await message.answer(f'Не удается выполнить успешный запрос, {response.status=}')
            SCRAPPING_TASK_URL = new_url
            await message.answer(f'Ссылка успешно обновлена: {SCRAPPING_TASK_URL}')
