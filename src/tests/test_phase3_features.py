"""
Phase 3 feature test suite.

Covers the 5 infrastructure features implemented for Fase 3 light:
  1. Variantes de producto
  2. Reportes personalizables
  3. Cola de jobs push/email
  4. i18n persistente
  5. Búsqueda por imagen

Plus an API REST smoke test (FastAPI TestClient) covering health,
auth, productos, kpis, variantes, reportes, push, i18n.

Run:
    cd src && uv run python tests/test_phase3_features.py
"""

import asyncio
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

# Use an isolated DB
TMP_DB_DIR = Path(tempfile.mkdtemp(prefix="inv_p3_test_"))
SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

import config.settings as _settings  # noqa: E402

_settings.DATABASE_FILE = _settings.DATABASE_PATH / "inventario_p3test.db"
if _settings.DATABASE_FILE.exists():
    _settings.DATABASE_FILE.unlink()

from core.controller import InventarioController  # noqa: E402
from services.permissions import ALL_PERMISSION_KEYS  # noqa: E402
from utils.i18n import get_locale, set_locale  # noqa: E402

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
    ctrl.current_user = "admin"
    ctrl.current_user_role = "admin"
    ctrl.current_user_permissions = set(ALL_PERMISSION_KEYS)

    db = ctrl.db

    # ----- Seed base data -----
    p1 = db.crear_producto(
        codigo="P1",
        nombre="Camiseta",
        cantidad=100,
        precio=20.0,
        stock_min=10,
        categoria="Ropa",
    )
    p2 = db.crear_producto(
        codigo="P2",
        nombre="Pantalón",
        cantidad=50,
        precio=40.0,
        stock_min=5,
        categoria="Ropa",
    )
    # Seed one product image so image search has a candidate. We generate
    # a real PNG so PIL can decode it (PIL rejects fake/empty PNG headers).
    img_dir = SRC_DIR / "tests" / "_tmp_images"
    img_dir.mkdir(exist_ok=True)
    img_path = img_dir / "p1.png"
    img_path2 = img_dir / "p2.png"
    try:
        from PIL import Image

        Image.new("RGB", (16, 16), color=(255, 0, 0)).save(img_path)
        Image.new("RGB", (16, 16), color=(0, 255, 0)).save(img_path2)
    except Exception as e:
        print(f"WARNING: no se pudo crear imagen PIL: {e}")
        img_path.write_bytes(b"")
        img_path2.write_bytes(b"")
    with db._get_connection() as conn:
        conn.execute(
            "INSERT INTO imagenes_producto (producto_id, ruta, creado_en) VALUES (?, ?, datetime('now'))",
            (p1["id"], str(img_path)),
        )
        conn.execute(
            "INSERT INTO imagenes_producto (producto_id, ruta, creado_en) VALUES (?, ?, datetime('now'))",
            (p2["id"], str(img_path2)),
        )
        conn.commit()

    # ================================================================
    section("F3.1: Variantes de producto")
    # ================================================================
    try:
        ok, res = await ctrl.crear_variante(
            producto_id=p1["id"],
            sku="CAM-M-ROJO",
            atributos={"talla": "M", "color": "rojo"},
            cantidad=15,
        )
        record("Crear variante", ok and isinstance(res.get("id"), int), f"id={res.get('id')}")

        # Atributos vacíos: error
        ok2, res2 = await ctrl.crear_variante(
            producto_id=p1["id"],
            sku="CAM-X",
            atributos={},
            cantidad=0,
        )
        record("Variante sin atributos rechazada", not ok2, str(res2))

        # SKU duplicado: error
        ok3, res3 = await ctrl.crear_variante(
            producto_id=p1["id"],
            sku="CAM-M-ROJO",
            atributos={"talla": "L"},
            cantidad=0,
        )
        record("SKU duplicado rechazado", not ok3, str(res3))

        # Listar variantes del producto
        variantes = await ctrl.obtener_variantes(producto_id=p1["id"])
        record(
            "Listar variantes del producto",
            len(variantes) == 1
            and variantes[0]["sku"] == "CAM-M-ROJO"
            and variantes[0]["atributos_dict"]["talla"] == "M",
            f"count={len(variantes)}",
        )

        # Actualizar stock variante
        vid = variantes[0]["id"]
        ok4, _ = await ctrl.actualizar_stock_variante(vid, 25)
        record("Actualizar stock variante", ok4)

        v_post = await ctrl.obtener_variantes(producto_id=p1["id"])
        record(
            "Stock variante refleja el cambio",
            v_post[0]["cantidad"] == 25,
            f"cantidad={v_post[0]['cantidad']}",
        )

        # Eliminar variante (soft)
        ok5, _ = await ctrl.eliminar_variante(vid)
        record("Eliminar variante (soft)", ok5)
        v_activas = await ctrl.obtener_variantes(producto_id=p1["id"], solo_activas=True)
        record("Variante eliminada no aparece en solo_activas", len(v_activas) == 0)
    except Exception:
        record("F3.1 Variantes", False, traceback.format_exc())

    # ================================================================
    section("F3.2: Reportes personalizables")
    # ================================================================
    try:
        # Whitelist columnas
        mods = await ctrl.obtener_modulos_reporte()
        record(
            "Listar módulos de reporte disponibles",
            any(m["key"] == "productos" for m in mods),
            f"mods={[m['key'] for m in mods]}",
        )

        # Guardar plantilla
        ok, res = await ctrl.guardar_plantilla_reporte(
            nombre="Inventario bajo mínimo",
            modulo="productos",
            columnas=["codigo", "nombre", "cantidad", "stock_min"],
            filtros={"stock_min": 0},
            ordenado_por="cantidad",
        )
        record("Guardar plantilla de reporte", ok, f"id={res.get('id')}")

        # Columna inválida (inyección SQL evitada)
        ok2, res2 = await ctrl.guardar_plantilla_reporte(
            nombre="Mala",
            modulo="productos",
            columnas=["codigo", "; DROP TABLE productos;--"],
        )
        record("Columna inválida es rechazada", not ok2, str(res2))

        # Módulo inválido
        ok3, res3 = await ctrl.guardar_plantilla_reporte(
            nombre="Mala",
            modulo="usuarios",
            columnas=["id"],
        )
        record("Módulo inválido es rechazado", not ok3, str(res3))

        # Ejecutar reporte
        resultado = await ctrl.ejecutar_reporte(
            modulo="productos",
            columnas=["codigo", "nombre", "cantidad"],
            filtros={"stock_min": 10},  # >= 10
            ordenado_por="cantidad",
        )
        record(
            "Ejecutar reporte devuelve filas",
            "rows" in resultado
            and len(resultado["rows"]) >= 1
            and resultado["total"] == len(resultado["rows"]),
            f"total={resultado.get('total')}",
        )

        # Reporte con agrupación
        resultado2 = await ctrl.ejecutar_reporte(
            modulo="productos",
            columnas=["codigo", "categoria", "cantidad"],
            agrupacion="categoria",
        )
        record(
            "Reporte agrupado devuelve grupos",
            resultado2.get("grupos") is not None and "Ropa" in resultado2["grupos"],
            f"keys={list((resultado2.get('grupos') or {}).keys())}",
        )

        # Listar plantillas
        plantillas = await ctrl.obtener_plantillas_reporte()
        record(
            "Listar plantillas guardadas",
            len(plantillas) >= 1 and isinstance(plantillas[0]["columnas"], list),
            f"count={len(plantillas)}",
        )

        # Eliminar plantilla
        pid = plantillas[0]["id"]
        ok4, _ = await ctrl.eliminar_plantilla_reporte(pid)
        record("Eliminar plantilla", ok4)
    except Exception:
        record("F3.2 Reportes", False, traceback.format_exc())

    # ================================================================
    section("F3.3: Push / Email queue")
    # ================================================================
    try:
        # Encolar
        ok, res = await ctrl.encolar_push(
            tipo="low_stock",
            destinatario="admin@test.com",
            asunto="Stock bajo",
            cuerpo="Producto P2 bajo mínimo",
        )
        record("Encolar push", ok and isinstance(res.get("id"), int), f"id={res.get('id')}")

        # Encolar otro
        ok2, _ = await ctrl.encolar_push(
            tipo="sale",
            destinatario="x@y.com",
            asunto="Venta",
            cuerpo="Venta registrada",
        )
        record("Encolar segundo push", ok2)

        # Listar pendientes
        pendientes = await ctrl.obtener_jobs_push(estado="pendiente")
        record("Listar jobs pendientes", len(pendientes) == 2, f"count={len(pendientes)}")

        # Despachar (sin SMTP -> dry-run)
        desp = await ctrl.despachar_jobs_push(limit=10)
        record(
            "Despachar jobs (dry-run)",
            desp["procesados"] == 2 and desp["enviados"] == 2 and desp["fallidos"] == 0,
            f"desp={desp}",
        )

        # Listar enviados
        enviados = await ctrl.obtener_jobs_push(estado="enviado")
        record("Jobs marcados como enviados", len(enviados) == 2, f"count={len(enviados)}")

        # Despachar cuando ya no hay pendientes
        desp2 = await ctrl.despachar_jobs_push()
        record("Despachar con cola vacía", desp2["procesados"] == 0, f"desp={desp2}")

        # Despachar con sender que falla
        await ctrl.encolar_push(
            tipo="custom",
            destinatario="x@y.com",
            asunto="otro",
            cuerpo="otro",
        )

        def bad_sender(_cfg, a, c):
            return {"sent": False, "reason": "smtp down"}

        from services import phase3_db as p3

        # Manually invoke with the bad sender (controller signature doesn't
        # accept a sender override; we call the underlying function).
        result = p3.despachar_jobs_pendientes(db, sender=bad_sender, limit=5)
        record(
            "Sender fallido marca jobs como fallido",
            result["fallidos"] == 1 and result["enviados"] == 0,
            f"res={result}",
        )
    except Exception:
        record("F3.3 Push", False, traceback.format_exc())

    # ================================================================
    section("F3.4: i18n persistente")
    # ================================================================
    try:
        # Idioma por defecto = 'es'
        idioma_inicial = await ctrl.obtener_idioma_usuario("test_user")
        record("Idioma por defecto es 'es'", idioma_inicial == "es", f"got={idioma_inicial}")

        # Cambiar a 'en'
        ok, res = await ctrl.cambiar_idioma("test_user", "en")
        record("Cambiar idioma a 'en'", ok and get_locale() == "en", f"locale={get_locale()}")

        # Recuperar persistido
        idioma_post = await ctrl.obtener_idioma_usuario("test_user")
        record("Idioma persistido en DB", idioma_post == "en", f"got={idioma_post}")

        # Volver a 'es'
        ok2, _ = await ctrl.cambiar_idioma("test_user", "es")
        record("Volver a 'es'", ok2 and get_locale() == "es", f"locale={get_locale()}")

        # Idioma inválido rechazado
        ok3, res3 = await ctrl.cambiar_idioma("test_user", "fr")
        record("Idioma no soportado es rechazado", not ok3, str(res3))

        # Listar idiomas disponibles
        idiomas = await ctrl.obtener_idiomas_disponibles()
        record(
            "Listar idiomas disponibles",
            len(idiomas) == 2 and {i["code"] for i in idiomas} == {"es", "en"},
            f"idiomas={[i['code'] for i in idiomas]}",
        )

        # Restore default
        set_locale("es")
    except Exception:
        record("F3.4 i18n", False, traceback.format_exc())

    # ================================================================
    section("F3.5: Búsqueda por imagen")
    # ================================================================
    try:
        # Sin extractor: usa perceptual hash fallback (PIL genera phash por
        # brillo promedio; imagen roja y verde son distintas).
        res = await ctrl.buscar_por_imagen(str(img_path), top_k=3)
        record(
            "Buscar por imagen (fallback phash) devuelve resultados",
            isinstance(res, list) and len(res) >= 1,
            f"res={[r.get('codigo') for r in res]}",
        )

        # Con extractor custom que retorna vectores idénticos
        def extractor_dummy(path):
            return [0, 1, 0, 1, 0, 1]

        res2 = await ctrl.buscar_por_imagen(
            str(img_path),
            extractor=extractor_dummy,
            top_k=3,
        )
        record("Extractor custom funciona", isinstance(res2, list), f"count={len(res2)}")

        # Imagen inexistente
        res3 = await ctrl.buscar_por_imagen("/no/existe.png")
        record("Imagen inexistente devuelve lista vacía", res3 == [], f"res={res3}")
    except Exception:
        record("F3.5 Imagen", False, traceback.format_exc())

    # ================================================================
    section("API REST: smoke test")
    # ================================================================
    try:
        from fastapi.testclient import TestClient

        from api.rest import app

        client = TestClient(app)

        # Health
        r = client.get("/health")
        record(
            "GET /health",
            r.status_code == 200 and r.json()["status"] == "ok",
            f"status={r.status_code}",
        )

        # Auth missing
        r = client.get("/productos")
        record("GET /productos sin auth -> 401", r.status_code == 401, f"status={r.status_code}")

        # Auth via X-User header (sin password: trusted upstream)
        headers = {"X-User": "admin"}
        r = client.get("/productos", headers=headers)
        record(
            "GET /productos con X-User",
            r.status_code == 200 and isinstance(r.json(), list),
            f"status={r.status_code} count={len(r.json())}",
        )

        r = client.get("/kpis", headers=headers)
        record(
            "GET /kpis",
            r.status_code == 200 and "total_productos" in r.json(),
            f"status={r.status_code}",
        )

        r = client.get("/variantes", headers=headers)
        record("GET /variantes", r.status_code == 200, f"status={r.status_code}")

        r = client.get("/reportes/modulos", headers=headers)
        record("GET /reportes/modulos", r.status_code == 200, f"status={r.status_code}")

        # Ejecutar reporte vía API
        r = client.post(
            "/reportes/ejecutar",
            headers=headers,
            json={
                "modulo": "productos",
                "columnas": ["codigo", "nombre"],
                "filtros": {},
            },
        )
        record(
            "POST /reportes/ejecutar",
            r.status_code == 200 and "rows" in r.json(),
            f"status={r.status_code}",
        )

        # Push queue
        r = client.post(
            "/push/encolar",
            headers=headers,
            json={
                "tipo": "custom",
                "destinatario": "a@b.com",
                "asunto": "test",
                "cuerpo": "body",
            },
        )
        record("POST /push/encolar", r.status_code == 200, f"status={r.status_code}")

        r = client.get("/push/jobs", headers=headers)
        record(
            "GET /push/jobs",
            r.status_code == 200 and isinstance(r.json(), list),
            f"status={r.status_code} count={len(r.json())}",
        )

        # i18n
        r = client.post(
            "/i18n/cambiar",
            headers=headers,
            json={"usuario": "admin", "idioma": "en"},
        )
        record("POST /i18n/cambiar", r.status_code == 200, f"status={r.status_code}")

        r = client.get("/i18n/idiomas", headers=headers)
        record(
            "GET /i18n/idiomas",
            r.status_code == 200 and {x["code"] for x in r.json()} == {"es", "en"},
            f"status={r.status_code}",
        )

        # OpenAPI docs available
        r = client.get("/openapi.json")
        record("GET /openapi.json", r.status_code == 200, f"status={r.status_code}")

        set_locale("es")  # restore
    except Exception:
        record("API REST", False, traceback.format_exc())

    # Cleanup
    try:
        if _settings.DATABASE_FILE.exists():
            _settings.DATABASE_FILE.unlink()
        shutil.rmtree(TMP_DB_DIR, ignore_errors=True)
        shutil.rmtree(SRC_DIR / "tests" / "_tmp_images", ignore_errors=True)
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
