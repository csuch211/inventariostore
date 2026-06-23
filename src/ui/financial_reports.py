"""Financial reports views.

Provides UI for P&L, balance sheet, cash flow, and financial dashboards.
"""

import asyncio
from datetime import datetime, timedelta

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


# ============ Dashboard Financiero ============


async def show_financial_dashboard(app):
    """Display financial dashboard with key metrics."""
    C = app._get_colors()
    controller = app.controller

    async def refresh():
        try:
            # Get trial balance for calculations
            balance = await controller.obtener_balance_comprobacion()

            # Calculate key metrics
            ingresos = sum(b.get("total_credito", 0) for b in balance
                          if b.get("cuenta_codigo", "").startswith("4"))
            gastos = sum(b.get("total_debito", 0) for b in balance
                         if b.get("cuenta_codigo", "").startswith("5"))
            utilidad_neta = ingresos - gastos

            activos = sum(b.get("total_debito", 0) for b in balance
                          if b.get("cuenta_codigo", "").startswith("1"))
            pasivos = sum(b.get("total_credito", 0) for b in balance
                          if b.get("cuenta_codigo", "").startswith("2"))
            patrimonio = activos - pasivos

            # Get sales stats
            try:
                stats = await controller.obtener_estadisticas_ventas()
                ventas_hoy = stats.get("ingresos_hoy", 0)
                ventas_mes = stats.get("ingresos_totales", 0)
            except Exception:
                ventas_hoy = 0
                ventas_mes = 0

        except Exception:
            ingresos = gastos = utilidad_neta = 0
            activos = pasivos = patrimonio = 0
            ventas_hoy = ventas_mes = 0

        # KPI Cards
        def kpi_card(title, value, icon, color, bg):
            return ft.Container(
                content=ft.Column([
                    ft.Icon(icon, color=color, size=24),
                    ft.Text(title, size=11, color="#475569"),
                    ft.Text(value, size=20, weight=ft.FontWeight.BOLD, color=color),
                ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=16,
                border_radius=10,
                bgcolor=bg,
                width=200,
                height=120,
            )

        cards_row1 = ft.Row([
            kpi_card("Ingresos", _fmt_money(ingresos), ft.icons.Icons.TRENDING_UP, THEME_SUCCESS_COLOR, "#DCFCE7"),
            kpi_card("Gastos", _fmt_money(gastos), ft.icons.Icons.TRENDING_DOWN, THEME_WARNING_COLOR, "#FEF3C7"),
            kpi_card("Utilidad Neta", _fmt_money(utilidad_neta),
                     ft.icons.Icons.ACCOUNT_BALANCE,
                     THEME_SUCCESS_COLOR if utilidad_neta >= 0 else THEME_ACCENT_COLOR,
                     "#DCFCE7" if utilidad_neta >= 0 else "#FEE2E2"),
        ], spacing=15, alignment=ft.MainAxisAlignment.CENTER)

        cards_row2 = ft.Row([
            kpi_card("Activos", _fmt_money(activos), ft.icons.Icons.LANDSCAPE, THEME_PRIMARY_COLOR, "#DBEAFE"),
            kpi_card("Pasivos", _fmt_money(pasivos), ft.icons.Icons.LANDSCAPE, THEME_WARNING_COLOR, "#FEF3C7"),
            kpi_card("Patrimonio", _fmt_money(patrimonio), ft.icons.Icons.ACCOUNT_BALANCE, THEME_SUCCESS_COLOR, "#DCFCE7"),
        ], spacing=15, alignment=ft.MainAxisAlignment.CENTER)

        cards_row3 = ft.Row([
            kpi_card("Ventas Hoy", _fmt_money(ventas_hoy), ft.icons.Icons.TODAY, THEME_SUCCESS_COLOR, "#DCFCE7"),
            kpi_card("Ventas Mes", _fmt_money(ventas_mes), ft.icons.Icons.CALENDAR_MONTH, THEME_PRIMARY_COLOR, "#DBEAFE"),
        ], spacing=15, alignment=ft.MainAxisAlignment.CENTER)

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Dashboard Financiero", "Resumen ejecutivo"),
                ft.Container(content=cards_row1, padding=20),
                ft.Container(content=cards_row2, padding=ft.Padding(left=20, right=20, top=0, bottom=10)),
                ft.Container(content=cards_row3, padding=ft.Padding(left=20, right=20, top=0, bottom=20)),
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    await refresh()


# ============ Estado de Resultados (P&L) ============


async def show_estado_resultados(app):
    """Display Profit & Loss statement."""
    C = app._get_colors()
    controller = app.controller

    async def refresh():
        try:
            balance = await controller.obtener_balance_comprobacion()
        except Exception:
            balance = []

        # Group by account type
        ingresos = [(b["cuenta_codigo"], b["cuenta_nombre"], b.get("total_credito", 0))
                    for b in balance if b.get("cuenta_codigo", "").startswith("4")]
        gastos = [(b["cuenta_codigo"], b["cuenta_nombre"], b.get("total_debito", 0))
                  for b in balance if b.get("cuenta_codigo", "").startswith("5")]

        total_ingresos = sum(v for _, _, v in ingresos)
        total_gastos = sum(v for _, _, v in gastos)
        utilidad = total_ingresos - total_gastos

        # Build rows
        ingresos_rows = []
        for codigo, nombre, monto in ingresos:
            ingresos_rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(codigo)),
                ft.DataCell(ft.Text(nombre)),
                ft.DataCell(ft.Text(_fmt_money(monto))),
            ]))

        gastos_rows = []
        for codigo, nombre, monto in gastos:
            gastos_rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(codigo)),
                ft.DataCell(ft.Text(nombre)),
                ft.DataCell(ft.Text(_fmt_money(monto))),
            ]))

        table_style = {
            "heading_row_color": "#DBEAFE",
        }

        content = ft.Column([
            ft.Text("Ingresos", size=16, weight=ft.FontWeight.BOLD, color=THEME_SUCCESS_COLOR),
            ft.DataTable(
                columns=[ft.DataColumn(ft.Text("Cuenta")), ft.DataColumn(ft.Text("Nombre")), ft.DataColumn(ft.Text("Monto"))],
                rows=ingresos_rows,
                **table_style,
            ) if ingresos_rows else ft.Text("Sin ingresos registrados", color="#475569"),
            ft.Row([
                ft.Text("Total Ingresos:", weight=ft.FontWeight.BOLD, size=14),
                ft.Text(_fmt_money(total_ingresos), weight=ft.FontWeight.BOLD, size=14, color=THEME_SUCCESS_COLOR),
            ]),
            ft.Divider(),
            ft.Text("Gastos", size=16, weight=ft.FontWeight.BOLD, color=THEME_WARNING_COLOR),
            ft.DataTable(
                columns=[ft.DataColumn(ft.Text("Cuenta")), ft.DataColumn(ft.Text("Nombre")), ft.DataColumn(ft.Text("Monto"))],
                rows=gastos_rows,
                **table_style,
            ) if gastos_rows else ft.Text("Sin gastos registrados", color="#475569"),
            ft.Row([
                ft.Text("Total Gastos:", weight=ft.FontWeight.BOLD, size=14),
                ft.Text(_fmt_money(total_gastos), weight=ft.FontWeight.BOLD, size=14, color=THEME_WARNING_COLOR),
            ]),
            ft.Divider(),
            ft.Row([
                ft.Text("Utilidad Neta:", weight=ft.FontWeight.BOLD, size=18),
                ft.Text(
                    _fmt_money(utilidad),
                    weight=ft.FontWeight.BOLD,
                    size=18,
                    color=THEME_SUCCESS_COLOR if utilidad >= 0 else THEME_ACCENT_COLOR,
                ),
            ]),
        ], spacing=10)

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Estado de Resultados", "P&L Statement"),
                ft.Container(content=content, padding=20),
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    await refresh()


