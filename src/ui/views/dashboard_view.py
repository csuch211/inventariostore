"""
Unified inventory dashboard view.

Extracted from app_view._show_dashboard as a standalone async function.
"""

import asyncio

import flet as ft

from config.settings import (
    THEME_ACCENT_COLOR,
    THEME_ACCENT_LIGHT,
    THEME_PRIMARY_COLOR,
    THEME_PRIMARY_LIGHT,
    THEME_SUCCESS_COLOR,
    THEME_SUCCESS_LIGHT,
    THEME_WARNING_COLOR,
    THEME_WARNING_LIGHT,
)
from core.theme_manager import theme_manager
from ui._utils import _fmt_money
from ui.charts import BarChart as TopProductsChart
from ui.charts import LineChart as ValorInventarioChart
from ui.charts import PieChart as DistributionChart
from ui.components import AppHeader, LoadingSpinner, SnackBarHelper
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _kpi_card(
    title: str,
    value: str,
    color: str,
    light_color: str,
    icon,
    colors: dict,
    col_size: int = 3,
) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(icon, color=color, size=22),
                            bgcolor=light_color,
                            padding=10,
                            border_radius=8,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    title,
                                    size=11,
                                    color=colors["text_muted"],
                                    weight=ft.FontWeight.W_500,
                                ),
                                ft.Text(
                                    value,
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                    color=color,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                        ),
                    ],
                    spacing=12,
                ),
            ]
        ),
        col={"sm": 6, "md": col_size, "xl": col_size},
        padding=16,
        bgcolor=colors["surface"],
        border_radius=12,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=4, color=colors["shadow"]),
    )


