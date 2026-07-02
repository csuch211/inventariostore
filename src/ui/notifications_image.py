"""
Notifications and image search views — push queue and image search.

Extracted from phase3_views_part2.py during AppView decomposition.
Re-exported by ui/extended_features.py.
"""

import asyncio

import flet as ft

from config.settings import (
    THEME_ACCENT_COLOR,
    THEME_ACCENT_LIGHT,
    THEME_PRIMARY_COLOR,
    THEME_SUCCESS_COLOR,
    THEME_SUCCESS_LIGHT,
    THEME_WARNING_COLOR,
    THEME_WARNING_LIGHT,
)
from core.theme_manager import theme_manager
from ui.components import AppHeader, SnackBarHelper
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _c(app):
    """Get the active color palette."""
    return theme_manager.palette(page=app.page)


# ============ Push Queue ============


async def show_push_queue(app):
    """Display push notification queue view."""
    c = _c(app)
    controller = app.controller

    estado_filter = ft.Dropdown(
        label="Filtrar por estado",
        options=[
            ft.dropdown.Option(key="", text="Todos"),
            ft.dropdown.Option(key="pendiente", text="Pendiente"),
            ft.dropdown.Option(key="enviado", text="Enviado"),
            ft.dropdown.Option(key="fallido", text="Fallido"),
        ],
        value="",
        width=200,
        fill_color=c["input_fill"],
        color=c["text_primary"],
        text_style=ft.TextStyle(color=c["text_primary"], size=14),
    )

    async def refresh():
        try:
            estado = estado_filter.value or None
            jobs = await controller.obtener_jobs_push(estado=estado)
        except Exception as e:
            logger.error("Error al obtener jobs push: %s", e)
            jobs = []

        rows = []
        for j in jobs:
            estado_val = j.get("estado", "")
            estado_color = {
                "pendiente": THEME_WARNING_COLOR,
                "enviado": THEME_SUCCESS_COLOR,
                "fallido": THEME_ACCENT_COLOR,
            }.get(estado_val, c["text_secondary"])

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(j.get("id", "")))),
                        ft.DataCell(ft.Text(str(j.get("tipo", "")))),
                        ft.DataCell(ft.Text(str(j.get("destinatario", "")))),
                        ft.DataCell(ft.Text(str(j.get("asunto", ""))[:40])),
                        ft.DataCell(ft.Text(estado_val, color=estado_color)),
                        ft.DataCell(ft.Text(str(j.get("intentos", 0)))),
                        ft.DataCell(ft.Text(str(j.get("creado_en", "")))),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Tipo")),
                ft.DataColumn(ft.Text("Destinatario")),
                ft.DataColumn(ft.Text("Asunto")),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Intentos")),
                ft.DataColumn(ft.Text("Fecha")),
            ],
            rows=rows,
            heading_row_color=c["primary_light"],
        )

        stats = {
            "total": len(jobs),
            "pendiente": sum(1 for j in jobs if j.get("estado") == "pendiente"),
            "enviado": sum(1 for j in jobs if j.get("estado") == "enviado"),
            "fallido": sum(1 for j in jobs if j.get("estado") == "fallido"),
        }

        stats_row = ft.Row(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Total", size=12, color=c["text_secondary"]),
                            ft.Text(str(stats["total"]), size=24, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=4,
                    ),
                    padding=16,
                    border_radius=8,
                    bgcolor=c["input_fill"],
                    width=120,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Pendientes", size=12, color=THEME_WARNING_COLOR),
                            ft.Text(
                                str(stats["pendiente"]),
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=THEME_WARNING_COLOR,
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=16,
                    border_radius=8,
                    bgcolor=THEME_WARNING_LIGHT,
                    width=120,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Enviados", size=12, color=THEME_SUCCESS_COLOR),
                            ft.Text(
                                str(stats["enviado"]),
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=THEME_SUCCESS_COLOR,
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=16,
                    border_radius=8,
                    bgcolor=THEME_SUCCESS_LIGHT,
                    width=120,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Fallidos", size=12, color=THEME_ACCENT_COLOR),
                            ft.Text(
                                str(stats["fallido"]),
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=THEME_ACCENT_COLOR,
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=16,
                    border_radius=8,
                    bgcolor=THEME_ACCENT_LIGHT,
                    width=120,
                ),
            ],
            spacing=15,
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay jobs en la cola", color=c["text_secondary"]),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column(
                [
                    AppHeader.create(t("phase3.push.title"), "Cola de notificaciones push"),
                    ft.Container(content=stats_row, padding=20),
                    ft.Container(
                        content=ft.Row(
                            [estado_filter, refresh_btn, despachar_btn],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=20,
                    ),
                    body,
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
            app.page.update()

    estado_filter.on_change = lambda e: asyncio.create_task(refresh())

    async def handle_refresh(e):
        await refresh()

    async def handle_despachar(e):
        try:
            result = await controller.despachar_jobs_push()
            enviados = result.get("enviados", 0)
            fallidos = result.get("fallidos", 0)
            SnackBarHelper.success(
                app.page, f"Despachados: {enviados} enviados, {fallidos} fallidos"
            )
            await refresh()
        except Exception:
            SnackBarHelper.error(app.page, "Error al despachar notificaciones.")

    refresh_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.REFRESH, color="white"),
                ft.Text("Actualizar", color="white"),
            ],
            spacing=5,
        ),
        on_click=handle_refresh,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    despachar_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.SEND, color="white"),
                ft.Text("Despachar Pendientes", color="white"),
            ],
            spacing=5,
        ),
        on_click=handle_despachar,
        style=ft.ButtonStyle(bgcolor=THEME_SUCCESS_COLOR),
    )

    await refresh()


# ============ Image Search ============


async def show_image_search(app):
    """Display image search view."""
    c = _c(app)
    controller = app.controller

    results_container = ft.Container(padding=20, expand=True)
    status_text = ft.Text("", size=12, color=c["text_secondary"])

    ruta_field = ft.TextField(
        label="Ruta de la imagen",
        hint_text="C:\\ruta\\a\\imagen.jpg",
        value="",
        expand=True,
        read_only=False,
        fill_color=c["input_fill"],
        color=c["text_primary"],
    )

    async def do_search(image_path):
        if not image_path:
            SnackBarHelper.error(app.page, "Ingresa la ruta de una imagen")
            return

        status_text.value = "Buscando productos similares..."
        app.page.update()

        try:
            results = await controller.buscar_por_imagen(ruta_imagen=image_path)
        except Exception as ex:
            status_text.value = f"Error: {ex}"
            app.page.update()
            return

        if not results:
            status_text.value = "No se encontraron productos similares"
            results_container.content = ft.Container(
                content=ft.Text("No se encontraron productos similares", color=c["text_secondary"]),
                padding=20,
            )
            app.page.update()
            return

        rows = []
        for r in results:
            similitud = r.get("similitud", 0)
            similitud_pct = f"{similitud * 100:.1f}%" if similitud else "-"

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(r.get("codigo", "")))),
                        ft.DataCell(ft.Text(str(r.get("nombre", "")))),
                        ft.DataCell(ft.Text(str(r.get("cantidad", 0)))),
                        ft.DataCell(ft.Text(f"${r.get('precio', 0):.2f}")),
                        ft.DataCell(ft.Text(similitud_pct)),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(t("products.code"))),
                ft.DataColumn(ft.Text(t("phase1.devoluciones.producto"))),
                ft.DataColumn(ft.Text("Stock")),
                ft.DataColumn(ft.Text("Precio")),
                ft.DataColumn(ft.Text("Similitud")),
            ],
            rows=rows,
            heading_row_color=c["primary_light"],
        )

        results_container.content = ft.Container(content=table, expand=True)
        status_text.value = f"Encontrados {len(results)} productos similares"
        app.page.update()

    async def handle_search(e):
        await do_search(ruta_field.value.strip())

    search_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.SEARCH, color="white"),
                ft.Text("Buscar", color="white"),
            ],
            spacing=5,
        ),
        on_click=handle_search,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    if app.main_view:
        app.main_view.content = ft.Column(
            [
                AppHeader.create(t("phase3.image_search.title"), "Búsqueda por imagen"),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "Ingresa la ruta de una imagen para buscar productos similares en el inventario",
                                size=14,
                                color=c["text_secondary"],
                            ),
                            ft.Container(height=10),
                            ft.Row(
                                [ruta_field, search_btn],
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.START,
                            ),
                            status_text,
                        ],
                        spacing=10,
                    ),
                    padding=20,
                ),
                results_container,
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        app.page.update()
