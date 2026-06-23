"""
Product reports views — variantes and reportes.

Extracted from phase3_views_part2.py during AppView decomposition.
"""

import flet as ft

from ui.components import AppHeader, SnackBarHelper
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def show_variantes(app):
    """Display product variants management view."""
    C = app._get_colors()

    try:
        variantes = await app.controller.obtener_variantes()
    except Exception:
        variantes = []

    content = ft.Column(
        [
            AppHeader.create(t("phase3.variantes.title"), "Gestión de variantes de producto"),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            f"Total variantes: {len(variantes)}",
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


async def show_reportes(app):
    """Display customizable reports view."""
    C = app._get_colors()

    try:
        plantillas = await app.controller.obtener_plantillas_reporte()
    except Exception:
        plantillas = []

    content = ft.Column(
        [
            AppHeader.create(t("phase3.reportes.title"), "Reportes personalizables"),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            f"Plantillas guardadas: {len(plantillas)}",
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
