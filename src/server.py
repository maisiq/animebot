from aiogram.types import Update
from aiohttp import web
from aiohttp.web_request import Request

from bot import bot, dp
from config import SERVER_HOST, SERVER_PORT
from init import init


async def handle(request: Request):
    if request.can_read_body:
        try:
            update_data = await request.json()
            update = Update(**update_data)
            await dp.feed_update(bot, update)
        except Exception as e:
            print("Failed to process new updates: ", str(e))
            return web.json_response({"statusCode": 400, "body": "bad request"})
    return web.json_response({"statusCode": 200, "body": "ok"})


def run_server():
    app = web.Application()
    app.cleanup_ctx.append(init)
    app.router.add_post('/webhook', handle)
    app.router.add_get('/webhook', handle)

    web.run_app(
        app, 
        host=SERVER_HOST, 
        port=int(SERVER_PORT),
    )
