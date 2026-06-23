"""Accounting views for double-entry bookkeeping.

Provides UI for journal entries, chart of accounts, and trial balance.
"""

import asyncio

import flet as ft

from config.settings import THEME_PRIMARY_COLOR, THEME_SUCCESS_COLOR
from ui.components import AppHeader, FormField, SnackBarHelper
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _fmt_money(v) -> str:
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "$0.00"


# ============ Asientos Contables ============


async def show_asientos(app):
    """Display journal entries view."""
    C = app._get_colors()
    controller = app.controller

    async def refresh():
        try:
            asientos = await controller.obtener_asientos()
        except Exception:
            asientos = []

        rows = []
        for a in asientos:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(a.get("id", "")))),
                        ft.DataCell(ft.Text(str(a.get("numero", "")))),
                        ft.DataCell(ft.Text(str(a.get("fecha", "")))),
                        ft.DataCell(ft.Text(str(a.get("descripcion", "")))),
                        ft.DataCell(ft.Text(str(a.get("tipo", "")))),
                        ft.DataCell(ft.Text(str(a.get("estado", "")))),
                        ft.DataCell(ft.Text(str(a.get("creado_en", "")))),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Número")),
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Descripción")),
                ft.DataColumn(ft.Text("Tipo")),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Creado")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay asientos contables", color="#475569"),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column(
                [
                    AppHeader.create("Asientos Contables", "Libro diario"),
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

    async def open_new(e):
        fecha = FormField.create_text_field("Fecha", hint="YYYY-MM-DD")
        descripcion = FormField.create_text_field("Descripción")
        tipo = FormField.create_dropdown("Tipo", ["venta", "compra", "pago", "ajuste", "devolucion"])

        # Simple two-line entry
        cuenta_debito = FormField.create_text_field("Cuenta débito (ej: 1.1.01)")
        monto_debito = FormField.create_text_field("Monto débito")
        cuenta_credito = FormField.create_text_field("Cuenta crédito (ej: 4.1.01)")
        monto_credito = FormField.create_text_field("Monto crédito")

        err = ft.Text("", color="#DC2626")

        async def save(ev):
            try:
                movimientos = [
                    {
                        "cuenta_codigo": cuenta_debito.value or "1.1.01",
                        "cuenta_nombre": "Caja",
                        "debito": float(monto_debito.value or 0),
                        "credito": 0,
                    },
                    {
                        "cuenta_codigo": cuenta_credito.value or "4.1.01",
                        "cuenta_nombre": "Ventas",
                        "debito": 0,
                        "credito": float(monto_credito.value or 0),
                    },
                ]
                ok, res = await controller.crear_asiento(
                    fecha=fecha.value or "",
                    descripcion=descripcion.value or "",
                    tipo=tipo.value or "ajuste",
                    movimientos=movimientos,
                )
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, f"Asiento {res.get('numero', '')} creado")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Nuevo Asiento Contable"),
            content=ft.Column([
                ft.Text("Cuenta Débito", weight=ft.FontWeight.BOLD),
                ft.Row([cuenta_debito, monto_debito], spacing=10),
                ft.Text("Cuenta Crédito", weight=ft.FontWeight.BOLD),
                ft.Row([cuenta_credito, monto_credito], spacing=10),
                ft.Divider(),
                fecha,
                descripcion,
                tipo,
                err,
            ], tight=True, spacing=8),
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
            ft.Text("Nuevo Asiento", color="white"),
        ], spacing=5),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    await refresh()


# ============ Plan de Cuentas ============