async def show_dashboard(app):
    """Display the unified inventory home/dashboard.

    Single source of truth for KPIs: ``obtener_kpis_dashboard`` aggregates
    all metrics in one DB round-trip, then charts are fetched concurrently.
    Previously this view rendered two overlapping KPI sections (basic stats
    cards + a separate "Executive Dashboard" block) and called four
    additional controllers sequentially; both issues are resolved here.
    """
    loading_container = LoadingSpinner.create()
    if app.main_view:
        app.main_view.content = loading_container
        app.page.update()

    palette = theme_manager.palette(page=app.page)
    try:

        async def _charts():
            return await asyncio.gather(
                app.controller.obtener_top_productos_stock(limit=10),
                app.controller.obtener_distribucion_categorias(),
                app.controller.obtener_serie_inventario(dias=30),
                app.controller.obtener_todos_productos(),
            )

        kpis_task = asyncio.create_task(app.controller.obtener_kpis_dashboard())
        charts_task = asyncio.create_task(_charts())
        kpis = await kpis_task
        top_productos, distribucion, serie, products = await charts_task

        total_productos = int(kpis.get("total_productos", 0))
        unidades_totales = int(kpis.get("unidades_totales", 0))
        valor_venta = float(kpis.get("valor_inventario_venta", 0))
        valor_costo = float(kpis.get("valor_inventario_costo", 0))
        margen = float(kpis.get("margen_estimado", 0))
        criticos = int(kpis.get("productos_criticos", 0))
        agotados = int(kpis.get("productos_agotados", 0))
        ventas_hoy_count = int(kpis.get("ventas_hoy_count", 0))
        ventas_hoy_total = float(kpis.get("ventas_hoy_total", 0))
        ventas_mes_count = int(kpis.get("ventas_mes_count", 0))
        ventas_mes_total = float(kpis.get("ventas_mes_total", 0))
        top_mes = kpis.get("top_productos_mes", []) or []

        # Row 1: inventory headcount + value + risk (4 cards)
        cards_row1 = [
            _kpi_card(
                t("dashboard.total_products"),
                str(total_productos),
                THEME_PRIMARY_COLOR,
                THEME_PRIMARY_LIGHT,
                ft.icons.Icons.INVENTORY_2,
                palette,
            ),
            _kpi_card(
                "Unidades",
                str(unidades_totales),
                palette["info"],
                palette["info_light"],
                ft.icons.Icons.STORAGE,
                palette,
            ),
            _kpi_card(
                t("phase1.dashboard.valor_venta"),
                _fmt_money(valor_venta),
                THEME_SUCCESS_COLOR,
                THEME_SUCCESS_LIGHT,
                ft.icons.Icons.ATTACH_MONEY,
                palette,
            ),
            _kpi_card(
                t("phase1.dashboard.valor_costo"),
                _fmt_money(valor_costo),
                palette["purple"],
                palette["purple_light"],
                ft.icons.Icons.PAID,
                palette,
            ),
        ]
        # Row 2: risk + sales (5 cards). Margen spans 1 col on its own.
        cards_row2 = [
            _kpi_card(
                t("phase1.dashboard.criticos"),
                str(criticos),
                THEME_WARNING_COLOR,
                THEME_WARNING_LIGHT,
                ft.icons.Icons.WARNING_AMBER,
                palette,
            ),
            _kpi_card(
                t("phase1.dashboard.agotados"),
                str(agotados),
                THEME_ACCENT_COLOR,
                THEME_ACCENT_LIGHT,
                ft.icons.Icons.ERROR,
                palette,
            ),
            _kpi_card(
                t("phase1.dashboard.margen"),
                _fmt_money(margen),
                palette["teal"],
                palette["teal_light"],
                ft.icons.Icons.TRENDING_UP,
                palette,
            ),
            _kpi_card(
                "Ventas hoy",
                f"{ventas_hoy_count} · {_fmt_money(ventas_hoy_total)}",
                palette["success"],
                THEME_SUCCESS_LIGHT,
                ft.icons.Icons.TODAY,
                palette,
            ),
            _kpi_card(
                "Ventas mes",
                f"{ventas_mes_count} · {_fmt_money(ventas_mes_total)}",
                palette["primary"],
                THEME_PRIMARY_LIGHT,
                ft.icons.Icons.CALENDAR_MONTH,
                palette,
            ),
        ]

        # Recent products (newest first)
        recent_products = sorted(
            products,
            key=lambda x: x.get("creado_en", x.get("fecha_creacion", "")),
            reverse=True,
        )[:5]
        recent_table_rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(p.get("codigo", "")))),
                    ft.DataCell(ft.Text(str(p.get("nombre", ""))[:30])),
                    ft.DataCell(ft.Text(str(p.get("cantidad", 0)))),
                    ft.DataCell(ft.Text(f"${p.get('precio', 0):.2f}")),
                ]
            )
            for p in recent_products
        ]
        recent_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(t("products.code"))),
                ft.DataColumn(ft.Text(t("products.name"))),
                ft.DataColumn(ft.Text(t("products.quantity"))),
                ft.DataColumn(ft.Text(t("products.price"))),
            ],
            rows=recent_table_rows,
            border=ft.border.Border(
                ft.BorderSide(1, palette["divider"]),
                ft.BorderSide(1, palette["divider"]),
                ft.BorderSide(1, palette["divider"]),
                ft.BorderSide(1, palette["divider"]),
            ),
            heading_row_color=palette["table_heading"],
            data_row_color=palette["table_row"],
            horizontal_lines=ft.BorderSide(0.1, palette["divider"]),
            vertical_lines=ft.BorderSide(0.1, palette["divider"]),
        )

        # Build charts (flet-charts wrappers from ui/charts.py)
        bar_chart = TopProductsChart.build(
            top_productos,
            title=t("dashboard.chart.top_products"),
            value_label=t("products.quantity"),
            empty_message=t("products.empty"),
            colors=palette,
        )
        pie_chart = DistributionChart.build(
            distribucion,
            title=t("dashboard.chart.by_category"),
            empty_message=t("products.empty"),
            colors=palette,
        )
        line_chart = ValorInventarioChart.build(
            serie,
            title=t("dashboard.chart.value_30d"),
            value_label="$",
            empty_message=t("products.empty"),
            colors=palette,
        )

        # Top-products-of-the-month table
        top_mes_rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(it.get("codigo", "")))),
                    ft.DataCell(ft.Text(str(it.get("nombre", "")))),
                    ft.DataCell(ft.Text(str(it.get("unidades", 0)))),
                    ft.DataCell(ft.Text(_fmt_money(float(it.get("ingresos", 0) or 0)))),
                ]
            )
            for it in top_mes
        ]
        top_mes_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(t("products.code"))),
                ft.DataColumn(ft.Text(t("phase1.devoluciones.producto"))),
                ft.DataColumn(ft.Text("Unidades")),
                ft.DataColumn(ft.Text("Ingresos")),
            ],
            rows=top_mes_rows,
            heading_row_color=palette["table_heading"],
            horizontal_lines=ft.BorderSide(0.1, palette["divider"]),
            vertical_lines=ft.BorderSide(0.1, palette["divider"]),
        )

        content = ft.Column(
            [
                AppHeader.create(t("dashboard.title"), t("dashboard.subtitle")),
                ft.Container(
                    content=ft.ResponsiveRow(
                        controls=cards_row1,
                        columns=12,
                        spacing=15,
                        run_spacing=15,
                    ),
                    padding=20,
                ),
                ft.Container(
                    content=ft.ResponsiveRow(
                        controls=cards_row2,
                        columns=12,
                        spacing=15,
                        run_spacing=15,
                    ),
                    padding=ft.Padding(left=20, right=20, top=0, bottom=10),
                ),
                ft.Container(
                    content=ft.ResponsiveRow(
                        controls=[
                            ft.Container(
                                content=bar_chart,
                                col={"sm": 12, "md": 12, "lg": 6},
                                padding=10,
                            ),
                            ft.Container(
                                content=pie_chart,
                                col={"sm": 12, "md": 12, "lg": 6},
                                padding=10,
                            ),
                        ],
                        columns=12,
                        spacing=10,
                        run_spacing=10,
                    ),
                    padding=ft.Padding(left=10, right=10, top=0, bottom=10),
                ),
                ft.Container(
                    content=ft.Row(
                        [line_chart],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding(left=10, right=10, top=0, bottom=10),
                ),
                ft.Container(
                    content=ft.ResponsiveRow(
                        controls=[
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text(
                                            "Productos Recientes",
                                            size=16,
                                            weight=ft.FontWeight.BOLD,
                                            color=palette["primary"],
                                        ),
                                        recent_table,
                                    ],
                                    spacing=15,
                                ),
                                col={"sm": 12, "lg": 6},
                                padding=20,
                                bgcolor=palette["surface"],
                                border_radius=10,
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text(
                                            t("phase1.dashboard.top_mes"),
                                            size=16,
                                            weight=ft.FontWeight.BOLD,
                                            color=palette["primary"],
                                        ),
                                        top_mes_table,
                                    ],
                                    spacing=15,
                                ),
                                col={"sm": 12, "lg": 6},
                                padding=20,
                                bgcolor=palette["surface"],
                                border_radius=10,
                            ),
                        ],
                        columns=12,
                        spacing=15,
                        run_spacing=15,
                    ),
                    padding=ft.Padding(left=20, right=20, top=0, bottom=20),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        if app.main_view:
            app.main_view.content = content
            app.page.update()

    except Exception as e:
        logger.exception(f"dashboard: render failed: {e}")
        SnackBarHelper.error(app.page, "Error al cargar el dashboard.")
