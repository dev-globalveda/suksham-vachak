"""Centralized logging configuration for Suksham Vachak.

This module provides structured logging using structlog with:
- Development mode: Pretty console output with colors
- Production mode: JSON structured logs for log aggregation
- Correlation IDs for request tracing
- Per-module log levels
- Context binding for rich log metadata

Usage:
    from suksham_vachak.logging import get_logger, configure_logging

    # Configure once at startup
    configure_logging(env="development", level="DEBUG")

    # Get a logger for your module
    logger = get_logger(__name__)

    # Log with context
    logger.info("Processing match", match_id="1234", innings=1)

    # Bind context for multiple log calls
    log = logger.bind(match_id="1234")
    log.info("Parsing started")
    log.info("Parsing complete", events=150)
"""

from __future__ import annotations

import logging
import os
import sys
from contextvars import ContextVar
from uuid import uuid4

import structlog
from structlog.types import EventDict, Processor, WrappedLogger

# Context variable for correlation ID (request tracing)
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    """Get the current correlation ID for request tracing."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set or generate a correlation ID for the current context.

    Args:
        correlation_id: Optional ID to use. If None, generates a new UUID.

    Returns:
        The correlation ID that was set.
    """
    if correlation_id is None:
        correlation_id = str(uuid4())[:8]  # Short ID for readability
    correlation_id_var.set(correlation_id)
    return correlation_id


def add_correlation_id(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Structlog processor to add correlation ID to log events."""
    corr_id = get_correlation_id()
    if corr_id:
        event_dict["correlation_id"] = corr_id
    return event_dict


def add_module_context(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Add module name as a structured field."""
    if "logger" in event_dict:
        # Extract just the module name from full path
        logger_name = str(event_dict.pop("logger"))
        if logger_name.startswith("suksham_vachak."):
            # suksham_vachak.parser.cricsheet -> parser.cricsheet
            event_dict["module"] = logger_name.replace("suksham_vachak.", "")
        else:
            event_dict["module"] = logger_name
    return event_dict


# Default log levels per module (can be overridden via env vars)
DEFAULT_MODULE_LEVELS: dict[str, str] = {
    "suksham_vachak.api": "INFO",
    "suksham_vachak.parser": "INFO",
    "suksham_vachak.stats": "INFO",
    "suksham_vachak.context": "INFO",
    "suksham_vachak.commentary": "INFO",
    "suksham_vachak.tts": "INFO",
    "suksham_vachak.rag": "INFO",
    "suksham_vachak.personas": "INFO",
    # Third-party libraries - quieter by default
    "httpx": "WARNING",
    "httpcore": "WARNING",
    "chromadb": "WARNING",
    "uvicorn": "INFO",
    "uvicorn.access": "WARNING",
}


def _get_dev_processors() -> list[Processor]:
    """Get processors for development mode (pretty console output)."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="%H:%M:%S"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        add_correlation_id,
        add_module_context,
        structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback,
        ),
    ]


def _get_prod_processors() -> list[Processor]:
    """Get processors for production mode (JSON structured logs)."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        add_correlation_id,
        add_module_context,
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]


def configure_logging(
    env: str | None = None,
    level: str | None = None,
    module_levels: dict[str, str] | None = None,
) -> None:
    """Configure structured logging for the application.

    Args:
        env: Environment mode. "production" for JSON logs, else pretty console.
             Defaults to LOG_ENV or "development".
        level: Default log level. Defaults to LOG_LEVEL or "INFO".
        module_levels: Per-module log levels. Merged with defaults.

    Environment Variables:
        LOG_ENV: "production" or "development"
        LOG_LEVEL: Default level (DEBUG, INFO, WARNING, ERROR)
        LOG_MODULE_LEVELS: JSON string of module:level pairs
    """
    # Determine environment
    if env is None:
        env = os.getenv("LOG_ENV", "development")

    is_production = env.lower() == "production"

    # Determine default level
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")

    # Merge module levels
    effective_module_levels = DEFAULT_MODULE_LEVELS.copy()
    if module_levels:
        effective_module_levels.update(module_levels)

    # Parse module levels from env if present
    env_levels = os.getenv("LOG_MODULE_LEVELS")
    if env_levels:
        import contextlib
        import json

        with contextlib.suppress(json.JSONDecodeError):
            effective_module_levels.update(json.loads(env_levels))

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    # Set per-module levels
    for module_name, module_level in effective_module_levels.items():
        logging.getLogger(module_name).setLevel(getattr(logging, module_level.upper()))

    # Configure structlog
    processors = _get_prod_processors() if is_production else _get_dev_processors()

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger for the given module.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        A bound structlog logger with context support.

    Example:
        logger = get_logger(__name__)
        logger.info("Event processed", event_type="wicket", batter="Kohli")
    """
    return structlog.get_logger(name)


# Convenience: configure with defaults on import if not already configured
# This ensures logging works even if configure_logging() is never called
if not structlog.is_configured():
    configure_logging()
