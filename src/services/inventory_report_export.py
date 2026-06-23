"""Inventory report PDF exporter.

Generates PDF reports for ABC analysis, turnover, and aging.
"""

from datetime import datetime
from pathlib import Path

from utils.exceptions import InventarioException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class InventoryReportExporter:
    """Export inventory reports to PDF."""

    def __init__(self, export_dir: Path | None = None):
        self.export_dir = export_dir or Path("./exports")
        self.export_dir.mkdir(exist_ok=True)

    def _fmt_money(self, v) -> str:
        try:
            return f"${float(v):,.2f}"
        except Exception:
            return "$0.00"

    def export_abc_analysis(
        self,
        productos: list[dict],
        filename: str | None = None,
    ) -> Path:
        """Export ABC analysis to PDF."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

            if not filename:
                filename = f"analisis_abc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            filepath = self.export_dir / filename

            doc = SimpleDocTemplate(str(filepath), pagesize=letter,
                                    rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []

            elements.append(Spacer(1, 0.5 * inch))

            # Summary
            total_a = len([p for p in productos if p.get("abc_class") == "A"])
            total_b = len([p for p in productos if p.get("abc_class") == "B"])
            total_c = len([p for p in productos if p.get("abc_class") == "C"])

            summary_data = [
                ["CLASE", "CANTIDAD", "DESCRIPCIÓN"],
                ["A", str(total_a), "Alto valor (80% ingresos)"],
                ["B", str(total_b), "Valor medio (15% ingresos)"],
                ["C", str(total_c), "Bajo valor (5% ingresos)"],
            ]
            summary_table = Table(summary_data, colWidths=[1.5 * inch, 1.5 * inch, 3 * inch])
            summary_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 0.3 * inch))

            # Top products table
            if productos:
                data = [["CÓDIGO", "PRODUCTO", "STOCK", "PRECIO", "CLASE"]]
                for p in productos[:20]:
                    data.append([
                        str(p.get("codigo", "")),
                        str(p.get("nombre", ""))[:25],
                        str(p.get("cantidad", 0)),
                        self._fmt_money(p.get("precio", 0)),
                        str(p.get("abc_class", "")),
                    ])

                table = Table(data, colWidths=[1.2 * inch, 2 * inch, 1 * inch, 1.2 * inch, 1 * inch])
                table.setStyle(TableStyle([
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ]))
                elements.append(table)

            # Footer
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(_make_footer(f"Análisis ABC - {datetime.now().strftime('%Y-%m-%d %H:%M')}"))

            doc.build(elements)
            logger.info("ABC analysis exported: %s", filepath)
            return filepath
        except Exception as e:
            logger.error("Error exporting ABC analysis: %s", e)
            raise InventarioException(f"Export failed: {e}")

    def export_turnover(
        self,
        turnover_data: dict,
        filename: str | None = None,
    ) -> Path:
        """Export turnover analysis to PDF."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

            if not filename:
                filename = f"rotacion_inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            filepath = self.export_dir / filename

            doc = SimpleDocTemplate(str(filepath), pagesize=letter,
                                    rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []

            elements.append(Spacer(1, 0.5 * inch))

            # KPIs table
            kpi_data = [
                ["MÉTRICA", "VALOR"],
                ["Ratio de Rotación", f"{turnover_data.get('turnover_ratio', 0):.2f}"],
                ["Días de Stock", f"{turnover_data.get('days_of_supply', 0):.0f}"],
                ["Riesgo de Agotamiento", turnover_data.get('stockout_risk', 'N/A').upper()],
                ["Stock Total", str(turnover_data.get('total_stock', 0))],
                ["Valor Total", self._fmt_money(turnover_data.get('total_value', 0))],
                ["COGS", self._fmt_money(turnover_data.get('cogs', 0))],
            ]
            kpi_table = Table(kpi_data, colWidths=[3 * inch, 2 * inch])
            kpi_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(kpi_table)

            # Footer
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(_make_footer(f"Rotación de Inventario - {datetime.now().strftime('%Y-%m-%d %H:%M')}"))

            doc.build(elements)
            logger.info("Turnover report exported: %s", filepath)
            return filepath
        except Exception as e:
            logger.error("Error exporting turnover report: %s", e)
            raise InventarioException(f"Export failed: {e}")


def _make_footer(text: str):
    """Create a footer for reports."""
    from reportlab.lib.units import inch
    from reportlab.platypus import Table, TableStyle

    footer_data = [[text]]
    footer_table = Table(footer_data, colWidths=[6 * inch])
    footer_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Oblique"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), "grey"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return footer_table
