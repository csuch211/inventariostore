"""
Centralized logging configuration
"""

import contextlib
import logging
import logging.handlers
import sys

from config.settings import DEBUG, LOG_FILE, LOG_LEVEL, LOG_PATH


def _safe_emit(stream):
    """Return True if stream is writable, False otherwise."""
    try:
        if stream is None:
            return False
        # Detect closed/broken stdio streams (Python 3.14 + Flet on Windows)
        if hasattr(stream, "closed") and stream.closed:
            return False
        # Writing an empty string is a cheap liveness check
        stream.write("")
        return True
    except OSError, ValueError, AttributeError:
        return False


# ------------------------------------------------------------------
# Global safety net for third-party StreamHandlers.
# Flet (and other libs) attach a StreamHandler to the root logger that
# points to sys.stdout. Under Python 3.14 on Windows, the Flet event
# loop can replace/close stdout mid-runtime, raising
#   OSError: [Errno 22] Invalid argument
# when the root logger emits a record. We patch StreamHandler.emit so
# that any handler (ours or a third party's) silently no-ops on a
# broken stream instead of spamming stderr with the traceback.
# ------------------------------------------------------------------
_original_stream_emit = logging.StreamHandler.emit


def _patched_stream_emit(self, record):  # type: ignore[no-redef]
    try:
        stream = self.stream
        if stream is None or (hasattr(stream, "closed") and stream.closed):
            return
        _original_stream_emit(self, record)
    except OSError, ValueError, AttributeError:
        # Stream became invalid between checks. Swallow it; the file
        # handler keeps capturing the message and the app stays up.
        with contextlib.suppress(Exception):
            self.handleError(record)


logging.StreamHandler.emit = _patched_stream_emit  # type: ignore[assignment]


class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that silently drops records when the underlying stream
    becomes invalid (e.g. sys.stdout replaced by Flet's event loop on Windows
    under Python 3.14, which raises OSError [Errno 22]).
    """

    def emit(self, record):
        try:
            if not _safe_emit(self.stream):
                return
            super().emit(record)
        except Exception:
            # Never let logging crash the host application
            self.handleError(record)


def setup_logger(name: str) -> logging.Logger:
    """
    Configure logger with both file and console handlers.

    The console handler is only attached in DEBUG mode, because Flet's
    asyncio event loop on Windows can replace/close sys.stdout during
    runtime, causing OSError [Errno 22] when logging tries to write.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    if logger.handlers:  # Avoid adding handlers multiple times
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.propagate = False

    # NOTE: do NOT override logging.Handler.handleError globally. Doing so
    # breaks subsequent imports in Python 3.14. Per-handler error handling
    # is achieved by wrapping emit() in SafeStreamHandler (below) and by
    # catching OSError on the RotatingFileHandler constructor above.

    # Formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter("%(levelname)s - %(name)s - %(message)s")

    # Ensure log directory exists
    with contextlib.suppress(OSError):
        LOG_PATH.mkdir(parents=True, exist_ok=True)

    # File handler (rotating to prevent huge files)
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=10_000_000,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except OSError:
        # If file logging is unavailable, fall back to NullHandler so the
        # app still works.
        logger.addHandler(logging.NullHandler())
        return logger

    # Console handler: only when stdout is usable and we're in DEBUG mode.
    # In production / packaged apps, the file log is sufficient and avoids
    # the Flet+Win+Py3.14 stdout issue entirely.
    if DEBUG and _safe_emit(sys.stdout):
        console_handler = SafeStreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger
