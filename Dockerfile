FROM python:3.12-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# --- build stage: установка зависимостей через uv по uv.lock ---
FROM base AS build-stage

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /animeBot

# Копируем только манифесты — слой пересобирается лишь при изменении зависимостей
COPY pyproject.toml uv.lock ./

# Ставим зависимости в изолированное виртуальное окружение внутри образа
RUN uv sync --frozen --no-install-project --no-dev

# --- runtime stage ---
FROM base AS run-stage

WORKDIR /animeBot

COPY --from=build-stage /animeBot/.venv /animeBot/.venv
ENV PATH="/animeBot/.venv/bin:$PATH"

COPY . .

CMD ["python", "src/main.py"]
