from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from repository.config import get_session
from repository.repository import UsersRepository


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
