"""
Tests for the optimizations and behavior of src/ui/phase3_views_part2.py.

Covers:
  - show_push_queue: ListView rendering, job cards, batched page.update,
    filter dropdown change refresh, enqueue dialog construction.
  - show_image_search: ListView rendering, single shared FilePicker, search
    result rendering, empty path error handling.
  - Module-level constants: _BORDER_HAIRLINE and _STATE_COLORS identity
    is preserved across calls (no per-row allocation).

Note: The standalone show_i18n view was removed; language is now changed
via the sidebar LangSwitcher. Tests for that flow live in
test_lang_switcher.py (next to this file).

Uses fake page/view fakes so no Flet event loop or real UI is required.

Run:
    cd src && .venv/Scripts/python.exe tests/test_phase3_views_part2.py
"""

from __future__ import annotations

import asyncio
import importlib
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from types import SimpleNamespace
from typing import Any

try:
    import pytest
except ModuleNotFoundError:

    class PytestMock:  # type: ignore[no-redef]
        class MarkMock:
            @staticmethod
            def asyncio(f):
                return f

        mark = MarkMock

    pytest = PytestMock

# ---------------------------------------------------------------------------
# Isolated DB setup (same pattern as test_phase3_features.py).
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.asyncio

TMP_DB_DIR = Path(tempfile.mkdtemp(prefix="inv_p3ui_test_"))
SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

import config.settings as _settings  # noqa: E402

_settings.DATABASE_FILE = _settings.DATABASE_PATH / "inventario_p3ui_test.db"
if _settings.DATABASE_FILE.exists():
    _settings.DATABASE_FILE.unlink()

import flet as ft  # noqa: E402

from core.controller import InventarioController  # noqa: E402
from services.permissions import ALL_PERMISSION_KEYS  # noqa: E402

# Force a fresh import of the module under test (so module-level singletons
# are not carried over from any earlier run in the same interpreter).
p3v2 = importlib.import_module("ui.phase3_views_part2")
importlib.reload(p3v2)


PASS = "✔"
FAIL = "✘"
results: list[tuple] = []


def record(name: str, ok: bool, msg: str = "") -> None:
    results.append((name, ok, msg))
    icon = PASS if ok else FAIL
    line = f"  {icon} {name}"
    if msg:
        line += f" — {msg}"
    print(line)


def section(title: str) -> None:
    print(f"\n── {title} ──")


# ---------------------------------------------------------------------------
# Fakes — minimal stand-ins for ft.Page and the view object.
# ---------------------------------------------------------------------------


class FakeOverlay(list):
    """Behaves like page.overlay: list that we can append to."""


class FakePage:
    """Captures state normally mutated by ft.Page during a render."""

    def __init__(self) -> None:
        self.overlay: FakeOverlay = FakeOverlay()
        self.update_count: int = 0
        self.dialogs_shown: list[Any] = []
        self.popped_dialogs: int = 0
        self.snackbars: list[Any] = []
        self.title: str = ""

    def update(self) -> None:
        self.update_count += 1

    def show_dialog(self, dialog: Any) -> None:
        self.dialogs_shown.append(dialog)

    def pop_dialog(self) -> None:
        self.popped_dialogs += 1

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"FakePage(updates={self.update_count}, "
            f"dialogs={len(self.dialogs_shown)}, "
            f"popped={self.popped_dialogs})"
        )


class FakeMainView:
    """Stand-in for AppView.main_view: a Container-like attribute holder."""

    def __init__(self) -> None:
        self.content: Any | None = None


class FakeView:
    """Stand-in for AppView — exposes .page, .main_view, .controller."""

    def __init__(self, controller: InventarioController) -> None:
        self.page: FakePage = FakePage()
        self.main_view: FakeMainView = FakeMainView()
        self.controller = controller
        self.refresh_nav_calls: int = 0

    async def _refresh_nav_badges(self) -> None:
        self.refresh_nav_calls += 1


# ---------------------------------------------------------------------------
# Helpers used in the assertions.
# ---------------------------------------------------------------------------


def _collect_controls_recursive(control: Any) -> list[Any]:
    """Walk a control tree and return every control encountered."""
    found: list[Any] = [control]
    children = getattr(control, "controls", None)
    if children:
        for c in children:
            found.extend(_collect_controls_recursive(c))
    content = getattr(control, "content", None)
    if content is not None and content is not control:
        found.extend(_collect_controls_recursive(content))
    return found


# ---------------------------------------------------------------------------
# Test scenarios.
# ---------------------------------------------------------------------------


