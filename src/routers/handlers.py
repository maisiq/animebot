import logging

from aiogram import html, F, Router
from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton, InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, PhotoSize, BufferedInputFile, CallbackQuery, URLInputFile
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.formatting import as_list, as_marked_section, Bold
from aiogram.utils.markdown import hide_link

from dependency_injector.wiring import Provide, inject, Closing
from sqlalchemy.exc import SQLAlchemyError

from repository.orm_models import DubbedSeason
from src.repository.repository import UsersRepository, AnimeRepository
from .middleware import IsUserExistsMiddleware
from ..config import bot, Container

router = Router()
# router.message.middleware(IsUserExistsMiddleware())

# START COMMAND


@router.message(CommandStart())
@inject
async def command_start_handler(
    message: Message,
    state: FSMContext,
    user_repo: UsersRepository = Provide[Container.user_repository],
) -> None:
    await state.clear()

    kb = [
        [KeyboardButton(text="Подписаться на аниме")],
        [KeyboardButton(text="Мои подписки"), KeyboardButton(text="Отменить подписку")]
    ]

    # добавить пользователя в бд, если он зашел впервые
    user = await user_repo.get_user_by_id(message.chat.id)
    if user is None:
        user_repo.add(message.chat.id)
        await user_repo.commit()
        logging.info('Добавлен новый пользователь!')

    await message.answer(
        f"Привет, {message.from_user.full_name}!\n"
        "Узнавай первым о выходе новых эпизодов аниме в любимой озвучке! "
        "Воспользуйся меню и подпишись на уведомления 😉", 
        reply_markup=ReplyKeyboardBuilder(kb).as_markup(resize_keyboard=True, 
                                                        input_field_placeholder="Выберите один из пунктов меню")
    )


# USER SUBSCRIPTIONS


@router.message(F.text.lower() == 'мои подписки')
@inject
async def any_message_handler(
    message: Message, 
    state: FSMContext,
    user_repository: UsersRepository = Provide[Container.user_repository],
) -> None:
    await state.clear()

    user = await user_repository.get_user_by_id(message.chat.id)

    if user:
        subscriptions = user.animelist
    else:
        subscriptions = list()

    seasons = [
        f'[Выход самой первой] {sub.season_name}' if sub.studio_name == '#subscribe_on_first'
        else  f'[{sub.studio_name}] {sub.season_name}'
        for sub in subscriptions
    ]
    if seasons:
        answer = as_marked_section('Ваши подписки:', *seasons, marker='▫️ ')
        await message.answer(**answer.as_kwargs())
    else:
        await message.answer('Список подписок пуст')


# UNSUBSCRIBE

# def create_subscribed_season_button(sub: DubbedSeason):
#     if sub.studio_name == '#subscribe_on_first':
#         return [InlineKeyboardButton(text=f'[Выход самой первой] {sub.season_name}', callback_data=str(sub.id))]
#     return [InlineKeyboardButton(text=f'[{sub.studio_name}] {sub.season_name}', callback_data=str(sub.id))]

def create_subscribed_season_buttons(subscriptions: list[DubbedSeason]) -> list[InlineKeyboardButton]:
    buttons = []

    for sub in subscriptions:
        if sub.studio_name == '#subscribe_on_first':
            buttons.append(
                [InlineKeyboardButton(text=f'[Выход самой первой] {sub.season_name}',callback_data=str(sub.id))]
            )
        else:
            buttons.append(
                [InlineKeyboardButton(text=f'[{sub.studio_name}] {sub.season_name}', callback_data=str(sub.id))]
            )

    if len(buttons) > 5:
        buttons += [[InlineKeyboardButton(text='❌ Отписаться от всех', callback_data='#unsubscribe_all')]]
    return buttons


class Unsubscribe(StatesGroup):
    unsubcribe = State()


@router.message(F.text.lower() == 'отменить подписку')
@inject
async def any_message_handler(
    message: Message,
    state: FSMContext,
    user_repo: UsersRepository = Provide[Container.user_repository],
) -> None:
    await state.clear()

    user = await user_repo.get_user_by_id(message.chat.id)
    if user:
        subscriptions = user.animelist
    else:
        subscriptions = list()

    buttons = create_subscribed_season_buttons(subscriptions)
    builder = InlineKeyboardBuilder(buttons)

    if buttons:
        await message.answer('Выберите, чтобы отменить подписку:', reply_markup=builder.as_markup())
    else:
        await message.answer('Список подписок пуст')
    await state.set_state(Unsubscribe.unsubcribe)


