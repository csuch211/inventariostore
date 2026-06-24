"""Notifications views for notification management.

Provides UI for notifications, templates, channels, and preferences.
"""

import asyncio

import flet as ft

from config.settings import THEME_PRIMARY_COLOR, THEME_SUCCESS_COLOR, THEME_WARNING_COLOR, THEME_ACCENT_COLOR
from ui.components import AppHeader, FormField, SnackBarHelper
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


# ============ Notificaciones ============


async def show_notificaciones(app):
    """Display notifications management view."""
    C = app._get_colors()
    controller = app.controller

    tipo_filter = ft.Dropdown(
        label="Tipo",
        options=[
            ft.dropdown.Option(key="", text="Todos"),
            ft.dropdown.Option(key="info", text="Info"),
            ft.dropdown.Option(key="warning", text="Advertencia"),
            ft.dropdown.Option(key="error", text="Error"),
            ft.dropdown.Option(key="success", text="Éxito"),
        ],
        value="",
        width=150,
        fill_color="#F8FAFC",
        color="#0F172A",
    )

    async def refresh():
        tipo = tipo_filter.value or None
        try:
            notificaciones = await controller.obtener_notificaciones(tipo=tipo)
            no_leidas = await controller.contar_no_leidas()
        except Exception:
            notificaciones = []
            no_leidas = 0

        # Header with count
        header_row = ft.Row([
            ft.Text(f"Notificaciones ({no_leidas} sin leer)", size=14, weight=ft.FontWeight.BOLD),
            ft.Button(
                content=ft.Text("Marcar todas leídas", size=12),
                on_click=lambda e: asyncio.create_task(mark_all_read()),
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        rows = []
        for n in notificaciones:
            tipo = n.get("tipo", "info")
            tipo_color = {
                "info": THEME_PRIMARY_COLOR,
                "warning": THEME_WARNING_COLOR,
                "error": THEME_ACCENT_COLOR,
                "success": THEME_SUCCESS_COLOR,
            }.get(tipo, "#475569")

            estado = n.get("estado", "")
            is_read = estado == "leido"

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Icon(
                            ft.icons.Icons.CIRCLE if not is_read else ft.icons.Icons.CHECK_CIRCLE,
                            color=tipo_color if not is_read else "#6B7280",
                            size=12,
                        )),
                        ft.DataCell(ft.Text(str(n.get("titulo", "")), weight=ft.FontWeight.BOLD if not is_read else ft.FontWeight.NORMAL)),
                        ft.DataCell(ft.Text(str(n.get("mensaje", ""))[:50])),
                        ft.DataCell(ft.Text(tipo.upper(), color=tipo_color)),
                        ft.DataCell(ft.Text(str(n.get("creado_en", ""))[:16])),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.Icons.VISIBILITY,
                                    icon_color=THEME_PRIMARY_COLOR,
                                    tooltip="Marcar leído",
                                    visible=not is_read,
                                    on_click=lambda ev, nid=n["id"]: asyncio.create_task(mark_read(nid)),
                                ),
                                ft.IconButton(
                                    icon=ft.icons.Icons.DELETE,
                                    icon_color=THEME_ACCENT_COLOR,
                                    tooltip="Eliminar",
                                    on_click=lambda ev, nid=n["id"]: asyncio.create_task(delete_notification(nid)),
                                ),
                            ])
                        ),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("")),
                ft.DataColumn(ft.Text("Título")),
                ft.DataColumn(ft.Text("Mensaje")),
                ft.DataColumn(ft.Text("Tipo")),
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay notificaciones", color="#475569"),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Notificaciones", "Centro de notificaciones"),
                ft.Container(
                    content=ft.Row([tipo_filter, header_row], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=20,
                ),
                body,
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    tipo_filter.on_change = lambda e: asyncio.create_task(refresh())

    async def mark_read(notificacion_id):
        await controller.marcar_leido(notificacion_id)
        await refresh()

    async def mark_all_read():
        await controller.marcar_todas_leidas()
        SnackBarHelper.success(app.page, "Todas las notificaciones marcadas como leídas")
        await refresh()

    async def delete_notification(notificacion_id):
        await controller.eliminar_notificacion(notificacion_id)
        await refresh()

    await refresh()


# ============ Plantillas de Notificación ============


async def show_plantillas_notificacion(app):
    """Display notification templates management view."""
    C = app._get_colors()
    controller = app.controller

    async def refresh():
        try:
            plantillas = await controller.obtener_plantillas_notificacion()
        except Exception:
            plantillas = []

        rows = []
        for p in plantillas:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(p.get("id", "")))),
                        ft.DataCell(ft.Text(str(p.get("nombre", "")))),
                        ft.DataCell(ft.Text(str(p.get("tipo", "")))),
                        ft.DataCell(ft.Text(str(p.get("asunto", ""))[:40])),
                        ft.DataCell(ft.Text(str(p.get("creado_en", ""))[:10])),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.Icons.DELETE,
                                    icon_color=THEME_ACCENT_COLOR,
                                    tooltip="Eliminar",
                                    on_click=lambda ev, pid=p["id"]: asyncio.create_task(delete_template(pid)),
                                ),
                            ])
                        ),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Nombre")),
                ft.DataColumn(ft.Text("Tipo")),
                ft.DataColumn(ft.Text("Asunto")),
                ft.DataColumn(ft.Text("Creado")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay plantillas", color="#475569"),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Plantillas de Notificación", "Gestión de plantillas"),
                ft.Container(
                    content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                    padding=20,
                ),
                body,
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    async def open_new(e):
        nombre = FormField.create_text_field("Nombre")
        asunto = FormField.create_text_field("Asunto")
        cuerpo = FormField.create_text_field("Cuerpo del mensaje")
        tipo = FormField.create_dropdown("Tipo", ["email", "push", "sms"])
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.crear_plantilla_notificacion(
                    nombre=nombre.value or "",
                    asunto=asunto.value or "",
                    cuerpo=cuerpo.value or "",
                    tipo=tipo.value or "email",
                )
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, "Plantilla creada")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Nueva Plantilla"),
            content=ft.Column([nombre, asunto, cuerpo, tipo, err], tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: app.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    async def delete_template(template_id):
        ok, res = await controller.eliminar_plantilla_notificacion(template_id)
        if ok:
            SnackBarHelper.success(app.page, "Plantilla eliminada")
            await refresh()
        else:
            SnackBarHelper.error(app.page, (res or {}).get("error", "Error"))

    new_btn = ft.Button(
        content=ft.Row([
            ft.Icon(ft.icons.Icons.ADD, color="white"),
            ft.Text("Nueva Plantilla", color="white"),
        ], spacing=5),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    await refresh()