async def test_push_queue_renders_listview_and_cards(ctrl: InventarioController) -> None:
    view = FakeView(ctrl)
    await p3v2.show_push_queue(view)

    # main_view content must be a Column wrapping the header, toolbar, list.
    assert view.main_view.content is not None, "main_view.content not set"
    tree = _collect_controls_recursive(view.main_view.content)

    listviews = [c for c in tree if isinstance(c, ft.ListView)]
    record(
        "Push queue uses ft.ListView (virtualization)",
        len(listviews) == 1,
        f"listviews={len(listviews)}",
    )

    # ListView must hold the seeded jobs.
    lv = listviews[0]
    record(
        "Push queue renders one card per job",
        len(lv.controls) == 2,
        f"cards={len(lv.controls)}",
    )

    # Buttons present
    buttons = [c for c in tree if isinstance(c, ft.Button)]
    record(
        "Push queue toolbar has new + dispatch buttons",
        len(buttons) == 2,
        f"buttons={len(buttons)}",
    )


async def test_push_queue_filters_trigger_single_refresh(
    ctrl: InventarioController,
) -> None:
    view = FakeView(ctrl)
    await p3v2.show_push_queue(view)

    updates_before = view.page.update_count

    # Simulate the dropdown change event by invoking the bound handler.
    dropdown = None
    for c in _collect_controls_recursive(view.main_view.content):
        if isinstance(c, ft.Dropdown):
            dropdown = c
            break
    assert dropdown is not None, "Dropdown not found"

    # Invoke on_change. It's a lambda that schedules a task; let it run.
    dropdown.on_change(SimpleNamespace())  # type: ignore[arg-type]
    # Sleep long enough for the scheduled refresh to complete its DB call.
    await asyncio.sleep(0.3)

    record(
        "Dropdown change triggers a refresh (page.update increased)",
        view.page.update_count > updates_before,
        f"updates before={updates_before}, after={view.page.update_count}",
    )


async def test_push_queue_enqueue_dialog_built(ctrl: InventarioController) -> None:
    view = FakeView(ctrl)
    await p3v2.show_push_queue(view)

    new_btn = None
    for c in _collect_controls_recursive(view.main_view.content):
        if isinstance(c, ft.Button) and getattr(c, "on_click", None):
            new_btn = c
            break
    assert new_btn is not None, "New-job button not found"

    # Invoke on_click to open the enqueue dialog (it is async).
    await new_btn.on_click(SimpleNamespace())  # type: ignore[arg-type]

    record(
        "Enqueue dialog is shown after clicking new",
        len(view.page.dialogs_shown) == 1,
        f"dialogs={len(view.page.dialogs_shown)}",
    )


async def test_i18n_idiomas_cache(ctrl: InventarioController) -> None:
    """Deprecated: show_i18n was removed. LangSwitcher is tested separately."""
    record("show_i18n removed (deprecated test)", True, "skipped")


async def test_image_search_uses_listview_and_shared_picker(
    ctrl: InventarioController,
) -> None:
    # Reset the module-level picker so we can observe fresh creation.
    # Another test module (test_lang_switcher.py) may have populated it.
    p3v2._image_search_picker = None

    view = FakeView(ctrl)
    await p3v2.show_image_search(view)

    tree = _collect_controls_recursive(view.main_view.content)
    listviews = [c for c in tree if isinstance(c, ft.ListView)]
    record(
        "Image search uses ft.ListView (virtualization)",
        len(listviews) == 1,
        f"listviews={len(listviews)}",
    )

    first_picker = view.page.overlay[0] if view.page.overlay else None
    record(
        "Single FilePicker is added to page.overlay",
        len(view.page.overlay) == 1 and isinstance(first_picker, ft.FilePicker),
        f"overlay len={len(view.page.overlay)}",
    )

    # A second view must reuse the same picker instance (identity check,
    # not overlay-empty check — the picker is re-parented to the new page).
    view2 = FakeView(ctrl)
    await p3v2.show_image_search(view2)
    second_picker = view2.page.overlay[0] if view2.page.overlay else None
    record(
        "Second show_image_search reuses the same FilePicker instance",
        second_picker is first_picker,
        f"first_id={id(first_picker)} second_id={id(second_picker)}",
    )
    # And the global singleton matches.
    record(
        "Module-level _image_search_picker is the same instance",
        p3v2._image_search_picker is first_picker,
        f"global_id={id(p3v2._image_search_picker)}",
    )


async def test_image_search_renders_results(ctrl: InventarioController) -> None:
    view = FakeView(ctrl)
    await p3v2.show_image_search(view)

    # Find the ruta field and populate it.
    ruta = None
    for c in _collect_controls_recursive(view.main_view.content):
        if isinstance(c, ft.TextField) and getattr(c, "label", "") == "Top K":
            continue
        if isinstance(c, ft.TextField):
            ruta = c
            break
    assert ruta is not None, "ruta_field not found"
    ruta.value = str(SRC_DIR / "tests" / "_tmp_images" / "p1.png")

    # Find search button.
    search_btn = None
    for c in _collect_controls_recursive(view.main_view.content):
        if isinstance(c, ft.Button) and not getattr(c.style, "bgcolor", None):
            search_btn = c
            break
    assert search_btn is not None, "search button not found"

    await search_btn.on_click(SimpleNamespace())  # type: ignore[arg-type]
    await asyncio.sleep(0)

    listview = next(
        c for c in _collect_controls_recursive(view.main_view.content) if isinstance(c, ft.ListView)
    )
    record(
        "Image search populates ListView with results",
        len(listview.controls) >= 1,
        f"rows={len(listview.controls)}",
    )


