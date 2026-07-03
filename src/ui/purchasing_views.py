"""Purchasing views for quotations, supplier evaluations, and receiving, refactored for clarity.

Provides UI for managing quotations, evaluating suppliers, and receiving goods.
"""

import asyncio

import flet as ft

from config.settings import (
    THEME_ACCENT_COLOR,
    THEME_PRIMARY_COLOR,
    THEME_SUCCESS_COLOR,
    THEME_WARNING_COLOR,
)
from core.theme_manager import theme_manager
from ui.components import AppHeader, FormField, SnackBarHelper
from utils.i18n import t

from ._utils import _fmt_money, get_logger

logger = get_logger(__name__)


# ============ Cotizaciones ============


async def show_cotizaciones(app):
    """Display quotations management view."""
    theme_manager.palette(page=app.page)
    controller = app.controller

    async def refresh():
        try:
            cotizaciones = await controller.obtener_cotizaciones()
        except Exception as e:
            logger.error("Error al obtener cotizaciones: %s", e)
            cotizaciones = []

        rows = []
        for c in cotizaciones:
            estado = c.get("estado", "")
            estado_color = {
                "solicitada": THEME_WARNING_COLOR,
                "aprobada": THEME_SUCCESS_COLOR,
                "rechazada": THEME_ACCENT_COLOR,
                "convertida": THEME_PRIMARY_COLOR,
            }.get(estado, "#475569")

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(c.get("id", "")))),
                        ft.DataCell(ft.Text(str(c.get("numero", "")))),
                        ft.DataCell(ft.Text(str(c.get("proveedor_nombre", "")))),
                        ft.DataCell(ft.Text(_fmt_money(c.get("subtotal", 0)))),
                        ft.DataCell(ft.Text(estado, color=estado_color)),
                        ft.DataCell(ft.Text(str(c.get("fecha_solicitud", "")))),
                        ft.DataCell(ft.Text(str(c.get("fecha_validez", "")))),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.Icons.CHECK,
                                    icon_color=THEME_SUCCESS_COLOR,
                                    tooltip="Aprobar",
                                    visible=estado == "solicitada",
                                    on_click=lambda ev, cid=c["id"]: asyncio.create_task(aprobar(cid)),
                                ),
                                ft.IconButton(
                                    icon=ft.icons.Icons.CANCEL,
                                    icon_color=THEME_ACCENT_COLOR,
                                    tooltip="Rechazar",
                                    visible=estado == "solicitada",
                                    on_click=lambda ev, cid=c["id"]: asyncio.create_task(rechazar(cid)),
                                ),
                                ft.IconButton(
                                    icon=ft.icons.Icons.SHOPPING_CART,
                                    icon_color=THEME_PRIMARY_COLOR,
                                    tooltip="Convertir a orden",
                                    visible=estado == "aprobada",
                                    on_click=lambda ev, cid=c["id"]: asyncio.create_task(convertir(cid)),
                                ),
                            ])
                        ),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Número")),
                ft.DataColumn(ft.Text("Proveedor")),
                ft.DataColumn(ft.Text("Subtotal")),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Solicitud")),
                ft.DataColumn(ft.Text("Validez")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay cotizaciones", color="#475569"),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Cotizaciones", "Gestión de cotizaciones de proveedores"),
                ft.Container(
                    content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                    padding=20,
                ),
                body,
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    async def aprobar(cotizacion_id):
        ok, res = await controller.aprobar_cotizacion(cotizacion_id)
        if ok:
            SnackBarHelper.success(app.page, "Cotización aprobada")
            await refresh()
        else:
            SnackBarHelper.error(app.page, (res or {}).get("error", "Error"))

    async def rechazar(cotizacion_id):
        ok, res = await controller.rechazar_cotizacion(cotizacion_id)
        if ok:
            SnackBarHelper.success(app.page, "Cotización rechazada")
            await refresh()
        else:
            SnackBarHelper.error(app.page, (res or {}).get("error", "Error"))

    async def convertir(cotizacion_id):
        ok, res = await controller.convertir_a_orden(cotizacion_id)
        if ok:
            SnackBarHelper.success(app.page, f"Orden #{res.get('id', '')} creada")
            await refresh()
        else:
            SnackBarHelper.error(app.page, (res or {}).get("error", "Error"))

    async def open_new(e):
        try:
            proveedores = await controller.obtener_proveedores()
        except Exception as exc:
            logger.error("Error al obtener proveedores: %s", exc)
            proveedores = []

        proveedor_opts = [f"{p.get('id')} — {p.get('nombre', '')}" for p in proveedores]
        proveedor = FormField.create_dropdown("Proveedor", proveedor_opts)
        notas = FormField.create_text_field("Notas")
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                items = [{"descripcion": "Item de prueba", "cantidad": 1, "precio_unitario": 100.0}]
                ok, res = await controller.crear_cotizacion(
                    proveedor_id=int((proveedor.value or "0").split(" — ")[0]),
                    items=items,
                    notas=notas.value or "",
                )
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, f"Cotización {res.get('numero', '')} creada")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Nueva Cotización"),
            content=ft.Column([proveedor, notas, err], tight=True, spacing=10),
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
            ft.Text("Nueva Cotización", color="white"),
        ], spacing=5),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    await refresh()
