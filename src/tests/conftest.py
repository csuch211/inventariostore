"""
Shared fixtures for pytest-based test discovery.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Isolated test database
# ---------------------------------------------------------------------------
_TMP_DB_DIR = Path(tempfile.mkdtemp(prefix="inv_pytest_"))
os.environ["DATABASE_FILE_OVERRIDE"] = str(_TMP_DB_DIR / "test.db")

import config.settings as _settings  # noqa: E402

_settings.DATABASE_FILE = _TMP_DB_DIR / "test.db"

from core.controller import InventarioController  # noqa: E402
from services.permissions import ALL_PERMISSION_KEYS  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _isolate_db():
    """Use an isolated temp DB for the entire pytest session."""
    yield
    try:
        if _settings.DATABASE_FILE.exists():
            _settings.DATABASE_FILE.unlink()
        shutil.rmtree(_TMP_DB_DIR, ignore_errors=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Controller fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def ctrl() -> Iterator[InventarioController]:
    """Create a controller with full admin permissions for testing."""
    controller = InventarioController()
    controller.current_user = "admin"
    controller.current_user_role = "admin"
    controller.current_user_permissions = set(ALL_PERMISSION_KEYS)
    yield controller


# ---------------------------------------------------------------------------
# Fake UI doubles (shared across tests that need UI interaction)
# ---------------------------------------------------------------------------


class _FakeOverlay(list):
    """Behaves like page.overlay."""


class FakePage:
    """Stand-in for ft.Page capturing state during UI renders."""

    def __init__(self) -> None:
        self.overlay: _FakeOverlay = _FakeOverlay()
        self.update_count: int = 0
        self.dialogs_shown: list[Any] = []
        self.popped_dialogs: int = 0
        self.snackbars: list[Any] = []
        self.title: str = ""
        self.clean_called: bool = False

    def update(self) -> None:
        self.update_count += 1

    def clean(self) -> None:
        self.clean_called = True

    def add(self, *args: Any) -> None:
        pass

    def show_dialog(self, dialog: Any) -> None:
        self.dialogs_shown.append(dialog)

    def pop_dialog(self) -> None:
        self.popped_dialogs += 1


class FakeMainView:
    """Stand-in for AppView.main_view."""

    def __init__(self) -> None:
        self.content: Any | None = None


@pytest.fixture
def fake_page() -> FakePage:
    """Return a fresh FakePage instance."""
    return FakePage()


@pytest.fixture
def fake_view(ctrl: InventarioController) -> FakeView:
    """Return a FakeView wrapping the ctrl fixture."""
    return FakeView(ctrl)


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
# Seeded database fixture (session-scoped, shared by all tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def seeded_ctrl() -> Iterator[InventarioController]:
    """Controller with pre-seeded products and push jobs."""
    controller = InventarioController()
    controller.current_user = "admin"
    controller.current_user_role = "admin"
    controller.current_user_permissions = set(ALL_PERMISSION_KEYS)
    db = controller.db

    db.crear_producto(
        codigo="SEED-1",
        nombre="Producto Semilla 1",
        cantidad=50,
        precio=10.0,
        stock_min=5,
        categoria="Tests",
    )
    db.crear_producto(
        codigo="SEED-2",
        nombre="Producto Semilla 2",
        cantidad=3,
        precio=20.0,
        stock_min=10,
        categoria="Tests",
    )

    asyncio.run(
        controller.encolar_push(
            tipo="low_stock",
            destinatario="seed@test.com",
            asunto="Seed job",
            cuerpo="Test push job",
        )
    )

    yield controller


# ---------------------------------------------------------------------------
# Charts module stub (replaces ui.charts with no-op stubs)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _stub_charts():
    """Stub ui.charts so that view tests can render without real charts."""

    stub = types.ModuleType("ui.charts")
    for cls_name in ("BarChart", "LineChart", "PieChart"):
        setattr(stub, cls_name, type(cls_name, (), {"build": staticmethod(lambda *a, **kw: None)}))
    old = sys.modules.get("ui.charts")
    sys.modules["ui.charts"] = stub
    yield
    if old is not None:
        sys.modules["ui.charts"] = old
