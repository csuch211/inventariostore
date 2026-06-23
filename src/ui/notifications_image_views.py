"""
Notifications and image search views — push queue and image search.

Extracted from phase3_views_part2.py during AppView decomposition.
"""

import flet as ft

from ui.components import AppHeader, SnackBarHelper
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def show_push_queue(app):
    """Display push notification queue view."""
    C = app._get_colors()

    try:
        jobs = await app.controller.obtener_jobs_push()
    except Exception:
        jobs = []

    content = ft.Column(
        [
            AppHeader.create(t("phase3.push.title"), "Cola de notificaciones push"),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            f"Jobs en cola: {len(jobs)}",
                            size=14,
                            color=C["text_secondary"],
                        ),
                    ],
                    spacing=10,
                ),
                padding=20,
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()


async def show_image_search(app):
    """Display image search view."""
    C = app._get_colors()

    content = ft.Column(
        [
            AppHeader.create(t("phase3.image_search.title"), "Búsqueda por imagen"),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Selecciona una imagen para buscar productos similares",
                            size=14,
                            color=C["text_secondary"],
                        ),
                    ],
                    spacing=10,
                ),
                padding=20,
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()
