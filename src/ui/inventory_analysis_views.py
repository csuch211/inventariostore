"""Inventory views for comprehensive inventory management.

Provides UI for stock analysis, ABC analysis, turnover, aging, and valuation.
"""

import asyncio

import flet as ft

from config.settings import THEME_PRIMARY_COLOR, THEME_SUCCESS_COLOR, THEME_WARNING_COLOR, THEME_ACCENT_COLOR
from services.inventory_report_export import InventoryReportExporter
from ui.components import AppHeader, SnackBarHelper
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _fmt_money(v) -> str:
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "$0.00"


# ============ Análisis ABC ============


async def show_abc_analysis(app):
    """Display ABC analysis view."""
    C = app._get_colors()
    controller = app.controller

    async def refresh():
        try:
            productos = await controller.analisis_abc()
        except Exception:
            productos = []

        # Summary cards
        total_a = len([p for p in productos if p.get("abc_class") == "A"])
        total_b = len([p for p in productos if p.get("abc_class") == "B"])
        total_c = len([p for p in productos if p.get("abc_class") == "C"])

        summary_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("Clase A", size=12, color="white"),
                    ft.Text(str(total_a), size=24, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("Alto valor", size=10, color="white"),
                ], spacing=4),
                padding=16, bgcolor=THEME_PRIMARY_COLOR, border_radius=8, width=150,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Clase B", size=12, color="white"),
                    ft.Text(str(total_b), size=24, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("Valor medio", size=10, color="white"),
                ], spacing=4),
                padding=16, bgcolor=THEME_WARNING_COLOR, border_radius=8, width=150,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Clase C", size=12, color="white"),
                    ft.Text(str(total_c), size=24, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("Bajo valor", size=10, color="white"),
                ], spacing=4),
                padding=16, bgcolor="#6B7280", border_radius=8, width=150,
            ),
        ], spacing=15)

        # Table
        rows = []
        for p in productos[:50]:  # Limit to top 50
            abc_color = {
                "A": THEME_PRIMARY_COLOR,
                "B": THEME_WARNING_COLOR,
                "C": "#6B7280",
            }.get(p.get("abc_class", ""), "#6B7280")

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(p.get("codigo", "")))),
                        ft.DataCell(ft.Text(str(p.get("nombre", ""))[:30])),
                        ft.DataCell(ft.Text(str(p.get("cantidad", 0)))),
                        ft.DataCell(ft.Text(_fmt_money(p.get("precio", 0)))),
                        ft.DataCell(ft.Text(_fmt_money(p.get("_revenue", 0)))),
                        ft.DataCell(ft.Text(p.get("abc_class", ""), color=abc_color, weight=ft.FontWeight.BOLD)),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Código")),
                ft.DataColumn(ft.Text("Producto")),
                ft.DataColumn(ft.Text("Stock")),
                ft.DataColumn(ft.Text("Precio")),
                ft.DataColumn(ft.Text("Ingresos")),
                ft.DataColumn(ft.Text("Clase")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay productos para analizar", color="#475569"),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Análisis ABC", "Clasificación por valor de ingresos"),
                ft.Container(content=summary_row, padding=20),
                ft.Container(
                    content=ft.Row([export_btn], alignment=ft.MainAxisAlignment.END),
                    padding=20,
                ),
                body,
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    async def export_pdf():
        try:
            productos = await controller.analisis_abc()
            exporter = InventoryReportExporter()
            path = exporter.export_abc_analysis(productos)
            SnackBarHelper.success(app.page, f"PDF exportado: {path.name}")
        except Exception as ex:
            SnackBarHelper.error(app.page, f"Error exportando: {ex}")

    export_btn = ft.Button(
        content=ft.Row([
            ft.Icon(ft.icons.Icons.PICTURE_AS_PDF, color="white"),
            ft.Text("Exportar PDF", color="white"),
        ], spacing=5),
        on_click=lambda e: asyncio.create_task(export_pdf()),
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    await refresh()


# ============ Rotación de Inventario ============


async def show_inventory_turnover(app):
    """Display inventory turnover analysis."""
    C = app._get_colors()
    controller = app.controller

    async def refresh():
        try:
            turnover = await controller.calcular_rotacion()
        except Exception:
            turnover = {}

        turnover_ratio = turnover.get("turnover_ratio", 0)
        days_of_supply = turnover.get("days_of_supply", 0)
        risk = turnover.get("stockout_risk", "low")
        total_stock = turnover.get("total_stock", 0)
        total_value = turnover.get("total_value", 0)

        risk_color = {
            "high": THEME_ACCENT_COLOR,
            "medium": THEME_WARNING_COLOR,
            "low": THEME_SUCCESS_COLOR,
        }.get(risk, "#6B7280")

        risk_bg = {
            "high": "#FEE2E2",
            "medium": "#FEF3C7",
            "low": "#DCFCE7",
        }.get(risk, "#F3F4F6")

        def kpi_card(title, value, icon, color, bg):
            return ft.Container(
                content=ft.Column([
                    ft.Icon(icon, color=color, size=24),
                    ft.Text(title, size=11, color="#475569"),
                    ft.Text(value, size=20, weight=ft.FontWeight.BOLD, color=color),
                ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=16, border_radius=10, bgcolor=bg, width=200, height=120,
            )

        cards = ft.Row([
            kpi_card("Ratio Rotación", f"{turnover_ratio:.2f}", ft.icons.Icons.REFRESH, THEME_PRIMARY_COLOR, "#DBEAFE"),
            kpi_card("Días de Stock", f"{days_of_supply:.0f}", ft.icons.Icons.CALENDAR_TODAY, THEME_WARNING_COLOR, "#FEF3C7"),
            kpi_card("Riesgo Agotamiento", risk.upper(), ft.icons.Icons.WARNING, risk_color, risk_bg),
            kpi_card("Valor Inventario", _fmt_money(total_value), ft.icons.Icons.ATTACH_MONEY, THEME_SUCCESS_COLOR, "#DCFCE7"),
        ], spacing=15, alignment=ft.MainAxisAlignment.CENTER)

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Rotación de Inventario", "Análisis de eficiencia"),
                ft.Container(content=cards, padding=20),
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    await refresh()


# ============ Análisis de Envejecimiento ============


async def show_inventory_aging(app):
    """Display inventory aging analysis."""
    C = app._get_colors()
    controller = app.controller

    async def refresh():
        try:
            productos = await controller.analisis_envejecimiento()
        except Exception:
            productos = []

        # Summary
        fresh = len([p for p in productos if p.get("aging_class") == "fresh"])
        aging = len([p for p in productos if p.get("aging_class") == "aging"])
        old = len([p for p in productos if p.get("aging_class") == "old"])
        stagnant = len([p for p in productos if p.get("aging_class") == "stagnant"])

        summary_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("Reciente", size=12, color="white"),
                    ft.Text(str(fresh), size=24, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("≤30 días", size=10, color="white"),
                ], spacing=4),
                padding=16, bgcolor=THEME_SUCCESS_COLOR, border_radius=8, width=150,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Envejeciendo", size=12, color="white"),
                    ft.Text(str(aging), size=24, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("30-90 días", size=10, color="white"),
                ], spacing=4),
                padding=16, bgcolor=THEME_WARNING_COLOR, border_radius=8, width=150,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Antiguo", size=12, color="white"),
                    ft.Text(str(old), size=24, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text(">90 días", size=10, color="white"),
                ], spacing=4),
                padding=16, bgcolor=THEME_ACCENT_COLOR, border_radius=8, width=150,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Estancado", size=12, color="white"),
                    ft.Text(str(stagnant), size=24, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("Sin movimiento", size=10, color="white"),
                ], spacing=4),
                padding=16, bgcolor="#6B7280", border_radius=8, width=150,
            ),
        ], spacing=15)

        # Table
        rows = []
        aging_colors = {
            "fresh": THEME_SUCCESS_COLOR,
            "aging": THEME_WARNING_COLOR,
            "old": THEME_ACCENT_COLOR,
            "stagnant": "#6B7280",
        }
        aging_labels = {
            "fresh": "Reciente",
            "aging": "Envejeciendo",
            "old": "Antiguo",
            "stagnant": "Estancado",
        }

        for p in productos[:50]:
            aging_class = p.get("aging_class", "stagnant")
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(p.get("codigo", "")))),
                        ft.DataCell(ft.Text(str(p.get("nombre", ""))[:30])),
                        ft.DataCell(ft.Text(str(p.get("cantidad", 0)))),
                        ft.DataCell(ft.Text(aging_labels.get(aging_class, aging_class),
                                            color=aging_colors.get(aging_class, "#6B7280"))),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Código")),
                ft.DataColumn(ft.Text("Producto")),
                ft.DataColumn(ft.Text("Stock")),
                ft.DataColumn(ft.Text("Clase")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay productos para analizar", color="#475569"),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Análisis de Envejecimiento", "Antigüedad del inventario"),
                ft.Container(content=summary_row, padding=20),
                body,
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    await refresh()


# ============ Riesgo de Agotamiento ============


async def show_stockout_risk(app):
    """Display stockout risk analysis."""
    C = app._get_colors()
    controller = app.controller

    async def refresh():
        try:
            productos = await controller.riesgo_agotamiento()
        except Exception:
            productos = []

        # Summary
        critical = len([p for p in productos if p.get("risk_level") == "critical"])
        high = len([p for p in productos if p.get("risk_level") == "high"])
        medium = len([p for p in productos if p.get("risk_level") == "medium"])

        summary_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("Crítico", size=12, color="white"),
                    ft.Text(str(critical), size=24, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("Sin stock", size=10, color="white"),
                ], spacing=4),
                padding=16, bgcolor=THEME_ACCENT_COLOR, border_radius=8, width=150,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Alto", size=12, color="white"),
                    ft.Text(str(high), size=24, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("Debajo mínimo", size=10, color="white"),
                ], spacing=4),
                padding=16, bgcolor=THEME_WARNING_COLOR, border_radius=8, width=150,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Medio", size=12, color="white"),
                    ft.Text(str(medium), size=24, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("<14 días", size=10, color="white"),
                ], spacing=4),
                padding=16, bgcolor="#F59E0B", border_radius=8, width=150,
            ),
        ], spacing=15)

        # Table (only show at-risk products)
        at_risk = [p for p in productos if p.get("risk_level") in ("critical", "high", "medium")]
        rows = []
        risk_colors = {
            "critical": THEME_ACCENT_COLOR,
            "high": THEME_WARNING_COLOR,
            "medium": "#F59E0B",
        }

        for p in at_risk[:30]:
            risk_level = p.get("risk_level", "low")
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(p.get("codigo", "")))),
                        ft.DataCell(ft.Text(str(p.get("nombre", ""))[:30])),
                        ft.DataCell(ft.Text(str(p.get("cantidad", 0)))),
                        ft.DataCell(ft.Text(str(p.get("stock_min", 0)))),
                        ft.DataCell(ft.Text(f"{p.get('days_until_stockout', 0):.0f} días")),
                        ft.DataCell(ft.Text(risk_level.upper(),
                                            color=risk_colors.get(risk_level, "#6B7280"),
                                            weight=ft.FontWeight.BOLD)),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Código")),
                ft.DataColumn(ft.Text("Producto")),
                ft.DataColumn(ft.Text("Stock")),
                ft.DataColumn(ft.Text("Mínimo")),
                ft.DataColumn(ft.Text("Días Restantes")),
                ft.DataColumn(ft.Text("Riesgo")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay productos en riesgo de agotamiento", color="#475569"),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Riesgo de Agotamiento", "Productos que requieren atención"),
                ft.Container(content=summary_row, padding=20),
                body,
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    await refresh()
