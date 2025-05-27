FROM python:3.10.16-slim-bullseye AS python


FROM python AS build-stage

ARG BUILD=dev

RUN apt-get update && apt-get install -y gcc

COPY ./requirements.txt /requirements.txt

RUN pip wheel --wheel-dir /usr/src/app/wheels -r /requirements.txt


FROM python AS run-stage

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /animeBot

COPY --from=build-stage /usr/src/app/wheels /wheels/

RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
    && rm -rf /wheels/

COPY . .

CMD ["python", "src/main.py"]
