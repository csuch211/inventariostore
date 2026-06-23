"""Verification suite for the theme-switch and import features.

Run from the repo root:
    uv run python src/tests/verify_theme_and_imports.py
"""

import asyncio
import csv
import shutil
import sys
import tempfile
import types
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO / "src"))

# Stub flet_charts before app_view imports it.
fake_charts = types.ModuleType("ui.charts")
fake_charts.BarChart = type("BarChart", (), {"build": staticmethod(lambda *a, **k: None)})
fake_charts.LineChart = type("LineChart", (), {"build": staticmethod(lambda *a, **k: None)})
fake_charts.PieChart = type("PieChart", (), {"build": staticmethod(lambda *a, **k: None)})
sys.modules["ui.charts"] = fake_charts

from utils.i18n import initialize_language

initialize_language("es")

import flet as ft

from services.export import ExportService


class FakePage:
    def __init__(self):
        self.controls = []
        self._dialogs = []
        self.width = 1280
        self.theme_mode = ft.ThemeMode.LIGHT
        self.title = ""
        self.theme = None
        self.dark_theme = None
        self.padding = 0
        self.spacing = 0
        self.bgcolor = "white"

    def clean(self):
        self.controls.clear()

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self, *a, **k):
        pass

    def show_dialog(self, dlg):
        self._dialogs.append(dlg)

    def pop_dialog(self):
        if self._dialogs:
            self._dialogs.pop()


def _section(title):
    print(f"\n=== {title} ===")


# ------------------------------- Theme fix -----------------------------------


async def feature_theme_change_rebuilds():
    """Regression test: _on_theme_change must trigger a full rebuild, not
    just _navigate_to. The symptom was that switching theme only refreshed
    a few controls until the user changed language (which forces a rebuild).
    """
    _section("Feature: theme switch triggers a full main-view rebuild")
    page = FakePage()
    from ui.app_view import AppView

    app = AppView(page)
    await app.controller.login("admin", "Admin123")
    app.current_user = "admin"
    app.current_token = "fake-token"

    # Set up a known route and a known sidebar.
    app._current_route = "dashboard"
    sidebar_calls = {"count": 0}

    async def _fake_show_main_view():
        sidebar_calls["count"] += 1
        # Simulate the construction that mutates state the test can probe.
        app.main_view = ft.Container(content=ft.Column([], expand=True))

    # Monkeypatch _show_main_view to count calls and stub the heavy rebuild.
    app._show_main_view = _fake_show_main_view  # type: ignore

    # The Switch's on_change calls _on_theme_change(self, e). Build a fake
    # event and dispatch.
    class FakeSwitch:
        value = True  # toggling to dark mode

    class FakeEvent:
        control = FakeSwitch()

    await app._on_theme_change(FakeEvent())
    print(f"  _show_main_view invocations during theme change: {sidebar_calls['count']}")
    assert sidebar_calls["count"] >= 1, "expected at least one full main-view rebuild"

    # Same for the segmented picker.
    sidebar_calls["count"] = 0

    class FakeChoiceEvent:
        class control:
            value = "dark"

    await app._on_theme_choice_change(FakeChoiceEvent())
    assert sidebar_calls["count"] >= 1
    print(f"  segmented picker rebuilds too: {sidebar_calls['count']}")
    print("  PASS")


# ------------------------------- Importers -----------------------------------


