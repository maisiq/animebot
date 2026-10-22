# AnimeAlarm Bot 🌸

Telegram-бот, который позволяет подписаться на аниме-сезон с конкретной студией озвучки и получать уведомления о выходе новых серий.

Под капотом — периодическая задача, которая скрапит страницу обновлений выбранного сайта, сохраняет новые эпизоды в базу данных и рассылает уведомления подписанным пользователям.

## Возможности

**Пользователям:**
- 🔔 Подписка на аниме-сезон с выбором студии озвучки (или подписка на «выход самой первой» серии)
- 📋 Просмотр списка своих подписок («Мои подписки»)
- ❌ Отмена подписок поштучно или всех сразу («Отменить подписку»)
- 🚀 Получение уведомления в момент выхода новой серии

**Администраторам** (команды доступны только пользователям из `ANIME_BOT_ADMIN_LIST`):

| Команда | Описание |
|---|---|
| `/helpme` | Справка по командам |
| `/add_studio` | Добавить студию озвучки |
| `/add_origin` | Добавить оригинальное название аниме (RU/EN) |
| `/add_season` | Добавить сезон |
| `/add_dubbed_season` | Добавить озвученный сезон (связь сезона и студии) |
| `/update_status` | Обновить статус |
| `/origins` | Список оригинальных названий |
| `/studios` | Список студий озвучки |
| `/set_scrapper_url` | Задать URL для скрапинга |

## Технологии

- **Python 3.11+**
- [aiogram 3](https://docs.aiogram.dev/) — фреймворк для Telegram-ботов (работа через webhook на aiohttp)
- [SQLAlchemy 2 (async)](https://docs.sqlalchemy.org/) + [Alembic](https://alembic.sqlalchemy.org/) — ORM и миграции
- **PostgreSQL 17** — хранилище данных
- [APScheduler](https://apscheduler.readthedocs.io/) — периодический скраппинг и рассылка уведомлений
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) — парсинг HTML
- [dependency-injector](https://python-dependency-injector.ets-labs.org/) — DI-контейнер
- [uv](https://github.com/astral-sh/uv) — управление зависимостями (`pyproject.toml` + `uv.lock`)

## Структура проекта

```
.
├── migrations/           # Миграции Alembic
├── src/
│   ├── main.py           # Точка входа (запуск aiohttp-сервера с webhook)
│   ├── server.py         # HTTP-сервер, приём update'ов от Telegram
│   ├── bot.py            # Инициализация Bot и Dispatcher
│   ├── init.py           # DI, планировщик задач, подключение роутеров
│   ├── config.py         # Конфигурация из переменных окружения
│   ├── container.py      # dependency-injector контейнер
│   ├── routers/          # Хендлеры пользовательских и админ-команд
│   ├── repository/       # ORM-модели и репозитории
│   ├── uow/              # Unit of Work
│   ├── tasks/
│   │   ├── scrapping_task/    # Скраппинг сайта с обновлениями
│   │   └── notification_task/ # Рассылка уведомлений о новых сериях
│   └── logger/           # Настройка логирования
├── docker-compose.yml    # Сервисы bot + postgres
├── Dockerfile
├── init.sh               # Проверка/накатка миграций + запуск бота
└── animebot.service      # systemd unit для bare-metal деплоя
```

## Быстрый старт

### 1. Переменные окружения

Скопируйте шаблон `.env-empty` в `.env` и заполните значения:

```bash
cp .env-empty .env
```

| Переменная | Описание |
|---|---|
| `ANIME_BOT_TOKEN` | Токен Telegram-бота (от [@BotFather](https://t.me/BotFather)) |
| `ANIME_BOT_ADMIN_LIST` | ID администраторов через запятую, напр. `123456,789012` |
| `ANIME_BOT_SCRAPPING_TASK_INTERVAL` | Интервал скраппинга в минутах |
| `ANIME_SERVER_HOST` | Хост для webhook-сервера |
| `ANIME_SERVER_PORT` | Порт для webhook-сервера |
| `ANIME_DB_DSN` | Строка подключения к БД, напр. `postgresql+psycopg://user:pass@host:5432/dbname` |
| `ANIME_DB_SCHEMA` | (опционально) Схема БД, по умолчанию `animealarm` |

> Также могут понадобиться `ANIME_BOT_SCRAPPING_TASK_URL` (URL страницы для скрапинга) и переменные PostgreSQL (`POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PASSWORD`) для docker-compose.

### 2. Запуск в Docker

```bash
docker compose up --build
```

Контейнер сам проверит миграции (`init.sh`: `alembic check` → при необходимости autogenerate + `upgrade head`) и запустит бота.

### 3. Локальный запуск (без Docker)

Требуется [uv](https://docs.astral-sh/uv/) и доступный PostgreSQL:

```bash
uv sync                                  # установить зависимости
alembic upgrade head                     # накатить миграции
uv run python src/main.py                # запустить сервер с webhook
```

### 4. Настройка webhook

Бот работает через webhook, поэтому сервер должен быть доступен по HTTPS. Укажите webhook через Bot API:

```bash
curl -F "url=https://<your-domain>/webhook" \
     -F "secret_token=<token>" \
     https://api.telegram.org/bot<ANIME_BOT_TOKEN>/setWebhook
```

## Миграции БД

```bash
alembic revision --autogenerate -m "description of change"  # создать ревизию
alembic upgrade head                                        # применить все миграции
alembic downgrade -1                                        # откатить последнюю
```

Migrations env подхватывает `ANIME_DB_DSN` из `.env` автоматически.

## Деплой на сервер (systemd)

В репозитории есть готовые файлы для bare-metal деплоя:

- `animebot.service` — unit-файл systemd (ожидает проект в `/home/animealarm` с `.venv`)
- `startup.sh` — скрипт запуска

```bash
sudo cp animebot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now animebot
```

## Лицензия

MIT
