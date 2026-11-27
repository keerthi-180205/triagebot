"""Logging setup shared by the web app and the worker.

Call setup_logging() once at startup. Wrap work in log_context() so every log line
shows which delivery or run it belongs to. Never log secrets or tokens.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

LOG_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s [delivery=%(delivery_id)s run=%(run_id)s] %(message)s"
)

# Context variables are separate for each asyncio task, so concurrent jobs do not mix IDs.
_delivery_id: ContextVar[str] = ContextVar("delivery_id", default="-")
_run_id: ContextVar[str] = ContextVar("run_id", default="-")


class _ContextFilter(logging.Filter):
    """Add the current delivery and run IDs to each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.delivery_id = _delivery_id.get()
        record.run_id = _run_id.get()
        return True


def setup_logging(level: str = "INFO") -> None:
    """Send all logs to stderr in one format. Safe to call more than once."""
    handler = logging.StreamHandler()
    handler.addFilter(_ContextFilter())
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # The arq command adds its own handler, which would print each of its lines twice.
    logging.getLogger("arq").handlers.clear()
    # httpx logs every request URL at INFO level.
    logging.getLogger("httpx").setLevel(logging.WARNING)


@contextmanager
def log_context(*, delivery_id: str | None = None, run_id: int | None = None) -> Iterator[None]:
    """Attach IDs to every log line written inside the block."""
    tokens = []
    if delivery_id is not None:
        tokens.append((_delivery_id, _delivery_id.set(delivery_id)))
    if run_id is not None:
        tokens.append((_run_id, _run_id.set(str(run_id))))
    try:
        yield
    finally:
        for variable, token in reversed(tokens):
            variable.reset(token)
