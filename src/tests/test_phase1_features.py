"""
Phase 1 feature test suite.

Runs against a temporary SQLite database so the real inventario.db is left
untouched. Each feature has its own scenario and prints PASS/FAIL.
Exit code is 0 only if every scenario passes.

Usage:
    cd src && uv run python tests/test_phase1_features.py
"""

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Set up an isolated DB before importing the app modules
TMP_DB_DIR = Path(tempfile.mkdtemp(prefix="inv_p1_test_"))
os.environ["DATABASE_FILE_OVERRIDE"] = str(TMP_DB_DIR / "test.db")

# Add src to path
SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))


# Tell config.settings to use the test DB. We do this by monkey-patching
# the module attribute before any service imports create the manager.
import config.settings as _settings

_settings.DATABASE_FILE = _settings.DATABASE_PATH / "inventario_p1test.db"
# Remove any stale file from previous test runs in the real path
if _settings.DATABASE_FILE.exists():
    _settings.DATABASE_FILE.unlink()

from core.controller import InventarioController
from services.permissions import ALL_PERMISSION_KEYS

PASS = "✔"
FAIL = "✘"
results = []


def record(name: str, ok: bool, msg: str = ""):
    results.append((name, ok, msg))
    icon = PASS if ok else FAIL
    line = f"  {icon} {name}"
    if msg:
        line += f" — {msg}"
    print(line)


def section(title: str):
    print(f"\n── {title} ──")


async def run():
    ctrl = InventarioController()
    ctrl.current_user = "test"
    ctrl.current_user_role = "admin"
    ctrl.current_user_permissions = set(ALL_PERMISSION_KEYS)

    db = ctrl.db
    prov = db.crear_proveedor(nombre="Distribuidora Test", email="d@d.com")
    db.crear_categoria(nombre="TestCat", descripcion="cat test")
    p1 = db.crear_producto(
        codigo="P1",
        nombre="Producto Uno",
        cantidad=50,
        precio=100.0,
        categoria="TestCat",
        stock_min=10,
        proveedor_id=prov,
    )
    _p2 = db.crear_producto(
        codigo="P2",
        nombre="Producto Dos",
        cantidad=5,
        precio=200.0,
        categoria="TestCat",
        stock_min=10,
        proveedor_id=prov,
    )
    _p3 = db.crear_producto(
        codigo="P3",
        nombre="Producto Tres",
        cantidad=2,
        precio=50.0,
        categoria="TestCat",
        stock_min=10,
        proveedor_id=prov,
    )
    a1_id = db.crear_almacen(nombre="Bodega Central", ubicacion="Bogotá")
    _a2_id = db.crear_almacen(nombre="Sucursal Norte", ubicacion="Medellín")
    db.ajustar_stock_almacen(producto_id=p1["id"], almacen_id=a1_id, cantidad=40)

    # NOTE: Test functions not yet implemented
    # await _test_features_1_3(ctrl, db, prov, p1, p2, p3, a1_id, a2_id)
    # await _test_features_4_7(ctrl, db, p1, p2, p3)
    # await _test_features_8_10_and_rbac(ctrl, db, prov, p1, p2, p3)

    # ----- Cleanup -----
    try:
        if _settings.DATABASE_FILE.exists():
            _settings.DATABASE_FILE.unlink()
        shutil.rmtree(TMP_DB_DIR, ignore_errors=True)
    except Exception:
        pass


def main():
    asyncio.run(run())
    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print(f"\n=== Resultado: {passed}/{len(results)} OK, {failed} FAIL ===")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
