"""CRM views for customer relationship management.

Provides UI for contacts, opportunities, pipeline, and activities.
"""

import asyncio

import flet as ft

from config.settings import THEME_PRIMARY_COLOR, THEME_SUCCESS_COLOR, THEME_WARNING_COLOR, THEME_ACCENT_COLOR
from ui.components import AppHeader, FormField, SnackBarHelper
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _fmt_money(v) -> str:
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "$0.00"


# ============ Contactos ============


async def show_contactos(app):
    """Display contacts management view."""
    C = app._get_colors()
    controller = app.controller

    async def refresh():
        try:
            contactos = await controller.obtener_contactos()
        except Exception:
            contactos = []

        rows = []
        for c in contactos:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(c.get("id", "")))),
                        ft.DataCell(ft.Text(f"{c.get('nombre', '')} {c.get('apellido', '')}")),
                        ft.DataCell(ft.Text(str(c.get("email", "") or ""))),
                        ft.DataCell(ft.Text(str(c.get("telefono", "") or ""))),
                        ft.DataCell(ft.Text(str(c.get("cargo", "") or ""))),
                        ft.DataCell(ft.Text(str(c.get("empresa", "") or ""))),
                        ft.DataCell(ft.Text(str(c.get("fuente", "")))),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.Icons.EDIT,
                                    icon_color=THEME_PRIMARY_COLOR,
                                    tooltip="Editar",
                                    on_click=lambda ev, cid=c["id"]: asyncio.create_task(edit_contact(cid)),
                                ),
                                ft.IconButton(
                                    icon=ft.icons.Icons.DELETE,
                                    icon_color=THEME_ACCENT_COLOR,
                                    tooltip="Desactivar",
                                    on_click=lambda ev, cid=c["id"]: asyncio.create_task(deactivate_contact(cid)),
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
                ft.DataColumn(ft.Text("Email")),
                ft.DataColumn(ft.Text("Teléfono")),
                ft.DataColumn(ft.Text("Cargo")),
                ft.DataColumn(ft.Text("Empresa")),
                ft.DataColumn(ft.Text("Fuente")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay contactos registrados", color="#475569"),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Contactos CRM", "Gestión de contactos y seguimiento"),
                ft.Container(
                    content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                    padding=20,
                ),
                body,
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    async def open_new(e):
        nombre = FormField.create_text_field("Nombre")
        apellido = FormField.create_text_field("Apellido")
        email = FormField.create_text_field("Email")
        telefono = FormField.create_text_field("Teléfono")
        cargo = FormField.create_text_field("Cargo")
        empresa = FormField.create_text_field("Empresa")
        fuente = FormField.create_dropdown("Fuente", ["directo", "referido", "web", "evento", "otro"])
        notas = FormField.create_text_field("Notas")
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.crear_contacto(
                    nombre=nombre.value or "",
                    apellido=apellido.value or "",
                    email=email.value or "",
                    telefono=telefono.value or "",
                    cargo=cargo.value or "",
                    empresa=empresa.value or "",
                    fuente=fuente.value or "directo",
                    notas=notas.value or "",
                )
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, "Contacto creado")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Nuevo Contacto"),
            content=ft.Column([nombre, apellido, email, telefono, cargo, empresa, fuente, notas, err],
                             tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: app.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    async def edit_contact(contacto_id):
        contacto = await controller.obtener_contacto(contacto_id)
        if not contacto:
            SnackBarHelper.error(app.page, "Contacto no encontrado")
            return

        nombre = FormField.create_text_field("Nombre", value=contacto.get("nombre", ""))
        apellido = FormField.create_text_field("Apellido", value=contacto.get("apellido", ""))
        email = FormField.create_text_field("Email", value=contacto.get("email", ""))
        cargo = FormField.create_text_field("Cargo", value=contacto.get("cargo", ""))
        empresa = FormField.create_text_field("Empresa", value=contacto.get("empresa", ""))
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.actualizar_contacto(
                    contacto_id,
                    nombre=nombre.value,
                    apellido=apellido.value,
                    email=email.value,
                    cargo=cargo.value,
                    empresa=empresa.value,
                )
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, "Contacto actualizado")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Editar Contacto"),
            content=ft.Column([nombre, apellido, email, cargo, empresa, err],
                             tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: app.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    async def deactivate_contact(contacto_id):
        ok, res = await controller.eliminar_contacto(contacto_id)
        if ok:
            SnackBarHelper.success(app.page, "Contacto desactivado")
            await refresh()
        else:
            SnackBarHelper.error(app.page, (res or {}).get("error", "Error"))

    new_btn = ft.Button(
        content=ft.Row([
            ft.Icon(ft.icons.Icons.ADD, color="white"),
            ft.Text("Nuevo Contacto", color="white"),
        ], spacing=5),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    await refresh()


# ============ Pipeline de Ventas ============


async def show_pipeline(app):
    """Display sales pipeline view."""
    C = app._get_colors()
    controller = app.controller

    async def refresh():
        try:
            pipeline = await controller.pipeline_oportunidades()
            oportunidades = await controller.obtener_oportunidades()
        except Exception:
            pipeline = {}
            oportunidades = []

        # Pipeline summary cards
        states = ["abierta", "ganada", "perdida", "cancelada"]
        state_colors = {
            "abierta": THEME_WARNING_COLOR,
            "ganada": THEME_SUCCESS_COLOR,
            "perdida": THEME_ACCENT_COLOR,
            "cancelada": "#6B7280",
        }
        state_icons = {
            "abierta": ft.icons.Icons.PENDING,
            "ganada": ft.icons.Icons.CHECK_CIRCLE,
            "perdida": ft.icons.Icons.CANCEL,
            "cancelada": ft.icons.Icons.BLOCK,
        }

        pipeline_cards = []
        for state in states:
            data = pipeline.get(state, {"cantidad": 0, "total": 0})
            pipeline_cards.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(state_icons.get(state, ft.icons.Icons.HELP), color=state_colors.get(state, "#6B7280"), size=24),
                        ft.Text(state.upper(), size=12, color=state_colors.get(state, "#6B7280")),
                        ft.Text(str(data["cantidad"]), size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(_fmt_money(data["total"]), size=12, color="#475569"),
                    ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=16,
                    border_radius=10,
                    bgcolor="#F8FAFC",
                    width=180,
                    height=120,
                )
            )

        # Opportunities table
        rows = []
        for o in oportunidades[:20]:
            estado = o.get("estado", "")
            estado_color = state_colors.get(estado, "#6B7280")
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(o.get("id", "")))),
                        ft.DataCell(ft.Text(str(o.get("titulo", "")))),
                        ft.DataCell(ft.Text(f"{o.get('nombre', '')} {o.get('apellido', '')}")),
                        ft.DataCell(ft.Text(_fmt_money(o.get("monto", 0)))),
                        ft.DataCell(ft.Text(estado.upper(), color=estado_color, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(str(o.get("fecha_cierre_estimada", "") or ""))),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.Icons.CHECK,
                                    icon_color=THEME_SUCCESS_COLOR,
                                    tooltip="Ganar",
                                    visible=estado == "abierta",
                                    on_click=lambda ev, oid=o["id"]: asyncio.create_task(change_state(oid, "ganada")),
                                ),
                                ft.IconButton(
                                    icon=ft.icons.Icons.CANCEL,
                                    icon_color=THEME_ACCENT_COLOR,
                                    tooltip="Perder",
                                    visible=estado == "abierta",
                                    on_click=lambda ev, oid=o["id"]: asyncio.create_task(change_state(oid, "perdida")),
                                ),
                            ])
                        ),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Título")),
                ft.DataColumn(ft.Text("Contacto")),
                ft.DataColumn(ft.Text("Monto")),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Cierre")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay oportunidades", color="#475569"),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Pipeline de Ventas", "Seguimiento de oportunidades"),
                ft.Container(
                    content=ft.Row(pipeline_cards, spacing=15, alignment=ft.MainAxisAlignment.CENTER),
                    padding=20,
                ),
                ft.Container(
                    content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                    padding=20,
                ),
                body,
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    async def change_state(oportunidad_id, new_state):
        ok, res = await controller.actualizar_estado_oportunidad(oportunidad_id, new_state)
        if ok:
            SnackBarHelper.success(app.page, f"Oportunidad marcada como {new_state}")
            await refresh()
        else:
            SnackBarHelper.error(app.page, (res or {}).get("error", "Error"))

    async def open_new(e):
        try:
            contactos = await controller.obtener_contactos()
        except Exception:
            contactos = []

        contacto_opts = [f"{c.get('id')} — {c.get('nombre', '')} {c.get('apellido', '')}" for c in contactos]
        contacto = FormField.create_dropdown("Contacto", contacto_opts)
        titulo = FormField.create_text_field("Título")
        monto = FormField.create_text_field("Monto")
        prioridad = FormField.create_dropdown("Prioridad", ["baja", "media", "alta"])
        notas = FormField.create_text_field("Notas")
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.crear_oportunidad(
                    contacto_id=int((contacto.value or "0").split(" — ")[0]),
                    titulo=titulo.value or "",
                    monto=float(monto.value or 0),
                    prioridad=prioridad.value or "media",
                    notas=notas.value or "",
                )
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, "Oportunidad creada")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Nueva Oportunidad"),
            content=ft.Column([contacto, titulo, monto, prioridad, notas, err],
                             tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: app.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    new_btn = ft.Button(
        content=ft.Row([
            ft.Icon(ft.icons.Icons.ADD, color="white"),
            ft.Text("Nueva Oportunidad", color="white"),
        ], spacing=5),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    await refresh()
