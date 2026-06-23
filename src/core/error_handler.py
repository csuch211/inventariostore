"""Centralized error handling for controller methods.

Provides a decorator that wraps controller methods with consistent
try/except/logging behavior, eliminating duplicated error handling code.
"""

import functools
import inspect
import sqlite3

from utils.exceptions import (
    DatabaseException,
    InventarioError,
    ValidationException,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


def handle_controller_errors(func):
    """Decorator that provides centralized error handling for controller methods.

    Catches InventarioError (and subclasses) and re-raises them unchanged.
    Catches sqlite3.Error and wraps in DatabaseException.
    Catches other exceptions and wraps in InventarioError with context.

    Works with both sync and async methods.
    """

    @functools.wraps(func)
    async def async_wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except InventarioError:
            raise
        except sqlite3.IntegrityError as e:
            logger.error("Integrity error in %s: %s", func.__name__, e)
            raise DatabaseException(str(e)) from e
        except sqlite3.OperationalError as e:
            logger.error("SQL error in %s: %s", func.__name__, e)
            raise DatabaseException(str(e)) from e
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Validation error in %s: %s", func.__name__, e)
            raise ValidationException(str(e)) from e
        except Exception as e:
            logger.error("Unexpected error in %s: %s", func.__name__, e)
            raise InventarioError(f"{func.__name__} failed: {e}") from e

    @functools.wraps(func)
    def sync_wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except InventarioError:
            raise
        except sqlite3.IntegrityError as e:
            logger.error("Integrity error in %s: %s", func.__name__, e)
            raise DatabaseException(str(e)) from e
        except sqlite3.OperationalError as e:
            logger.error("SQL error in %s: %s", func.__name__, e)
            raise DatabaseException(str(e)) from e
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Validation error in %s: %s", func.__name__, e)
            raise ValidationException(str(e)) from e
        except Exception as e:
            logger.error("Unexpected error in %s: %s", func.__name__, e)
            raise InventarioError(f"{func.__name__} failed: {e}") from e

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
