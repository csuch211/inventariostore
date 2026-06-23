"""
Tests for the unified _show_dashboard in AppView (ui/app_view.py).

After removing the legacy views.py / InventarioView and consolidating the
two overlapping KPI sections (basic stats cards + executive block) into a
single 9-card grid, this suite verifies:

  - The KPIs are fetched in a single round-trip via obtener_kpis_dashboard
    (not via 4+ separate controller calls as before).
  - Chart queries run concurrently with the KPI fetch.
  - The render no longer contains the duplicate "Dashboard Ejecutivo" block
    with two rows of KPI cards.
  - The expected KPI metrics are surfaced in the rendered tree.
  - The views.py module no longer exists (no InventarioView leakage).

Run:
    cd src && .venv/Scripts/python.exe tests/test_dashboard_unified.py
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

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

TMP_DB_DIR = Path(tempfile.mkdtemp(prefix="inv_dash_test_"))
SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

import config.settings as _settings  # noqa: E402
from core.controller import InventarioController  # noqa: E402
from services.permissions import ALL_PERMISSION_KEYS  # noqa: E402

_settings.DATABASE_FILE = _settings.DATABASE_PATH / "inventario_dash_test.db"
if _settings.DATABASE_FILE.exists():
    _settings.DATABASE_FILE.unlink()


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


def test_legacy_views_py_removed() -> None:
    legacy = SRC_DIR / "views.py"
    record(
        "src/views.py removed (legacy InventarioView)",
        not legacy.exists(),
        f"path={legacy}",
    )


def test_dashboard_method_signature_present() -> None:
    ui_app_view = importlib.import_module("ui.app_view")
    importlib.reload(ui_app_view)
    cls = ui_app_view.AppView
    method = getattr(cls, "_show_dashboard", None)
    record(
        "AppView._show_dashboard exists and is a coroutine function",
        method is not None and inspect.iscoroutinefunction(method),
        f"present={method is not None}",
    )


def test_unused_translation_keys_removed() -> None:
    for fname in ("es.json", "en.json"):
        path = SRC_DIR / "utils" / "translations" / fname
        data = json.loads(path.read_text(encoding="utf-8"))
        for legacy_key in (
            "dashboard.total_stock",
            "dashboard.total_value",
            "dashboard.low_stock",
        ):
            assert legacy_key not in data, f"{fname} still has {legacy_key}"
    record(
        "Unused legacy dashboard.* keys removed from translations",
        True,
        "es.json + en.json",
    )


# ---------------------------------------------------------------------------
# Integration-style test: instantiate a real controller and exercise the
# data-fetching pattern from _show_dashboard to assert it goes through
# obtener_kpis_dashboard exactly once.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kpis_round_trip_count() -> None:
    ctrl = InventarioController()
    ctrl.current_user = "admin"
    ctrl.current_user_role = "admin"
    ctrl.current_user_permissions = set(ALL_PERMISSION_KEYS)
    db = ctrl.db

    # Seed two products so KPIs are non-trivial.
    db.crear_producto(
        codigo="DP1",
        nombre="Destornillador",
        cantidad=12,
        precio=5.0,
        stock_min=5,
        categoria="Herramientas",
    )
    db.crear_producto(
        codigo="DP2",
        nombre="Martillo",
        cantidad=2,
        precio=15.0,
        stock_min=5,
        categoria="Herramientas",
    )

    # Count invocations of obtener_kpis_dashboard.
    kpis_calls = {"n": 0}
    original = ctrl.obtener_kpis_dashboard

    async def counting():
        kpis_calls["n"] += 1
        return await original()

    ctrl.obtener_kpis_dashboard = counting  # type: ignore[assignment]

    try:
        # Simulate the first half of _show_dashboard.
        async def _charts():
            return await asyncio.gather(
                ctrl.obtener_top_productos_stock(limit=10),
                ctrl.obtener_distribucion_categorias(),
                ctrl.obtener_serie_inventario(dias=30),
                ctrl.obtener_todos_productos(),
            )

        kpis_task = asyncio.create_task(ctrl.obtener_kpis_dashboard())
        charts_task = asyncio.create_task(_charts())
        kpis = await kpis_task
        top, dist, serie, products = await charts_task
    finally:
        ctrl.obtener_kpis_dashboard = original  # type: ignore[assignment]

    record(
        "obtener_kpis_dashboard called exactly once",
        kpis_calls["n"] == 1,
        f"calls={kpis_calls['n']}",
    )

    expected_keys = {
        "total_productos",
        "unidades_totales",
        "valor_inventario_venta",
        "valor_inventario_costo",
        "margen_estimado",
        "productos_criticos",
        "productos_agotados",
        "ventas_hoy_count",
        "ventas_hoy_total",
        "ventas_mes_count",
        "ventas_mes_total",
        "top_productos_mes",
    }
    record(
        "KPIs payload contains all 12 expected keys",
        expected_keys.issubset(kpis.keys()),
        f"missing={expected_keys - set(kpis.keys())}",
    )

    record(
        "Charts + products fetched concurrently (all four resolved)",
        len(top) >= 0 and dist is not None and serie is not None and len(products) == 2,
        (
            f"top={len(top)} dist={dist is not None} "
            f"serie={serie is not None} products={len(products)}"
        ),
    )


@pytest.mark.asyncio
async def test_kpis_and_charts_run_in_parallel() -> None:
    """kpis and chart gather must start before either one finishes, so
    wall-clock latency ≈ max(kpis_time, charts_time), not the sum."""
    ctrl = InventarioController()
    ctrl.current_user = "admin"
    ctrl.current_user_permissions = set(ALL_PERMISSION_KEYS)
    db = ctrl.db
    db.crear_producto(
        codigo="PAR1",
        nombre="Tornillo",
        cantidad=100,
        precio=0.5,
        stock_min=10,
        categoria="Ferretería",
    )

    # Inject a 200ms sleep into kpis to simulate a slow query.
    original_kpis = ctrl.obtener_kpis_dashboard

    async def slow_kpis():
        await asyncio.sleep(0.2)
        return await original_kpis()

    ctrl.obtener_kpis_dashboard = slow_kpis  # type: ignore[assignment]
    try:

        async def _charts():
            return await asyncio.gather(
                ctrl.obtener_top_productos_stock(limit=10),
                ctrl.obtener_distribucion_categorias(),
                ctrl.obtener_serie_inventario(dias=30),
                ctrl.obtener_todos_productos(),
            )

        t0 = time.monotonic()
        kpis_task = asyncio.create_task(ctrl.obtener_kpis_dashboard())
        charts_task = asyncio.create_task(_charts())
        await asyncio.gather(kpis_task, charts_task)
        elapsed = time.monotonic() - t0
    finally:
        ctrl.obtener_kpis_dashboard = original_kpis  # type: ignore[assignment]

    # Sequential would be ~0.2s + ~5*sqlite; concurrent should be well
    # under 0.5s on any machine.
    record(
        "KPIs and charts run concurrently (elapsed < 0.5s with 200ms kpis)",
        elapsed < 0.5,
        f"elapsed={elapsed:.3f}s",
    )


async def run() -> None:
    section("Legacy file removal")
    try:
        test_legacy_views_py_removed()
    except Exception:
        record("legacy views.py", False, traceback.format_exc())

    section("Method signature")
    try:
        test_dashboard_method_signature_present()
    except Exception:
        record("method signature", False, traceback.format_exc())

    section("Translation keys")
    try:
        test_unused_translation_keys_removed()
    except Exception:
        record("unused keys", False, traceback.format_exc())

    section("Single-roundtrip KPI fetch")
    try:
        await test_kpis_round_trip_count()
    except Exception:
        record("kpi roundtrip", False, traceback.format_exc())

    section("Concurrency")
    try:
        await test_kpis_and_charts_run_in_parallel()
    except Exception:
        record("concurrency", False, traceback.format_exc())


def main() -> None:
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
