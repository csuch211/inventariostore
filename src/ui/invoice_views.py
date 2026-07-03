"""Invoice views for billing management, refactored for clarity.

Provides UI for creating, viewing, and managing invoices.
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


# ============ Facturas ============


async def show_facturas(app):
    """Display invoices management view."""
    theme_manager.palette(page=app.page)
    controller = app.controller

    async def refresh():
        try:
            facturas = await controller.obtener_facturas()
        except Exception as e:
            logger.error("Error al obtener facturas: %s", e)
            facturas = []

        rows = []
        for f in facturas:
            estado = f.get("estado", "")
            estado_color = {
                "borrador": THEME_WARNING_COLOR,
                "emitida": THEME_PRIMARY_COLOR,
                "pagada": THEME_SUCCESS_COLOR,
                "cancelada": THEME_ACCENT_COLOR,
            }.get(estado, "#475569")

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(f.get("id", "")))),
                        ft.DataCell(ft.Text(str(f.get("numero", "")))),
                        ft.DataCell(ft.Text(str(f.get("cliente_nombre", "")))),
                        ft.DataCell(ft.Text(_fmt_money(f.get("total", 0)))),
                        ft.DataCell(ft.Text(str(f.get("tipo", "")))),
                        ft.DataCell(ft.Text(estado, color=estado_color)),
                        ft.DataCell(ft.Text(str(f.get("fecha_emision", "") or ""))),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.Icons.VISIBILITY,
                                    icon_color=THEME_PRIMARY_COLOR,
                                    tooltip="Ver",
                                    on_click=lambda ev, fid=f["id"]: asyncio.create_task(view_invoice(fid)),
                                ),
                                ft.IconButton(
                                    icon=ft.icons.Icons.CANCEL,
                                    icon_color=THEME_ACCENT_COLOR,
                                    tooltip="Cancelar",
                                    visible=f.get("estado") != "cancelada",
                                    on_click=lambda ev, fid=f["id"]: asyncio.create_task(cancel_invoice(fid)),
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
                ft.DataColumn(ft.Text("Cliente")),
                ft.DataColumn(ft.Text("Total")),
                ft.DataColumn(ft.Text("Tipo")),
                ft.DataColumn(ft.Text("Estado")),
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
                content=ft.Text("No hay facturas registradas", color="#475569"),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column(
                [
                    AppHeader.create("Facturas", "Gestión de facturación"),
                    ft.Container(
                        content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                        padding=20,
                    ),
                    body,
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
            app.page.update()

    async def view_invoice(factura_id):
        factura = await controller.obtener_factura(factura_id)
        if not factura:
            SnackBarHelper.error(app.page, "Factura no encontrada")
            return

        detalle = factura.get("detalle", [])
        detalle_rows = []
        for d in detalle:
            detalle_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(d.get("descripcion", "")))),
                        ft.DataCell(ft.Text(str(d.get("cantidad", 0)))),
                        ft.DataCell(ft.Text(_fmt_money(d.get("precio_unitario", 0)))),
                        ft.DataCell(ft.Text(f"{d.get('descuento_pct', 0)}%")),
                        ft.DataCell(ft.Text(_fmt_money(d.get('impuesto_monto', 0)))),
                        ft.DataCell(ft.Text(_fmt_money(d.get("subtotal", 0)))),
                    ]
                )
            )

        detalle_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Descripción")),
                ft.DataColumn(ft.Text("Cantidad")),
                ft.DataColumn(ft.Text("Precio")),
                ft.DataColumn(ft.Text("Descuento")),
                ft.DataColumn(ft.Text("Impuesto")),
                ft.DataColumn(ft.Text("Subtotal")),
            ],
            rows=detalle_rows,
            heading_row_color="#DBEAFE",
        )

        dialog = ft.AlertDialog(
            title=ft.Text(f"Factura {factura.get('numero', '')}"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Cliente: {factura.get('cliente_nombre', '')}"),
                    ft.Text(f"Tipo: {factura.get('tipo', '')}"),
                    ft.Text(f"Estado: {factura.get('estado', '')}"),
                    ft.Text(f"Notas: {factura.get('notas', '') or ''}"),
                    ft.Divider(),
                    detalle_table,
                    ft.Divider(),
                    ft.Row([
                        ft.Text("Subtotal:", weight=ft.FontWeight.BOLD),
                        ft.Text(_fmt_money(factura.get("subtotal", 0))),
                    ]),
                    ft.Row([
                        ft.Text("Impuestos:", weight=ft.FontWeight.BOLD),
                        ft.Text(_fmt_money(factura.get("impuestos_total", 0))),
                    ]),
                    ft.Row([
                        ft.Text("Descuentos:", weight=ft.FontWeight.BOLD),
                        ft.Text(_fmt_money(factura.get("descuentos_total", 0))),
                    ]),
                    ft.Row([
                        ft.Text("Total:", weight=ft.FontWeight.BOLD, size=18),
                        ft.Text(_fmt_money(factura.get("total", 0)), size=18, weight=ft.FontWeight.BOLD, color=THEME_PRIMARY_COLOR),
                    ]),
                ], spacing=5),
                width=600,
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda ev: app.page.pop_dialog()),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    async def cancel_invoice(factura_id):
        ok, res = await controller.cancelar_factura(factura_id)
        if ok:
            SnackBarHelper.success(app.page, "Factura cancelada")
            await refresh()
        else:
            SnackBarHelper.error(app.page, (res or {}).get("error", "Error"))

    async def open_new(e):
        # Get clients for dropdown
        try:
            clientes = await controller.obtener_clientes()
        except Exception as exc:
            logger.error("Error al obtener clientes: %s", exc)
            clientes = []

        cliente_opts = [f"{c.get('id')} — {c.get('nombre', '')}" for c in clientes]
        cliente = FormField.create_dropdown("Cliente", cliente_opts)
        tipo = FormField.create_dropdown("Tipo", ["factura", "boleta", "nota_credito"])
        notas = FormField.create_text_field("Notas")

        # Items section
        items_container = ft.Container(content=ft.Text("Agrega items desde el formulario de productos", color="#475569"))

        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                # For now, create a simple invoice with a test item
                items = [{"descripcion": "Producto de prueba", "cantidad": 1, "precio_unitario": 100.0}]
                ok, res = await controller.crear_factura(
                    cliente_id=int((cliente.value or "0").split(" — ")[0]),
                    items=items,
                    tipo=tipo.value or "factura",
                    notas=notas.value or "",
                )
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, f"Factura {res.get('numero', '')} creada")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Nueva Factura"),
            content=ft.Column(
                [cliente, tipo, notas, items_container, err],
                tight=True,
                spacing=10,
            ),
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
            ft.Text("Nueva Factura", color="white"),
        ], spacing=5),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    await refresh()