@router.callback_query(Unsubscribe.unsubcribe)
@inject
async def unsubscribe_season_handler(
    callback: CallbackQuery, 
    anime_repo: AnimeRepository = Provide[Container.anime_repository],
    user_repo: UsersRepository = Provide[Container.user_repository]
) -> None:
    user = await user_repo.get_user_by_id(callback.message.chat.id)

    if callback.data == '#unsubscribe_all':
        user.unsubscribe_all()
    else:
        season = await anime_repo.get_dubbed_season_by_id(int(callback.data))
        user.unsubscribe(season)
    await user_repo.commit()  

    # refresh user's subs
    user = await user_repo.get_user_by_id(callback.message.chat.id)

    if user:
        subscriptions = user.animelist
    else:
        subscriptions = list()

    buttons = create_subscribed_season_buttons(subscriptions)
    builder = InlineKeyboardBuilder(buttons)

    await callback.answer('Подписка отменена', show_alert=True)

    if buttons:
        await callback.message.edit_reply_markup(callback.inline_message_id, reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text('Список подписок пуст')


# SUBSCRIBE FLOW


class Subscribe(StatesGroup):
    enter_title = State()
    choosing_season = State()
    choosing_voiceover_studio = State()


@router.message(F.text.lower() == 'подписаться на аниме')
async def subsribe_flow_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer('Введите название аниме, которое сейчас выходит')
    await state.set_state(Subscribe.enter_title)


@router.message(Subscribe.enter_title)
@inject
async def subsribe_query_handler(message: Message, 
                                 state: FSMContext,
                                 user_repo: AnimeRepository = Provide[Container.anime_repository]
) -> None:
    ''' Список доступных аниме по запросу '''

    seasons = await user_repo.get_seasons_by_query(message.text)
    buttons = [
        [InlineKeyboardButton(text=season.title_ru, callback_data=str(season.id))]
        for season in seasons if season
    ]
    builder = InlineKeyboardBuilder(buttons)
    if buttons:
        await message.answer(f'Вот что мне удалось найти по запросу "{message.text}":', reply_markup=builder.as_markup())
        await state.set_state(Subscribe.choosing_season)
    else:
        await message.answer('Ничего не найдено. Попробуйте ввести по-другому')


@router.callback_query(Subscribe.choosing_season)
@inject
async def any_message_handler(
    callback: CallbackQuery,
    state: FSMContext,
    anime_repo: AnimeRepository = Provide[Container.anime_repository]
) -> None:
    ''' выводит аниме со списком доступных озвучек '''
    
    season = await anime_repo.get_season_by_id(int(callback.data))
    dubbed_seasons = await anime_repo.get_dubbed_seasons_by_season_id(int(callback.data))

    buttons = []

    for s in dubbed_seasons:
        if s.studio_name == '#subscribe_on_first':
            buttons.append(
                [InlineKeyboardButton(text='✅ На выход первой', callback_data=str(s.id))]
            )
        else:
            buttons.append(
                [InlineKeyboardButton(text=s.studio_name, callback_data=str(s.id))]
            )

    builder = InlineKeyboardBuilder(buttons)
    builder.adjust(2)

    if dubbed_seasons:
        await callback.message.answer_photo(
            photo=URLInputFile(season.cover),
            caption=season.title_ru,
            reply_markup=builder.as_markup()
        )
        await state.set_state(Subscribe.choosing_voiceover_studio)
    else:
        await callback.message.answer('В данный момент список озвучек пуст :(\n'
                                      'Пожалуйста, сообщите об этом - @maisiq')


@router.callback_query(Subscribe.choosing_voiceover_studio)
@inject
async def add_subscribiton_handler(
    callback: CallbackQuery,  
    user_repo: UsersRepository = Provide[Container.user_repository],
    anime_repo: AnimeRepository = Provide[Container.anime_repository],
) -> None:
 
    season = await anime_repo.get_dubbed_season_by_id(int(callback.data))
    user = await user_repo.get_user_by_id(callback.message.chat.id)

    if user.is_subsribed(season):
        await callback.answer('❗️ Вы уже подписаны', show_alert=True)
    else:
        user.subscribe(season)
        try:
            await user_repo.commit()
            await callback.answer('✅ Подписка оформлена', show_alert=True)
        except SQLAlchemyError:
            await callback.answer('❌ Произошла ошибка, повторите попытку немного позже', show_alert=True)

# should be last handler

@router.message()
@inject
async def command_start_handler(
    message: Message, 
) -> None:
    kb = [
        [KeyboardButton(text="Подписаться на аниме")],
        [KeyboardButton(text="Мои подписки"), KeyboardButton(text="Отменить подписку")]
    ]
    await message.answer(
        'Воспользуйтесь меню', 
        reply_markup=ReplyKeyboardBuilder(kb).as_markup(resize_keyboard=True, input_field_placeholder="Выберите один из пунктов меню")
    ) 