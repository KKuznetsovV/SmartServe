import logging
import os

import structlog


def setup_logging(environment: str | None = None) -> None:
    env = environment if environment is not None else os.environ.get("ENVIRONMENT", "development")
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if env != "development" else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