async def show_plan_cuentas(app):
    """Display chart of accounts view."""
    C = app._get_colors()
    controller = app.controller

    tipo_filter = ft.Dropdown(
        label="Filtrar por tipo",
        options=[
            ft.dropdown.Option(key="", text="Todos"),
            ft.dropdown.Option(key="activo", text="Activos"),
            ft.dropdown.Option(key="pasivo", text="Pasivos"),
            ft.dropdown.Option(key="patrimonio", text="Patrimonio"),
            ft.dropdown.Option(key="ingreso", text="Ingresos"),
            ft.dropdown.Option(key="gasto", text="Gastos"),
        ],
        value="",
        width=200,
        fill_color="#F8FAFC",
        color="#0F172A",
        text_style=ft.TextStyle(color="#0F172A", size=14),
    )

    async def refresh():
        tipo = tipo_filter.value or None
        try:
            cuentas = await controller.obtener_plan_cuentas(tipo=tipo)
        except Exception:
            cuentas = []

        rows = []
        for c in cuentas:
            tipo_color = {
                "activo": THEME_PRIMARY_COLOR,
                "pasivo": THEME_ACCENT_COLOR,
                "patrimonio": THEME_SUCCESS_COLOR,
                "ingreso": "#0EA5E9",
                "gasto": THEME_WARNING_COLOR,
            }.get(c.get("tipo", ""), "#475569")

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(c.get("codigo", "")))),
                        ft.DataCell(ft.Text(str(c.get("nombre", "")))),
                        ft.DataCell(ft.Text(str(c.get("tipo", "")), color=tipo_color)),
                        ft.DataCell(ft.Text(str(c.get("nivel", 1)))),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Código")),
                ft.DataColumn(ft.Text("Nombre")),
                ft.DataColumn(ft.Text("Tipo")),
                ft.DataColumn(ft.Text("Nivel")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay cuentas registradas", color="#475569"),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column(
                [
                    AppHeader.create("Plan de Cuentas", "Contabilidad básica"),
                    ft.Container(
                        content=ft.Row([tipo_filter], alignment=ft.MainAxisAlignment.START),
                        padding=20,
                    ),
                    body,
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
            app.page.update()

    tipo_filter.on_change = lambda e: asyncio.create_task(refresh())
    await refresh()


# ============ Balance de Comprobación ============


async def show_balance(app):
    """Display trial balance view."""
    C = app._get_colors()
    controller = app.controller

    async def refresh():
        try:
            balance = await controller.obtener_balance_comprobacion()
        except Exception:
            balance = []

        total_debito = sum(b.get("total_debito", 0) for b in balance)
        total_credito = sum(b.get("total_credito", 0) for b in balance)
        diferencia = total_debito - total_credito

        rows = []
        for b in balance:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(b.get("cuenta_codigo", "")))),
                        ft.DataCell(ft.Text(str(b.get("cuenta_nombre", "")))),
                        ft.DataCell(ft.Text(_fmt_money(b.get("total_debito", 0)))),
                        ft.DataCell(ft.Text(_fmt_money(b.get("total_credito", 0)))),
                    ]
                )
            )

        # Add totals row
        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text("TOTALES", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text(_fmt_money(total_debito), weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(_fmt_money(total_credito), weight=ft.FontWeight.BOLD)),
                ],
                color="#F1F5F9",
            )
        )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Cuenta")),
                ft.DataColumn(ft.Text("Nombre")),
                ft.DataColumn(ft.Text("Débitos")),
                ft.DataColumn(ft.Text("Créditos")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )

        balance_status = ft.Container(
            content=ft.Row([
                ft.Text("Diferencia:", weight=ft.FontWeight.BOLD),
                ft.Text(
                    _fmt_money(diferencia),
                    weight=ft.FontWeight.BOLD,
                    color=THEME_SUCCESS_COLOR if abs(diferencia) < 0.01 else THEME_ACCENT_COLOR,
                ),
            ], spacing=10),
            padding=16,
            bgcolor="#F8FAFC" if abs(diferencia) < 0.01 else "#FEE2E2",
            border_radius=8,
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay movimientos contables", color="#475569"),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column(
                [
                    AppHeader.create("Balance de Comprobación", "Resumen de cuentas"),
                    balance_status,
                    body,
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
            app.page.update()

    await refresh()