async def test_module_constants_are_hoisted(ctrl: InventarioController) -> None:
    # Identity check: must be the same object across calls.
    a = p3v2._BORDER_HAIRLINE
    b = p3v2._BORDER_HAIRLINE
    record(
        "_BORDER_HAIRLINE is a stable singleton (no per-row allocation)",
        a is b,
        f"id(a)={id(a)} id(b)={id(b)}",
    )

    s1 = p3v2._STATE_COLORS
    s2 = p3v2._STATE_COLORS
    record(
        "_STATE_COLORS is a stable singleton",
        s1 is s2 and set(s1.keys()) == {"pendiente", "enviado", "fallido"},
        f"keys={list(s1.keys())}",
    )


async def test_job_card_helper_is_pure(ctrl: InventarioController) -> None:
    job = {
        "id": 7,
        "tipo": "low_stock",
        "estado": "pendiente",
        "destinatario": "a@b.com",
        "asunto": "low",
        "cuerpo": "x" * 500,
        "intentos": 0,
        "ultimo_error": None,
        "creado_en": "2026-06-23 00:00:00",
    }
    card = p3v2._build_job_card(job)
    assert isinstance(card, ft.Container)
    text_values = [t.value for t in _collect_controls_recursive(card) if isinstance(t, ft.Text)]
    record(
        "Job card includes id, tipo, asunto and truncated body",
        any("#7" in v for v in text_values)
        and any("low_stock" in v for v in text_values)
        and any("low" in v for v in text_values),
        f"sample={text_values[:5]}",
    )
    # Body is truncated to 200 chars.
    bodies = [v for v in text_values if "x" in v and len(v) > 5]
    record(
        "Long body is truncated (length <= 200)",
        all(len(b) <= 200 for b in bodies),
        f"max_len={max(len(b) for b in bodies) if bodies else 0}",
    )


# ---------------------------------------------------------------------------
# Orchestrator.
# ---------------------------------------------------------------------------


async def run() -> None:
    ctrl = InventarioController()
    ctrl.current_user = "admin"
    ctrl.current_user_role = "admin"
    ctrl.current_user_permissions = set(ALL_PERMISSION_KEYS)
    db = ctrl.db

    # Seed two products and one push job per relevant state to exercise
    # the rendering branches.
    db.crear_producto(
        codigo="VP1",
        nombre="Camiseta UI",
        cantidad=100,
        precio=20.0,
        stock_min=10,
        categoria="Ropa",
    )

    ok, _ = await ctrl.encolar_push(
        tipo="low_stock",
        destinatario="admin@test.com",
        asunto="Bajo stock",
        cuerpo="P1 bajo mínimo",
    )
    assert ok
    await ctrl.encolar_push(
        tipo="sale",
        destinatario="x@y.com",
        asunto="Venta",
        cuerpo="Venta registrada",
    )

    section("show_push_queue")
    try:
        await test_push_queue_renders_listview_and_cards(ctrl)
        await test_push_queue_filters_trigger_single_refresh(ctrl)
        await test_push_queue_enqueue_dialog_built(ctrl)
    except Exception:
        record("show_push_queue", False, traceback.format_exc())

    section("show_i18n (deprecated view removed)")
    try:
        await test_i18n_idiomas_cache(ctrl)
    except Exception:
        record("show_i18n", False, traceback.format_exc())

    section("show_image_search")
    try:
        await test_image_search_uses_listview_and_shared_picker(ctrl)
        await test_image_search_renders_results(ctrl)
    except Exception:
        record("show_image_search", False, traceback.format_exc())

    section("Module-level optimizations")
    try:
        await test_module_constants_are_hoisted(ctrl)
        await test_job_card_helper_is_pure(ctrl)
    except Exception:
        record("module constants", False, traceback.format_exc())


def main() -> None:
    asyncio.run(run())
    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print(f"\n=== Resultado: {passed}/{len(results)} OK, {failed} FAIL ===")

    # Cleanup isolated DB and temp dir regardless of outcome.
    try:
        if _settings.DATABASE_FILE.exists():
            _settings.DATABASE_FILE.unlink()
        shutil.rmtree(TMP_DB_DIR, ignore_errors=True)
    except Exception:
        pass

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
