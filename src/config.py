from os import getenv

# Global

TRUTHY_VALUES = {"1", "true", "yes", "on"}
DEBUG = getenv("ANIME_DEBUG", "").strip().lower() in TRUTHY_VALUES

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

# Tasks

SCRAPPING_TASK_INTERVAL = getenv("ANIME_BOT_SCRAPPING_TASK_INTERVAL")
SCRAPPING_TASK_URL = getenv("ANIME_BOT_SCRAPPING_TASK_URL")

SEASON_SCRAPPING_TASK_INTERVAL = getenv("ANIME_BOT_SEASON_SCRAPPING_TASK_INTERVAL", "1440")
