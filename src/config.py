from os import getenv

# Global

DEBUG = getenv("ANIME_DEBUG")

# Bot

BOT_TOKEN = getenv("ANIME_BOT_TOKEN")

_admin_list = getenv("ANIME_BOT_ADMIN_LIST")
ADMIN_LIST = [int(s) for s in _admin_list.split(",")] if _admin_list else []


# Server

SERVER_HOST = getenv("ANIME_SERVER_HOST")
SERVER_PORT = getenv("ANIME_SERVER_PORT")

# DB

DB_DSN = getenv("ANIME_DB_DSN")
DB_SCHEMA = getenv("ANIME_DB_SCHEMA", "animealarm")
