"""Document management views.

Provides UI for documents, categories, versions, and tags.
"""

import asyncio

import flet as ft

from config.settings import THEME_PRIMARY_COLOR, THEME_SUCCESS_COLOR, THEME_WARNING_COLOR, THEME_ACCENT_COLOR
from ui.components import AppHeader, FormField, SnackBarHelper
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


# ============ Documentos ============


async def show_documentos(app):
    """Display documents management view."""
    C = app._get_colors()
    controller = app.controller

    tipo_filter = ft.Dropdown(
        label="Tipo",
        options=[
            ft.dropdown.Option(key="", text="Todos"),
            ft.dropdown.Option(key="documento", text="Documento"),
            ft.dropdown.Option(key="imagen", text="Imagen"),
            ft.dropdown.Option(key="video", text="Video"),
            ft.dropdown.Option(key="otro", text="Otro"),
        ],
        value="",
        width=150,
        fill_color="#F8FAFC",
        color="#0F172A",
    )

    async def refresh():
        tipo = tipo_filter.value or None
        try:
            documentos = await controller.obtener_documentos(tipo=tipo)
        except Exception:
            documentos = []

        rows = []
        for d in documentos:
            estado = d.get("estado", "")
            estado_color = {
                "borrador": THEME_WARNING_COLOR,
                "publicado": THEME_SUCCESS_COLOR,
                "archivado": "#6B7280",
            }.get(estado, "#475569")

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(d.get("id", "")))),
                        ft.DataCell(ft.Text(str(d.get("titulo", ""))[:40])),
                        ft.DataCell(ft.Text(str(d.get("categoria_nombre", "") or ""))),
                        ft.DataCell(ft.Text(str(d.get("tipo", "")))),
                        ft.DataCell(ft.Text(str(d.get("autor", "")))),
                        ft.DataCell(ft.Text(f"v{d.get('version_actual', 1)}")),
                        ft.DataCell(ft.Text(estado, color=estado_color)),
                        ft.DataCell(ft.Text(str(d.get("actualizado_en", ""))[:10])),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.Icons.EDIT,
                                    icon_color=THEME_PRIMARY_COLOR,
                                    tooltip="Editar",
                                    on_click=lambda ev, did=d["id"]: asyncio.create_task(edit_document(did)),
                                ),
                                ft.IconButton(
                                    icon=ft.icons.Icons.DELETE,
                                    icon_color=THEME_ACCENT_COLOR,
                                    tooltip="Eliminar",
                                    on_click=lambda ev, did=d["id"]: asyncio.create_task(delete_document(did)),
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
                ft.DataColumn(ft.Text("Categoría")),
                ft.DataColumn(ft.Text("Tipo")),
                ft.DataColumn(ft.Text("Autor")),
                ft.DataColumn(ft.Text("Versión")),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Actualizado")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay documentos", color="#475569"),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Gestión Documental", "Administrar documentos y archivos"),
                ft.Container(
                    content=ft.Row([tipo_filter, new_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=20,
                ),
                body,
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    tipo_filter.on_change = lambda e: asyncio.create_task(refresh())

    async def open_new(e):
        titulo = FormField.create_text_field("Título")
        descripcion = FormField.create_text_field("Descripción")
        tipo = FormField.create_dropdown("Tipo", ["documento", "imagen", "video", "otro"])
        visibilidad = FormField.create_dropdown("Visibilidad", ["privado", "publico", "restringido"])
        notas = FormField.create_text_field("Notas")
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.crear_documento(
                    titulo=titulo.value or "",
                    descripcion=descripcion.value or "",
                    tipo=tipo.value or "documento",
                    visibilidad=visibilidad.value or "privado",
                    notas=notas.value or "",
                )
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, f"Documento creado (v{res.get('version', 1)})")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Nuevo Documento"),
            content=ft.Column([titulo, descripcion, tipo, visibilidad, notas, err],
                             tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: app.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    async def edit_document(documento_id):
        doc = await controller.obtener_documento(documento_id)
        if not doc:
            SnackBarHelper.error(app.page, "Documento no encontrado")
            return

        titulo = FormField.create_text_field("Título", value=doc.get("titulo", ""))
        descripcion = FormField.create_text_field("Descripción", value=doc.get("descripcion", ""))
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.actualizar_documento(
                    documento_id,
                    titulo=titulo.value,
                    descripcion=descripcion.value,
                )
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, "Documento actualizado")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Editar Documento"),
            content=ft.Column([titulo, descripcion, err], tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: app.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    async def delete_document(documento_id):
        ok, res = await controller.eliminar_documento(documento_id)
        if ok:
            SnackBarHelper.success(app.page, "Documento eliminado")
            await refresh()
        else:
            SnackBarHelper.error(app.page, (res or {}).get("error", "Error"))

    new_btn = ft.Button(
        content=ft.Row([
            ft.Icon(ft.icons.Icons.ADD, color="white"),
            ft.Text("Nuevo Documento", color="white"),
        ], spacing=5),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    await refresh()
