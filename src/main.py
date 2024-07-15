from pathlib import Path
import asyncio
import logging
import sys

# add dirs to $PATH
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent))

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.tasks.scrapping_task.scrapper import scrapper
from src.tasks.notification_task.notify_and_save import new_episode_worker
from src.repository.config import sessionmanager
from src.config import dp, bot, Container
from src.routers.admin_commands import router as commands_router
from src.routers.handlers import router as handlers_router
from logs.log_config import setup_logger


async def main() -> None:
    # init db
    sessionmanager.init()

    queue = asyncio.Queue()

    # init periodic scrapping task
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scrapper, 'interval', minutes=5, args=[queue])
    scheduler.start()

    dp.include_router(commands_router)
    dp.include_router(handlers_router)

    # start bot
    start_app_task = asyncio.create_task(dp.start_polling(bot))

    # create infinite task for handling notifications when new episode is out
    db_handler = asyncio.create_task(new_episode_worker(queue))
    await asyncio.gather(start_app_task, db_handler)


if __name__ == "__main__":
    setup_logger(file_logger=True)

    # start DI container
    container = Container()

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
