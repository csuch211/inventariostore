"""
Chart wrappers around flet-charts.

Provides three ready-to-use chart controls that consume the dict shapes
already exposed by InventarioController:

- BarChart.build(obtener_top_productos_stock() -> [{nombre, cantidad}])
- PieChart.build(obtener_distribucion_categorias() -> [{nombre, total}])
- LineChart.build(obtener_serie_inventario() -> [{fecha, valor}])

Each wrapper handles:
- Color palette (deterministic per index)
- Axis labels (truncated long names)
- Sensible height (~250 px) and aspect_ratio for responsive layout
- Empty-state placeholder
"""

import flet as ft

# NOTE: flet_charts 0.85.x exposes the chart classes under their own submodules.
# The top-level `flet_charts.BarChart` is a proxy that does NOT accept constructor
# args, so we import from the actual modules.
from flet_charts.bar_chart import BarChart as _BarChart
from flet_charts.bar_chart_group import BarChartGroup as _BarChartGroup
from flet_charts.bar_chart_rod import BarChartRod as _BarChartRod
from flet_charts.chart_axis import ChartAxis, ChartAxisLabel
from flet_charts.line_chart import LineChart as _LineChart
from flet_charts.line_chart_data import LineChartData as _LineChartData
from flet_charts.line_chart_data_point import LineChartDataPoint as _LineChartDataPoint
from flet_charts.pie_chart import PieChart as _PieChart
from flet_charts.pie_chart_section import PieChartSection as _PieChartSection

# Default chart height in pixels
CHART_HEIGHT = 250

# Color palette - sequential, accessible
PALETTE = [
    "#1976D2",  # primary blue
    "#388E3C",  # green
    "#F57C00",  # orange
    "#7B1FA2",  # purple
    "#C2185B",  # pink
    "#0097A7",  # teal
    "#FBC02D",  # yellow
    "#5D4037",  # brown
    "#455A64",  # blue-grey
    "#D32F2F",  # red
]


def _color_for(index: int) -> str:
    return PALETTE[index % len(PALETTE)]


def _empty_state(message: str, colors: dict | None = None) -> ft.Container:
    surface = (colors or {}).get("surface", "white")
    text_muted = (colors or {}).get("text_muted", "gray600")
    icon_color = (colors or {}).get("text_muted", "gray400")
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.icons.Icons.BAR_CHART, size=40, color=icon_color),
                ft.Text(message, size=12, color=text_muted),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        height=CHART_HEIGHT,
        # Flet 0.85: ft.alignment is a module, not a shortcut. Use the enum.
        alignment=ft.alignment.Alignment.CENTER,
        bgcolor=surface,
        border_radius=10,
    )


def _truncate(text: str, max_len: int = 10) -> str:
    text = str(text)
    return text if len(text) <= max_len else text[: max_len - 1] + "\u2026"


class BarChart:
    """Horizontal-bar-style chart for top products by stock."""

    @staticmethod
    def build(
        data: list[dict],
        title: str | None = None,
        value_label: str = "Stock",
        empty_message: str = "Sin datos",
        colors: dict | None = None,
    ) -> ft.Container:
        if not data:
            return _empty_state(empty_message, colors)

        surface = (colors or {}).get("surface", "white")
        shadow = (colors or {}).get("shadow", "rgba(0,0,0,0.05)")
        (colors or {}).get("text_secondary", "gray700")

        max_value = max((int(d.get("cantidad", 0)) for d in data), default=0) or 1

        groups = []
        bottom_labels = []
        for idx, item in enumerate(data):
            cantidad = int(item.get("cantidad", 0))
            rod = _BarChartRod(
                from_y=0,
                to_y=cantidad,
                width=24,
                color=_color_for(idx),
                border_radius=4,
                tooltip=f"{item.get('nombre', '')}: {cantidad}",
            )
            groups.append(_BarChartGroup(x=idx, rods=[rod]))
            bottom_labels.append(
                ChartAxisLabel(value=idx, label=_truncate(item.get("nombre", ""), 8))
            )

        left_axis = ChartAxis(
            title=value_label,
            title_size=11,
            label_size=10,
            show_labels=True,
            show_min=False,
        )
        bottom_axis = ChartAxis(
            title="",
            show_labels=True,
            label_size=10,
            labels=bottom_labels,
            show_min=False,
            show_max=False,
        )

        chart = _BarChart(
            groups=groups,
            left_axis=left_axis,
            bottom_axis=bottom_axis,
            height=CHART_HEIGHT,
            max_y=max_value * 1.15,
            interactive=True,
        )

        body: list[ft.Control] = [chart]
        if title:
            title_color = (colors or {}).get("text_primary", "black")
            body.insert(
                0,
                ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=title_color),
            )
        return ft.Container(
            content=ft.Column(body, spacing=8, tight=True),
            padding=15,
            bgcolor=surface,
            border_radius=10,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=3, color=shadow),
        )


