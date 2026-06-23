"""Regression tests for the focus chains in _show_new_sale (POS) and
_show_stock_management.

Both views share the same bug we already fixed in _show_product_form:
the browser's native tab order jumps out of the form into sidebar
controls (Ventas, Clientes, etc.). The fix wires each form field's
``on_submit`` / ``on_select`` (Enter) and a custom ``on_key_down``
(Tab) handler so focus advances explicitly via ``page.focus()``
along a linear chain.

These tests build the views and assert that:
  1. Every form field has a callable on_submit / on_select.
  2. The expected submit button text is reachable via
     ``AppView._find_submit_btn_static``.
"""

import asyncio
import sys
import types
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO / "src"))

fake_charts = types.ModuleType("ui.charts")
fake_charts.BarChart = type("BarChart", (), {"build": staticmethod(lambda *a, **k: None)})
fake_charts.LineChart = type("LineChart", (), {"build": staticmethod(lambda *a, **k: None)})
fake_charts.PieChart = type("PieChart", (), {"build": staticmethod(lambda *a, **k: None)})
sys.modules["ui.charts"] = fake_charts

from utils.i18n import initialize_language, set_locale

initialize_language("es")

import flet as ft

from ui.app_view import AppView


class FakePage:
    def __init__(self):
        self.controls = []
        self._dialogs = []
        self.overlay = []
        self.width = 1280
        self.height = 800
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
            return self._dialogs.pop()
        return None


def _walk(node):
    yield node
    inner = getattr(node, "content", None)
    if inner is not None and inner is not node:
        yield from _walk(inner)
    for c in getattr(node, "controls", None) or []:
        if c is not node:
            yield from _walk(c)


async def _make_app() -> AppView:
    page = FakePage()
    app = AppView(page)
    await app.controller.login("admin", "Admin123")
    app.current_user = "admin"
    app.current_token = "fake-token"
    app.main_view = ft.Container()
    return app


# ============================================================
# _show_stock_management
# ============================================================


async def test_stock_focus_chain():
    print("\n=== Feature: _show_stock_management focus chain ===")
    app = await _make_app()
    await app._show_stock_management()
    tree = list(_walk(app.main_view.content))

    fields = [
        n
        for n in tree
        if isinstance(n, (ft.TextField, ft.Dropdown))
        and getattr(n, "label", "")
        and getattr(n, "label", "") in ("Cantidad", "Tipo de Movimiento", "Razón")
    ]
    by_label = {f.label: f for f in fields}
    print(f"  fields found: {list(by_label.keys())}")

    expected = ["Cantidad", "Tipo de Movimiento", "Razón"]
    for label in expected:
        assert label in by_label, f"missing field: {label!r}"

    for label in expected:
        f = by_label[label]
        assert callable(getattr(f, "on_submit", None)), f"{label!r} is missing on_submit"
        print(f"  {label!r}: on_submit wired")

    # Submit button reachable via the static helper. _show_stock_management
    # puts the form in main_view.content, not in page.controls, so we look
    # in main_view first.
    btn = AppView._find_submit_btn_static(
        app.main_view, "Actualizar Stock"
    ) or AppView._find_submit_btn_static(app.page, "Actualizar Stock")
    assert btn is not None, "Actualizar Stock button not found by _find_submit_btn_static"
    print(f"  submit button resolved via _find_submit_btn_static: {type(btn).__name__}")

    print("  PASS")


# ============================================================
# _show_new_sale (POS)
# ============================================================


async def test_sales_focus_chain():
    print("\n=== Feature: _show_new_sale focus chain ===")
    app = await _make_app()
    await app._show_new_sale()
    tree = list(_walk(app.main_view.content))

    # The POS uses translated labels; match by either language. Labels
    # are taken from src/utils/translations/{es,en}.json.
    candidates_by_lang = {
        "es": {
            "Cliente": "cliente",
            "Seleccionar producto": "producto",
            "Cant.": "cantidad",
            "Método de pago": "metodo",
            "Referencia": "referencia",
        },
        "en": {
            "Client": "cliente",
            "Select product": "producto",
            "Qty": "cantidad",
            "Payment Method": "metodo",
            "Reference": "referencia",
        },
    }
    cur = set_locale("es") or "es"
    label_to_key = candidates_by_lang.get(cur, candidates_by_lang["es"])

    fields = [
        n
        for n in tree
        if isinstance(n, (ft.TextField, ft.Dropdown)) and getattr(n, "label", "") in label_to_key
    ]
    by_label = {f.label: f for f in fields}
    print(f"  fields found: {list(by_label.keys())}")

    expected_chain = list(label_to_key.keys())
    for label in expected_chain:
        assert label in by_label, f"missing field: {label!r}"

    # Dropdowns use on_select, TextFields use on_submit. Either way the
    # closure must be set.
    for label in expected_chain:
        f = by_label[label]
        if isinstance(f, ft.Dropdown):
            assert callable(getattr(f, "on_select", None)), (
                f"{label!r} (Dropdown) is missing on_select"
            )
        else:
            assert callable(getattr(f, "on_submit", None)), (
                f"{label!r} (TextField) is missing on_submit"
            )
        print(f"  {label!r}: handler wired")

    # Submit button must be resolvable by either locale. The Spanish
    # label is "Completar Venta" (see sales.complete_sale in the
    # translations JSON), the English one is "Complete Sale".
    submit_labels_es = ["Completar Venta", "Complete Sale"]
    btn_es = None
    for label in submit_labels_es:
        btn_es = AppView._find_submit_btn_static(
            app.main_view, label
        ) or AppView._find_submit_btn_static(app.page, label)
        if btn_es is not None:
            break
    set_locale("en")
    submit_labels_en = ["Complete Sale", "Completar Venta"]
    btn_en = None
    for label in submit_labels_en:
        btn_en = AppView._find_submit_btn_static(
            app.main_view, label
        ) or AppView._find_submit_btn_static(app.page, label)
        if btn_en is not None:
            break
    assert btn_es is not None or btn_en is not None, (
        "Submit button not reachable via _find_submit_btn_static"
    )
    print(f"  submit button resolved: es={btn_es is not None}, en={btn_en is not None}")

    # Reset locale for subsequent tests.
    set_locale("es")

    print("  PASS")


# ============================================================
# Helper exposes the right controls (sanity)
# ============================================================


async def test_find_submit_btn_static():
    print("\n=== Feature: _find_submit_btn_static helper ===")
    page = FakePage()
    save = ft.Button(content=ft.Text("Save"))
    cancel = ft.Button(content=ft.Text("Cancel"))
    col = ft.Column([save, cancel])
    page.add(col)
    found = AppView._find_submit_btn_static(page, "Save")
    assert found is save, "expected the Save button"
    print("  found Save: OK")
    missing = AppView._find_submit_btn_static(page, "DoesNotExist")
    assert missing is None
    print("  missing label returns None: OK")
    print("  PASS")


async def main():
    await test_stock_focus_chain()
    await test_sales_focus_chain()
    await test_find_submit_btn_static()
    print("\n=== ALL FEATURES PASS ===")


if __name__ == "__main__":
    asyncio.run(main())
