import logging
import os
import sys

import structlog


def setup_logger(file_logger: bool = True, json_logs: bool | None = None):
    """Configure structlog on top of stdlib logging (single sink).

    - json_logs=True  -> single-line JSON to stdout (production / journald).
    - json_logs=False -> colorful human-readable output (local dev).

    structlog renders the event and merges structured kwargs into the record,
    then hands everything over to stdlib logging handlers.
    """
    if json_logs is None:
        # default: JSON when stdout is not an interactive terminal (systemd/docker)
        json_logs = not sys.stdout.isatty() or bool(os.getenv("ANIME_LOG_JSON"))

    # keep background task scheduler quiet
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # drop previously attached handlers so repeated setup doesn't duplicate output
    for handler in list(root.handlers):
        root.removeHandler(handler)

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    root.addHandler(stream_handler)

    if file_logger:
        fh = logging.FileHandler("logs/logs.log")
        fh.setLevel(logging.WARNING)
        root.addHandler(fh)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.stdlib.ExtraAdder(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    for handler in root.handlers:
        if json_logs:
            handler.setFormatter(
                structlog.stdlib.ProcessorFormatter(
                    processors=[
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.processors.format_exc_info,
                        structlog.processors.JSONRenderer(ensure_ascii=False),
                    ],
                    foreign_pre_chain=shared_processors,
                )
            )
        else:
            handler.setFormatter(
                structlog.stdlib.ProcessorFormatter(
                    processors=[
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.dev.ConsoleRenderer(colors=True),
                    ],
                    foreign_pre_chain=shared_processors,
                )
            )


def get_logger(name: str | None = None):
    """Return a bound structlog logger."""
    return structlog.get_logger(name or "app")
