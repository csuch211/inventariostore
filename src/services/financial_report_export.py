"""Financial report PDF exporter.

Generates PDF reports for P&L, balance sheet, and financial dashboard.
"""

from datetime import datetime
from pathlib import Path

from utils.exceptions import InventarioException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class FinancialReportExporter:
    """Export financial reports to PDF."""

    def __init__(self, export_dir: Path | None = None):
        self.export_dir = export_dir or Path("./exports")
        self.export_dir.mkdir(exist_ok=True)

    def _fmt_money(self, v) -> str:
        try:
            return f"${float(v):,.2f}"
        except Exception:
            return "$0.00"

    def export_estado_resultados(
        self,
        balance: list[dict],
        filename: str | None = None,
    ) -> Path:
        """Export P&L statement to PDF."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

            if not filename:
                filename = f"estado_resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            filepath = self.export_dir / filename

            # Group by account type
            ingresos = [(b["cuenta_codigo"], b["cuenta_nombre"], b.get("total_credito", 0))
                        for b in balance if b.get("cuenta_codigo", "").startswith("4")]
            gastos = [(b["cuenta_codigo"], b["cuenta_nombre"], b.get("total_debito", 0))
                      for b in balance if b.get("cuenta_codigo", "").startswith("5")]

            total_ingresos = sum(v for _, _, v in ingresos)
            total_gastos = sum(v for _, _, v in gastos)
            utilidad = total_ingresos - total_gastos

            doc = SimpleDocTemplate(str(filepath), pagesize=letter,
                                    rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []

            # Title
            styles = getSampleStyleSheet()
            elements.append(Spacer(1, 0.5 * inch))

            # Ingresos table
            if ingresos:
                elements.append(_make_section_table(
                    "INGRESOS", ingresos, total_ingresos, colors.HexColor("#16A34A")
                ))
                elements.append(Spacer(1, 0.3 * inch))

            # Gastos table
            if gastos:
                elements.append(_make_section_table(
                    "GASTOS", gastos, total_gastos, colors.HexColor("#DC2626")
                ))
                elements.append(Spacer(1, 0.3 * inch))

            # Utilidad Neta
            util_color = colors.HexColor("#16A34A") if utilidad >= 0 else colors.HexColor("#DC2626")
            util_data = [
                ["UTILIDAD NETA", self._fmt_money(utilidad)],
            ]
            util_table = Table(util_data, colWidths=[3 * inch, 2 * inch])
            util_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 14),
                ("TEXTCOLOR", (0, 0), (-1, -1), util_color),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]))
            elements.append(util_table)

            # Footer
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(_make_footer(f"Estado de Resultados - {datetime.now().strftime('%Y-%m-%d %H:%M')}"))

            doc.build(elements)
            logger.info("P&L exported: %s", filepath)
            return filepath
        except Exception as e:
            logger.error("Error exporting P&L: %s", e)
            raise InventarioException(f"Export failed: {e}")

    def export_balance_general(
        self,
        balance: list[dict],
        filename: str | None = None,
    ) -> Path:
        """Export balance sheet to PDF."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

            if not filename:
                filename = f"balance_general_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            filepath = self.export_dir / filename

            activos = [(b["cuenta_codigo"], b["cuenta_nombre"], b.get("total_debito", 0))
                       for b in balance if b.get("cuenta_codigo", "").startswith("1")]
            pasivos = [(b["cuenta_codigo"], b["cuenta_nombre"], b.get("total_credito", 0))
                       for b in balance if b.get("cuenta_codigo", "").startswith("2")]
            patrimonio = [(b["cuenta_codigo"], b["cuenta_nombre"], b.get("total_credito", 0))
                          for b in balance if b.get("cuenta_codigo", "").startswith("3")]

            total_activos = sum(v for _, _, v in activos)
            total_pasivos = sum(v for _, _, v in pasivos)
            total_patrimonio = sum(v for _, _, v in patrimonio)

            doc = SimpleDocTemplate(str(filepath), pagesize=letter,
                                    rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []

            elements.append(Spacer(1, 0.5 * inch))

            # Activos
            if activos:
                elements.append(_make_section_table(
                    "ACTIVOS", activos, total_activos, colors.HexColor("#2563EB")
                ))
                elements.append(Spacer(1, 0.3 * inch))

            # Pasivos
            if pasivos:
                elements.append(_make_section_table(
                    "PASIVOS", pasivos, total_pasivos, colors.HexColor("#D97706")
                ))
                elements.append(Spacer(1, 0.3 * inch))

            # Patrimonio
            if patrimonio:
                elements.append(_make_section_table(
                    "PATRIMONIO", patrimonio, total_patrimonio, colors.HexColor("#16A34A")
                ))
                elements.append(Spacer(1, 0.3 * inch))

            # Footer
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(_make_footer(f"Balance General - {datetime.now().strftime('%Y-%m-%d %H:%M')}"))

            doc.build(elements)
            logger.info("Balance sheet exported: %s", filepath)
            return filepath
        except Exception as e:
            logger.error("Error exporting balance sheet: %s", e)
            raise InventarioException(f"Export failed: {e}")

    def export_dashboard_financiero(
        self,
        balance: list[dict],
        stats: dict | None = None,
        filename: str | None = None,
    ) -> Path:
        """Export financial dashboard to PDF."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

            if not filename:
                filename = f"dashboard_financiero_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            filepath = self.export_dir / filename

            # Calculate metrics
            ingresos = sum(b.get("total_credito", 0) for b in balance
                          if b.get("cuenta_codigo", "").startswith("4"))
            gastos = sum(b.get("total_debito", 0) for b in balance
                         if b.get("cuenta_codigo", "").startswith("5"))
            utilidad = ingresos - gastos

            activos = sum(b.get("total_debito", 0) for b in balance
                          if b.get("cuenta_codigo", "").startswith("1"))
            pasivos = sum(b.get("total_credito", 0) for b in balance
                          if b.get("cuenta_codigo", "").startswith("2"))
            patrimonio = activos - pasivos

            doc = SimpleDocTemplate(str(filepath), pagesize=letter,
                                    rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []

            elements.append(Spacer(1, 0.5 * inch))

            # KPIs table
            kpi_data = [
                ["MÉTRICA", "VALOR"],
                ["Ingresos", self._fmt_money(ingresos)],
                ["Gastos", self._fmt_money(gastos)],
                ["Utilidad Neta", self._fmt_money(utilidad)],
                ["", ""],
                ["Activos", self._fmt_money(activos)],
                ["Pasivos", self._fmt_money(pasivos)],
                ["Patrimonio", self._fmt_money(patrimonio)],
            ]
            kpi_table = Table(kpi_data, colWidths=[3 * inch, 2 * inch])
            kpi_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]))
            elements.append(kpi_table)

            # Footer
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(_make_footer(f"Dashboard Financiero - {datetime.now().strftime('%Y-%m-%d %H:%M')}"))

            doc.build(elements)
            logger.info("Financial dashboard exported: %s", filepath)
            return filepath
        except Exception as e:
            logger.error("Error exporting financial dashboard: %s", e)
            raise InventarioException(f"Export failed: {e}")


def _make_section_table(title: str, items: list, total: float, color) -> Table:
    """Create a section table for financial reports."""
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.units import inch
    from reportlab.platypus import Table, TableStyle

    data = [[title, "MONTO"]]
    for codigo, nombre, monto in items:
        data.append([f"{codigo} - {nombre}", f"${monto:,.2f}"])
    data.append(["TOTAL", f"${total:,.2f}"])

    table = Table(data, colWidths=[4 * inch, 2 * inch])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), color),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [rl_colors.white, rl_colors.HexColor("#F8FAFC")]),
    ]))
    return table


def _make_footer(text: str) -> Table:
    """Create a footer for financial reports."""
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
