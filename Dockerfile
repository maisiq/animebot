FROM python:3.12.4-slim-bullseye as python

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /animeBot

COPY ./requirements/ ./requirements/

ARG BUILD=dev

RUN pip install --no-cache-dir -r ./requirements/${BUILD}.txt

COPY . .

CMD ["python", "src/main.py"]
