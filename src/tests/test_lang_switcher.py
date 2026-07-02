"""
Tests for the sidebar LangSwitcher component (ui/components.py).

After removing the standalone show_i18n view, the LangSwitcher is the single
entry point for changing UI language. These tests cover:

  - Dropdown is rendered with current locale preselected.
  - Selecting a different language calls set_locale immediately.
  - When a controller is provided, the change is persisted via
    controller.cambiar_idioma (asyncio.create_task is scheduled).
  - on_change callback receives the new language.
  - Selecting the current language is a no-op (no persist).

Run:
    cd src && .venv/Scripts/python.exe tests/test_lang_switcher.py
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from types import SimpleNamespace

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

pytestmark = pytest.mark.asyncio

TMP_DB_DIR = Path(tempfile.mkdtemp(prefix="inv_langswitcher_test_"))
SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

import config.settings as _settings

_settings.DATABASE_FILE = _settings.DATABASE_PATH / "inventario_lswitch_test.db"
if _settings.DATABASE_FILE.exists():
    _settings.DATABASE_FILE.unlink()

import flet as ft

from core.controller import InventarioController
from services.permissions import ALL_PERMISSION_KEYS
from ui.components import LangSwitcher
from utils.i18n import get_locale, set_locale

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


def _find_dropdown(control):
    if isinstance(control, ft.Dropdown):
        return control
    children = getattr(control, "controls", None)
    if children:
        for c in children:
            found = _find_dropdown(c)
            if found is not None:
                return found
    content = getattr(control, "content", None)
    if content is not None and content is not control:
        return _find_dropdown(content)
    return None


def _trigger_dropdown_change(dd, value: str) -> None:
    dd.value = value
    dd.on_select(SimpleNamespace(control=dd))


async def test_dropdown_preselects_current_locale(ctrl):
    set_locale("es")
    ctrl.current_user = "admin"

    container = LangSwitcher.create(controller=ctrl)
    dd = _find_dropdown(container)
    assert dd is not None, "LangSwitcher did not render a Dropdown"

    record(
        "Dropdown preselects the current locale",
        dd.value == "es",
        f"value={dd.value}",
    )


async def test_changing_language_calls_set_locale_and_persists(ctrl):
    set_locale("es")
    ctrl.current_user = "admin"

    persist_calls: list[str] = []
    original = ctrl.cambiar_idioma

    async def spy(usuario, idioma):
        persist_calls.append(idioma)
        return await original(usuario, idioma)

    ctrl.cambiar_idioma = spy  # type: ignore[assignment]
    on_change_received: list[str] = []

    try:
        container = LangSwitcher.create(
            controller=ctrl,
            on_change=on_change_received.append,
        )
        dd = _find_dropdown(container)

        _trigger_dropdown_change(dd, "en")
        await asyncio.sleep(0.3)

        record(
            "set_locale was called (locale is now 'en')",
            get_locale() == "en",
            f"locale={get_locale()}",
        )
        record(
            "controller.cambiar_idioma was scheduled and ran",
            persist_calls == ["en"],
            f"persisted={persist_calls}",
        )
        record(
            "on_change callback received the new language",
            on_change_received == ["en"],
            f"callbacks={on_change_received}",
        )

        set_locale("es")
    finally:
        ctrl.cambiar_idioma = original  # type: ignore[assignment]


async def test_same_language_is_noop(ctrl):
    set_locale("es")
    ctrl.current_user = "admin"

    persist_calls: list[str] = []
    original = ctrl.cambiar_idioma

    async def spy(usuario, idioma):
        persist_calls.append(idioma)
        return await original(usuario, idioma)

    ctrl.cambiar_idioma = spy  # type: ignore[assignment]
    try:
        container = LangSwitcher.create(controller=ctrl)
        dd = _find_dropdown(container)
        _trigger_dropdown_change(dd, "es")
        await asyncio.sleep(0.1)
        record(
            "Selecting current locale does not call cambiar_idioma",
            persist_calls == [],
            f"persist_calls={persist_calls}",
        )
    finally:
        ctrl.cambiar_idioma = original  # type: ignore[assignment]


async def test_no_controller_means_session_only(ctrl):
    set_locale("es")
    container = LangSwitcher.create(controller=None)
    dd = _find_dropdown(container)
    _trigger_dropdown_change(dd, "en")
    await asyncio.sleep(0.1)
    record(
        "Without controller, locale still switches (session only)",
        get_locale() == "en",
        f"locale={get_locale()}",
    )
    set_locale("es")


async def run():
    ctrl = InventarioController()
    ctrl.current_user = "admin"
    ctrl.current_user_role = "admin"
    ctrl.current_user_permissions = set(ALL_PERMISSION_KEYS)

    section("LangSwitcher - basic")
    try:
        await test_dropdown_preselects_current_locale(ctrl)
    except Exception:
        record("preselect current locale", False, traceback.format_exc())

    section("LangSwitcher - change persists via controller")
    try:
        await test_changing_language_calls_set_locale_and_persists(ctrl)
    except Exception:
        record("change persists", False, traceback.format_exc())

    section("LangSwitcher - same language is a no-op")
    try:
        await test_same_language_is_noop(ctrl)
    except Exception:
        record("same lang noop", False, traceback.format_exc())

    section("LangSwitcher - no controller, session only")
    try:
        await test_no_controller_means_session_only(ctrl)
    except Exception:
        record("no controller", False, traceback.format_exc())


def main():
    asyncio.run(run())
    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print(f"\n=== Resultado: {passed}/{len(results)} OK, {failed} FAIL ===")

    try:
        if _settings.DATABASE_FILE.exists():
            _settings.DATABASE_FILE.unlink()
        shutil.rmtree(TMP_DB_DIR, ignore_errors=True)
    except Exception:
        pass

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
