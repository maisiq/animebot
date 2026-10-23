import asyncio

from aiohttp.web_app import Application
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot import dp
from config import SCRAPPING_TASK_INTERVAL, SEASON_SCRAPPING_TASK_INTERVAL
from container import Container
from logger.config import get_logger
from routers.admin_commands import router as commands_router
from routers.handlers import router as handlers_router
from tasks.notification_task.notify_and_save import new_episode_worker
from tasks.scrapping_task.scrapper import scrapper
from tasks.scrapping_task.season_scrapper import season_scrapper


async def init(app: Application | None = None):
    container = Container()
    await container.init_resources()

    log = get_logger()

    queue = asyncio.Queue()

    # init periodic scrapping task
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scrapper, 'interval', minutes=float(SCRAPPING_TASK_INTERVAL), args=[queue])

    # init periodic season scrapping task (auto-add new season anime)
    scheduler.add_job(season_scrapper, 'interval', minutes=float(SEASON_SCRAPPING_TASK_INTERVAL))

    log.info("Starting scheduler")
    scheduler.start()

    dp.include_router(commands_router)
    dp.include_router(handlers_router)

    # start bot
    # start_app_task = asyncio.create_task(dp.start_polling(bot))

    # create infinite task for handling notifications when new episode is out
    worker_task = asyncio.create_task(new_episode_worker(queue))

    yield

    log.info("Shutting down dispatcher")
    await dp.emit_shutdown()

    log.info("Canceling bg task")
    worker_task.cancel()

    log.info("Shutting scheduler")
    scheduler.shutdown()

    log.info("Shutting di container")
    await container.shutdown_resources()

    