def _write_csv(path: Path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for r in rows:
            writer.writerow(r)


def _write_xlsx(path: Path, rows):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    wb.save(str(path))


def _stub_creator():
    """Return a (callable, list) pair; the callable records products passed to it."""
    bucket = []

    def _create(**kwargs):
        bucket.append(kwargs)
        return {"id": len(bucket), **kwargs}

    return _create, bucket


async def feature_import_from_csv():
    _section("Feature: CSV import via ExportService.import_from_csv")
    tmp = Path(tempfile.mkdtemp(prefix="import_csv_test_"))
    try:
        csv_path = tmp / "products.csv"
        _write_csv(
            csv_path,
            [
                ["codigo", "nombre", "cantidad", "precio", "categoria", "descripcion", "stock_min"],
                ["C-001", "Test Mouse", "10", "15.50", "Periféricos", "Wireless mouse", "3"],
                ["C-002", "Test Keyboard", "5", "30", "Periféricos", "Mechanical", "2"],
                ["BAD-1", "Bad row", "notanumber", "5", "", "", "0"],
                ["", "Empty codigo", "1", "1", "", "", "0"],
                ["C-003", "USB Cable", "50", "5.00", "Cables", "1m USB-C", "10"],
            ],
        )

        create, bucket = _stub_creator()
        success, errors = ExportService.import_from_csv(str(csv_path), create)
        print(f"  success={success}, errors={len(errors)}")
        print(f"  created products: {len(bucket)}")
        print(f"  first errors: {errors[:2]}")
        assert success == 3, f"expected 3 valid rows, got {success}"
        assert len(errors) == 2, f"expected 2 errors, got {len(errors)}"
        assert any("cantidad" in e.lower() for e in errors), "expected numeric error"
        assert any("codigo" in e.lower() for e in errors), "expected required-field error"
        assert bucket[0]["codigo"] == "C-001"
        assert bucket[0]["cantidad"] == 10
        assert bucket[0]["stock_min"] == 3
        print("  PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def feature_import_from_xlsx():
    _section("Feature: XLSX import via ExportService.import_from_xlsx")
    tmp = Path(tempfile.mkdtemp(prefix="import_xlsx_test_"))
    try:
        xlsx_path = tmp / "products.xlsx"
        _write_xlsx(
            xlsx_path,
            [
                ["Codigo", "Nombre", "Cantidad", "Precio", "Categoria", "Descripcion", "Stock_Min"],
                ["X-001", "Test Webcam", "8", "45.00", "Cámaras", "HD webcam", "2"],
                ["X-002", "Test Headphones", "12", "99.99", "Audio", "Bluetooth", "5"],
                ["X-003", "Test Charger", "30", "12.50", "Cables", "65W USB-C", "8"],
            ],
        )

        create, bucket = _stub_creator()
        success, errors = ExportService.import_from_xlsx(str(xlsx_path), create)
        print(f"  success={success}, errors={len(errors)}")
        print(f"  created products: {len(bucket)}")
        assert success == 3
        assert errors == []
        assert bucket[0]["codigo"] == "X-001"
        assert bucket[1]["cantidad"] == 12
        assert bucket[2]["stock_min"] == 8
        print("  PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def feature_import_xlsx_rejects_missing_columns():
    _section("Feature: XLSX import rejects missing required columns")
    from utils.exceptions import InventarioException

    tmp = Path(tempfile.mkdtemp(prefix="import_xlsx_bad_test_"))
    try:
        xlsx_path = tmp / "bad.xlsx"
        _write_xlsx(
            xlsx_path,
            [
                ["codigo", "cantidad"],
                ["X-001", "10"],
            ],
        )
        create, _ = _stub_creator()
        try:
            ExportService.import_from_xlsx(str(xlsx_path), create)
        except InventarioException as e:
            print(f"  correctly rejected: {e}")
            assert "nombre" in str(e).lower()
            print("  PASS")
            return
        raise AssertionError("expected InventarioException for missing 'nombre' column")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------- Controller ----------------------------------


async def feature_controller_dispatch():
    _section("Feature: controller.importar_productos_xlsx round-trip")
    from core.controller import InventarioController
    from services.database import DatabaseManager

    db = DatabaseManager()
    ctl = InventarioController.__new__(InventarioController)
    ctl.db = db
    ctl.current_user = "admin"

    tmp = Path(tempfile.mkdtemp(prefix="controller_import_"))
    try:
        xlsx_path = tmp / "controller_test.xlsx"
        _write_xlsx(
            xlsx_path,
            [
                ["codigo", "nombre", "cantidad", "precio"],
                ["CTL-001", "Controller Test 1", "7", "9.99"],
                ["CTL-002", "Controller Test 2", "3", "19.99"],
            ],
        )

        success, errors = await ctl.importar_productos_xlsx(str(xlsx_path))
        print(f"  success={success}, errors={errors}")
        assert success == 2
        assert errors == []
        print("  PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def main():
    await feature_theme_change_rebuilds()
    await feature_import_from_csv()
    await feature_import_from_xlsx()
    await feature_import_xlsx_rejects_missing_columns()
    await feature_controller_dispatch()
    print("\n=== ALL FEATURES PASS ===")


if __name__ == "__main__":
    asyncio.run(main())
