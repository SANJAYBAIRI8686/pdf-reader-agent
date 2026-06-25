import logging
import sys
# pyright: ignore [reportMissingImports]
import structlog
# pyright: ignore [reportMissingImports]
from app.core.config import settings

def setup_logging() -> None:
    """
    Configures standard logging and structlog to provide unified, structured logs.
    """
    # Define processor pipeline for structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.DEBUG and settings.APP_ENV == "development":
        # Human-readable color console rendering for local dev
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # JSON renderer for production (cloud logs ingestion)
        processors.append(structlog.processors.JSONRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.DEBUG else logging.INFO
        ),
        cache_logger_on_first_use=True,
    )

    # Intercept standard library logging and format it nicely
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
    )

    # Silence verbose logs from external libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG and settings.APP_ENV == "development" else logging.WARNING
    )
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)

# Instantiate a default logger for ease of import
logger = structlog.get_logger()
