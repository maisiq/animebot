from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

from src.repository.config import get_session
from src.repository.repository import UsersRepository



class IsUserExistsMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject | Message,
            data: Dict[str, Any],
    ) -> Any:
        ...
        # async with get_session() as session:
        #     repo = UsersRepository(session)
        #     service = UserService(repo)

        #     if event.text == '/start':
        #         return await handler(event, data)
        #     else:
        #         if await service.get_user_by_id(event.chat.id):
        #             return await handler(event, data)
        #         await event.answer('Произошла ошибка. Пожалуйста, воспользуйтесь командой /start')


class IsAdminMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject | Message,
            data: Dict[str, Any],
    ) -> Any:
        async with get_session() as session:
            user = await UsersRepository(session).get_user_by_id(event.chat.id)
            if user.is_admin:
                result = await handler(event, data)
                return result
