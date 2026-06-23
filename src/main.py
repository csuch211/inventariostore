"""Application entry point.

The logger is imported FIRST so its StreamHandler safety patch is in place
before Flet, services, or controllers attach handlers to the root logger.
This prevents the OSError [Errno 22] that occurs when Flet's event loop
replaces sys.stdout under Python 3.14 on Windows.
"""

import warnings

from utils.logger import setup_logger

# Silence noisy DeprecationWarnings from Flet under Python 3.14+
warnings.filterwarnings("ignore", category=DeprecationWarning, module="flet_runtime")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="flet_core")

from config.settings import ensure_dirs

ensure_dirs()

import flet as ft

from ui.app_view import AppView

logger = setup_logger("main")


async def main(page: ft.Page):
    """Flet entry point."""
    logger.info("Starting %s", "Sistema de Inventario Pro")
    try:
        app = AppView(page)
        await app.start()
    except Exception:
        logger.exception("Fatal error in main()")
        raise


if __name__ == "__main__":
    try:
        ft.run(main)
    except Exception:
        logger.exception("Unhandled exception in ft.run")
        raise