class PieChart:
    """Donut/pie chart for distribution by category."""

    @staticmethod
    def build(
        data: list[dict],
        title: str | None = None,
        value_label: str = "total",
        empty_message: str = "Sin datos",
        colors: dict | None = None,
    ) -> ft.Container:
        if not data:
            return _empty_state(empty_message, colors)

        surface = (colors or {}).get("surface", "white")
        shadow = (colors or {}).get("shadow", "rgba(0,0,0,0.05)")
        text_secondary = (colors or {}).get("text_secondary", "gray700")
        text_primary = (colors or {}).get("text_primary", "black")

        total = sum(int(d.get("total", 0)) for d in data) or 1
        sections = []
        legend_rows = []
        for idx, item in enumerate(data):
            value = int(item.get("total", 0))
            pct = (value / total) * 100
            color = _color_for(idx)
            sections.append(
                _PieChartSection(
                    value=value,
                    color=color,
                    radius=80,
                    title=f"{pct:.0f}%" if pct >= 5 else None,
                    title_style=ft.TextStyle(size=11, color="white", weight=ft.FontWeight.BOLD),
                )
            )
            legend_rows.append(
                ft.Row(
                    [
                        ft.Container(width=12, height=12, bgcolor=color, border_radius=2),
                        ft.Text(
                            f"{_truncate(item.get('nombre', ''), 14)}: {value}",
                            size=11,
                            color=text_secondary,
                        ),
                    ],
                    spacing=5,
                )
            )

        chart = _PieChart(
            sections=sections,
            height=CHART_HEIGHT,
            sections_space=2,
            center_space_radius=30,
        )

        body: list[ft.Control] = [
            ft.Row(
                [chart, ft.Column(legend_rows, spacing=4, tight=True)],
                spacing=15,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        ]
        if title:
            body.insert(
                0,
                ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=text_primary),
            )
        return ft.Container(
            content=ft.Column(body, spacing=10, tight=True),
            padding=15,
            bgcolor=surface,
            border_radius=10,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=3, color=shadow),
        )


class LineChart:
    """Time-series chart (e.g. inventory value over time)."""

    @staticmethod
    def build(
        data: list[dict],
        title: str | None = None,
        value_label: str = "Valor",
        empty_message: str = "Sin datos",
        colors: dict | None = None,
    ) -> ft.Container:
        if not data:
            return _empty_state(empty_message, colors)

        surface = (colors or {}).get("surface", "white")
        shadow = (colors or {}).get("shadow", "rgba(0,0,0,0.05)")
        text_primary = (colors or {}).get("text_primary", "black")

        points = [
            _LineChartDataPoint(x=idx, y=float(item.get("valor", 0)))
            for idx, item in enumerate(data)
        ]
        label_stride = max(1, len(data) // 7)
        bottom_labels = [
            ChartAxisLabel(
                value=idx,
                label=_truncate(item.get("fecha", "")[5:], 7),
            )
            for idx, item in enumerate(data)
            if idx % label_stride == 0 or idx == len(data) - 1
        ]

        series = _LineChartData(
            points=points,
            color=PALETTE[0],
            curved=True,
            stroke_width=2.5,
            below_line=ft.BoxShadow(
                spread_radius=0, blur_radius=4, color="#1976D230", offset=ft.Offset(0, 2)
            ),
        )

        left_axis = ChartAxis(
            title=value_label,
            title_size=11,
            label_size=10,
            show_labels=True,
            show_min=False,
        )
        bottom_axis = ChartAxis(
            title="",
            show_labels=True,
            label_size=9,
            labels=bottom_labels,
            show_min=False,
            show_max=False,
        )

        chart = _LineChart(
            data_series=[series],
            left_axis=left_axis,
            bottom_axis=bottom_axis,
            height=CHART_HEIGHT,
            min_x=0,
            max_x=len(data) - 1,
            interactive=True,
        )

        body: list[ft.Control] = [chart]
        if title:
            body.insert(
                0,
                ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=text_primary),
            )
        return ft.Container(
            content=ft.Column(body, spacing=8, tight=True),
            padding=15,
            bgcolor=surface,
            border_radius=10,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=3, color=shadow),
        )
