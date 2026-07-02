"""Tests for ExportService: CSV, JSON, PDF, XLSX export and CSV/XLSX import."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from services.export import ExportService
from utils.exceptions import InventarioException


@pytest.fixture
def export_service():
    tmp_dir = Path(tempfile.mkdtemp(prefix="inv_export_test_"))
    service = ExportService(export_dir=tmp_dir)
    yield service
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)


SAMPLE_PRODUCTS = [
    {"codigo": "P001", "nombre": "Producto A", "cantidad": 10, "precio": 5.99, "categoria": "General"},
    {"codigo": "P002", "nombre": "Producto B", "cantidad": 3, "precio": 12.50, "categoria": "General"},
]


class TestExportCSV:
    def test_export_csv_success(self, export_service):
        path = export_service.export_to_csv(SAMPLE_PRODUCTS)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "codigo" in content
        assert "P001" in content
        assert "Producto A" in content

    def test_export_csv_empty_list_raises(self, export_service):
        with pytest.raises(InventarioException, match="No products to export"):
            export_service.export_to_csv([])

    def test_export_csv_custom_filename(self, export_service):
        path = export_service.export_to_csv(SAMPLE_PRODUCTS, filename="custom.csv")
        assert path.name == "custom.csv"

    def test_export_csv_roundtrip(self, export_service):
        path = export_service.export_to_csv(SAMPLE_PRODUCTS)
        import csv
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["codigo"] == "P001"


class TestExportJSON:
    def test_export_json_success(self, export_service):
        path = export_service.export_to_json(SAMPLE_PRODUCTS)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data) == 2
        assert data[0]["codigo"] == "P001"

    def test_export_json_empty_list(self, export_service):
        path = export_service.export_to_json([])
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data == []

    def test_export_json_custom_filename(self, export_service):
        path = export_service.export_to_json(SAMPLE_PRODUCTS, filename="data.json")
        assert path.name == "data.json"


class TestExportSummaryReport:
    def test_export_summary_report_success(self, export_service):
        stats = {"total_productos": 10, "cantidad_total": 150, "valor_total": 5000.0}
        path = export_service.export_summary_report(stats)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "10" in content
        assert "150" in content
        assert "5,000.00" in content

    def test_export_summary_empty_stats(self, export_service):
        path = export_service.export_summary_report({})
        assert path.exists()


class TestExportPDF:
    def test_export_pdf_success(self, export_service):
        path = export_service.export_to_pdf(SAMPLE_PRODUCTS)
        assert path.exists()
        assert path.suffix == ".pdf"
        assert path.stat().st_size > 100

    def test_export_pdf_empty_raises(self, export_service):
        with pytest.raises(InventarioException, match="No products to export"):
            export_service.export_to_pdf([])

    def test_export_pdf_custom_columns(self, export_service):
        columns = [("codigo", "Código"), ("nombre", "Nombre")]
        path = export_service.export_to_pdf(SAMPLE_PRODUCTS, columns=columns)
        assert path.exists()

    def test_export_pdf_custom_title(self, export_service):
        path = export_service.export_to_pdf(SAMPLE_PRODUCTS, title="Mi Reporte")
        assert path.exists()


class TestExportXLSX:
    def test_export_xlsx_success(self, export_service):
        path = export_service.export_to_xlsx(SAMPLE_PRODUCTS)
        assert path.exists()
        assert path.suffix == ".xlsx"
        assert path.stat().st_size > 100

    def test_export_xlsx_empty_raises(self, export_service):
        with pytest.raises(InventarioException, match="No products to export"):
            export_service.export_to_xlsx([])

    def test_export_xlsx_custom_columns(self, export_service):
        columns = [("codigo", "Código"), ("nombre", "Nombre")]
        path = export_service.export_to_xlsx(SAMPLE_PRODUCTS, columns=columns)
        assert path.exists()


class TestImportCSV:
    def test_import_csv_success(self, export_service):
        csv_path = export_service.export_dir / "import_test.csv"
        csv_path.write_text("codigo,nombre,cantidad,precio\nIMP-01,Imported,5,10.0\n", encoding="utf-8-sig")

        created = []

        def fake_create(**kwargs):
            created.append(kwargs)
            return kwargs

        success, errors = ExportService.import_from_csv(str(csv_path), fake_create)
        assert success == 1
        assert errors == []
        assert created[0]["codigo"] == "IMP-01"

    def test_import_csv_file_not_found(self, export_service):
        with pytest.raises(InventarioException, match="CSV file not found"):
            ExportService.import_from_csv("/nonexistent.csv", lambda: None)

    def test_import_csv_missing_required_column(self, export_service):
        csv_path = export_service.export_dir / "bad.csv"
        csv_path.write_text("name,price\nTest,10\n", encoding="utf-8-sig")

        with pytest.raises(InventarioException, match="Missing required column"):
            ExportService.import_from_csv(str(csv_path), lambda: None)

    def test_import_csv_empty_file(self, export_service):
        csv_path = export_service.export_dir / "empty.csv"
        csv_path.write_text("", encoding="utf-8-sig")

        with pytest.raises(InventarioException, match="CSV appears to be empty"):
            ExportService.import_from_csv(str(csv_path), lambda: None)

    def test_import_csv_negative_values_rejected(self, export_service):
        csv_path = export_service.export_dir / "neg.csv"
        csv_path.write_text("codigo,nombre,cantidad,precio\nNEG-01,Bad,-5,10.0\n", encoding="utf-8-sig")

        success, errors = ExportService.import_from_csv(str(csv_path), lambda **k: {})
        assert success == 0
        assert any("non-negative" in e for e in errors)


class TestImportXLSX:
    def test_import_xlsx_file_not_found(self, export_service):
        with pytest.raises(InventarioException, match="XLSX file not found"):
            ExportService.import_from_xlsx("/nonexistent.xlsx", lambda: None)

    def test_import_xlsx_empty(self, export_service):
        bad_path = export_service.export_dir / "empty.xlsx"
        bad_path.write_bytes(b"not a real xlsx")
        with pytest.raises(InventarioException):
            ExportService.import_from_xlsx(str(bad_path), lambda: None)
