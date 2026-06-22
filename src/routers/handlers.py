from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, URLInputFile
from aiogram.utils.formatting import as_marked_section
from aiogram.utils.keyboard import (
    InlineKeyboardBuilder,
    InlineKeyboardButton,
    KeyboardButton,
    ReplyKeyboardBuilder,
)
from dependency_injector.wiring import Provide, inject
from sqlalchemy.exc import SQLAlchemyError

from container import Container
from repository.orm_models import DubbedSeason
from uow import UnitOfWork

router = Router()


# START COMMAND

@router.message(CommandStart())
@inject
async def command_start_handler(
    message: Message,
    state: FSMContext,
    uow: UnitOfWork = Provide[Container.uow],
) -> None:
    await state.clear()

    kb = [
        [KeyboardButton(text="Подписаться на аниме")],
        [KeyboardButton(text="Мои подписки"), KeyboardButton(text="Отменить подписку")]
    ]

    async with uow:
        # добавить пользователя в бд, если он зашел впервые
        user = await uow.users.get_user_by_id(message.chat.id)
        if user is None:
            uow.users.add(message.chat.id)
            await uow.commit()

    await message.answer(
        f"Привет, {message.from_user.full_name}!\n"
        "Узнавай первым о выходе новых эпизодов аниме в любимой озвучке! "
        "Воспользуйся меню и подпишись на уведомления 😉",
        reply_markup=ReplyKeyboardBuilder(kb).as_markup(
            resize_keyboard=True,
            input_field_placeholder="Выберите один из пунктов меню",
        )
    )


# USER SUBSCRIPTIONS


@router.message(F.text.lower() == 'мои подписки')
@inject
async def user_subscription_handler(
    message: Message,
    state: FSMContext,
    uow: UnitOfWork = Provide[Container.uow],
) -> None:
    await state.clear()

    async with uow:
        user = await uow.users.get_user_by_id(message.chat.id)

        if user:
            subscriptions = user.animelist  # TODO: fix one more request to db
        else:
            subscriptions = list()

    seasons = [
        f'[Выход самой первой] {sub.season_name}' if sub.studio_name == '#subscribe_on_first'
        else f'[{sub.studio_name}] {sub.season_name}' 
        for sub in subscriptions
    ]
    if seasons:
        answer = as_marked_section('Ваши подписки:', *seasons, marker='▫️ ')
        await message.answer(**answer.as_kwargs())
    else:
        await message.answer('Список подписок пуст')


# UNSUBSCRIBE

def create_subscribed_season_buttons(subscriptions: list[DubbedSeason]) -> list[InlineKeyboardButton]:
    buttons = []

    for sub in subscriptions:
        if sub.studio_name == '#subscribe_on_first':
            buttons.append(
                [InlineKeyboardButton(text=f'[Выход самой первой] {sub.season_name}', callback_data=str(sub.id))]
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
async def cancel_subscription_handler(
    message: Message,
    state: FSMContext,
    uow: UnitOfWork = Provide[Container.uow],
) -> None:
    await state.clear()

    async with uow:
        user = await uow.users.get_user_by_id(message.chat.id)
        if user:
            subscriptions = user.animelist  # TODO: fix one more request to db
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
    uow: UnitOfWork = Provide[Container.uow],
) -> None:
    async with uow:
        user = await uow.users.get_user_by_id(callback.message.chat.id)

        if callback.data == '#unsubscribe_all':
            user.unsubscribe_all()
        else:
            season = await uow.anime.get_dubbed_season_by_id(int(callback.data))
            user.unsubscribe(season)
        await uow.commit()

        # refresh user's subs
        user = await uow.users.get_user_by_id(callback.message.chat.id)

        if user:
            subscriptions = user.animelist  # TODO: fix one more request to db
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
async def subsribe_query_handler(
    message: Message,
    state: FSMContext,
    uow: UnitOfWork = Provide[Container.uow],
) -> None:
    '''Список доступных аниме по запросу.'''
    async with uow:
        seasons = await uow.anime.get_seasons_by_query(message.text)

    buttons = [
        [InlineKeyboardButton(text=season.title_ru, callback_data=str(season.id))]
        for season in seasons if season
    ]
    builder = InlineKeyboardBuilder(buttons)
    if buttons:
        await message.answer(
            f'Вот что мне удалось найти по запросу "{message.text}":',
            reply_markup=builder.as_markup(),
        )
        await state.set_state(Subscribe.choosing_season)
    else:
        await message.answer('Ничего не найдено. Попробуйте ввести по-другому')


@router.callback_query(Subscribe.choosing_season)
@inject
async def any_message_handler(
    callback: CallbackQuery,
    state: FSMContext,
    uow: UnitOfWork = Provide[Container.uow],
) -> None:
    '''Выводит аниме со списком доступных озвучек.'''
    async with uow:
        season = await uow.anime.get_season_by_id(int(callback.data))
        dubbed_seasons = await uow.anime.get_dubbed_seasons_by_season_id(int(callback.data))

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
            reply_markup=builder.as_markup(),
        )
        await state.set_state(Subscribe.choosing_voiceover_studio)
    else:
        await callback.message.answer(
            'В данный момент список озвучек пуст :(\n'
            'Пожалуйста, сообщите об этом - @maisiq'
        )


@router.callback_query(Subscribe.choosing_voiceover_studio)
@inject
async def add_subscribiton_handler(
    callback: CallbackQuery,
    uow: UnitOfWork = Provide[Container.uow],
) -> None:
    async with uow:
        season = await uow.anime.get_dubbed_season_by_id(int(callback.data))
        user = await uow.users.get_user_by_id(callback.message.chat.id)

        if user.is_subsribed(season):
            await callback.answer('❗️ Вы уже подписаны', show_alert=True)
        else:
            user.subscribe(season)
            try:
                await uow.commit()
                await callback.answer('✅ Подписка оформлена', show_alert=True)
            except SQLAlchemyError:
                await callback.answer('❌ Произошла ошибка, повторите попытку немного позже', show_alert=True)


# should be last handler

@router.message()
@inject
async def default_text_handler(message: Message) -> None:
    kb = [
        [KeyboardButton(text="Подписаться на аниме")],
        [KeyboardButton(text="Мои подписки"), KeyboardButton(text="Отменить подписку")],
    ]
    await message.answer(
        'Воспользуйтесь меню',
        reply_markup=ReplyKeyboardBuilder(kb).as_markup(
            resize_keyboard=True,
            input_field_placeholder='Выберите один из пунктов меню',
        )
    )
