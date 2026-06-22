from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from repository import UsersRepository
from repository.config import get_session


class IsAdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject | Message,
        data: Dict[str, Any],
    ) -> Any:
        session = get_session()
        repo = UsersRepository(session)
        user = await repo.get_user_by_id(event.chat.id)
        await session.close()
        if user.is_admin:
            result = await handler(event, data)
            return result
        