# ============ Balance General ============


async def show_balance_general(app):
    """Display balance sheet."""
    C = app._get_colors()
    controller = app.controller

    async def refresh():
        try:
            balance = await controller.obtener_balance_comprobacion()
        except Exception:
            balance = []

        activos = [(b["cuenta_codigo"], b["cuenta_nombre"], b.get("total_debito", 0))
                   for b in balance if b.get("cuenta_codigo", "").startswith("1")]
        pasivos = [(b["cuenta_codigo"], b["cuenta_nombre"], b.get("total_credito", 0))
                   for b in balance if b.get("cuenta_codigo", "").startswith("2")]
        patrimonio = [(b["cuenta_codigo"], b["cuenta_nombre"], b.get("total_credito", 0))
                      for b in balance if b.get("cuenta_codigo", "").startswith("3")]

        total_activos = sum(v for _, _, v in activos)
        total_pasivos = sum(v for _, _, v in pasivos)
        total_patrimonio = sum(v for _, _, v in patrimonio)

        def build_section(title, items, total, color):
            rows = []
            for codigo, nombre, monto in items:
                rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(codigo)),
                    ft.DataCell(ft.Text(nombre)),
                    ft.DataCell(ft.Text(_fmt_money(monto))),
                ]))
            return ft.Column([
                ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=color),
                ft.DataTable(
                    columns=[ft.DataColumn(ft.Text("Cuenta")), ft.DataColumn(ft.Text("Nombre")), ft.DataColumn(ft.Text("Monto"))],
                    rows=rows,
                    heading_row_color="#DBEAFE",
                ) if rows else ft.Text(f"Sin {title.lower()} registrados", color="#475569"),
                ft.Row([
                    ft.Text(f"Total {title}:", weight=ft.FontWeight.BOLD),
                    ft.Text(_fmt_money(total), weight=ft.FontWeight.BOLD, color=color),
                ]),
            ], spacing=8)

        content = ft.Column([
            build_section("Activos", activos, total_activos, THEME_PRIMARY_COLOR),
            ft.Divider(),
            build_section("Pasivos", pasivos, total_pasivos, THEME_WARNING_COLOR),
            ft.Divider(),
            build_section("Patrimonio", patrimonio, total_patrimonio, THEME_SUCCESS_COLOR),
            ft.Divider(),
            ft.Row([
                ft.Text("Ecuación Contable:", weight=ft.FontWeight.BOLD, size=14),
                ft.Text(f"Activos ({_fmt_money(total_activos)}) = "
                       f"Pasivos ({_fmt_money(total_pasivos)}) + "
                       f"Patrimonio ({_fmt_money(total_patrimonio)})",
                       size=12),
            ]),
        ], spacing=15)

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Balance General", "Balance sheet"),
                ft.Container(content=content, padding=20),
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    await refresh()
