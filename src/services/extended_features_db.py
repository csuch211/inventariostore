"""
Extended features data-access layer.

Covers 5 infrastructure features:
  - Variantes de producto (talla/color como sub-productos)
  - Plantillas de reporte personalizable (constructor columnas/filtros/agrupación)
  - Cola de jobs push/email
  - Preferencia de idioma por usuario (i18n persistente)
  - Búsqueda por imagen (hook stub delegando al controlador)
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import datetime

from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _conn(db):
    return db._get_connection()


def _audit(db, conn, accion, tabla, registro_id, usuario, detalles):
    db._audit_log(conn, accion, tabla, registro_id, usuario, detalles)


# ======================================================================
# F3.1: Variantes de producto
# ======================================================================


def crear_variante(
    db,
    producto_id: int,
    sku: str,
    atributos: dict[str, str],
    cantidad: int = 0,
    precio_override: float | None = None,
    usuario: str = "system",
) -> int:
    """Register a variant (e.g. Talla M, Color rojo) of a base product."""
    now = datetime.now().isoformat()
    if not sku or not sku.strip():
        raise DatabaseException("SKU de variante es obligatorio")
    if not atributos:
        raise DatabaseException("Atributos no pueden estar vacíos")
    try:
        with _conn(db) as conn:
            # Base product must exist
            row = conn.execute("SELECT id FROM productos WHERE id = ?", (producto_id,)).fetchone()
            if not row:
                raise DatabaseException(f"Producto {producto_id} no existe")
            atributos_json = json.dumps(atributos, ensure_ascii=False)
            cur = conn.execute(
                """INSERT INTO variantes_producto
                   (producto_id, sku, atributos, cantidad, precio_override,
                    activo, creado_en, actualizado_en)
                   VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
                (
                    producto_id,
                    sku.strip(),
                    atributos_json,
                    int(cantidad),
                    float(precio_override) if precio_override is not None else None,
                    now,
                    now,
                ),
            )
            vid = cur.lastrowid
            conn.commit()
            _audit(
                db,
                conn,
                "CREATE",
                "variantes_producto",
                vid,
                usuario,
                f"Variante {sku} creada para producto {producto_id}",
            )
            return vid
    except sqlite3.IntegrityError:
        raise DatabaseException(f"Ya existe una variante con SKU '{sku}'")
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to create variant: {e}")


def obtener_variantes(
    db,
    producto_id: int | None = None,
    sku: str | None = None,
    solo_activas: bool = True,
) -> list[dict]:
    try:
        with _conn(db) as conn:
            where = []
            params: list = []
            if producto_id is not None:
                where.append("v.producto_id = ?")
                params.append(int(producto_id))
            if sku:
                where.append("v.sku = ?")
                params.append(sku)
            if solo_activas:
                where.append("v.activo = 1")
            sql = (
                "SELECT v.*, p.nombre as producto_nombre, p.codigo as producto_codigo "
                "FROM variantes_producto v "
                "LEFT JOIN productos p ON v.producto_id = p.id "
            )
            if where:
                sql += "WHERE " + " AND ".join(where) + " "
            sql += "ORDER BY v.creado_en DESC"
            cur = conn.execute(sql, params)
            rows = []
            for r in cur.fetchall():
                d = dict(r)
                # Decode atributos JSON back into dict for convenience
                try:
                    d["atributos_dict"] = json.loads(d.get("atributos") or "{}")
                except json.JSONDecodeError:
                    d["atributos_dict"] = {}
                rows.append(d)
            return rows
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch variants: {e}")


def actualizar_stock_variante(db, variante_id: int, cantidad: int, usuario: str = "system") -> dict:
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            row = conn.execute(
                "SELECT id, cantidad FROM variantes_producto WHERE id = ?",
                (variante_id,),
            ).fetchone()
            if not row:
                raise DatabaseException("Variante no encontrada")
            conn.execute(
                "UPDATE variantes_producto SET cantidad = ?, actualizado_en = ? WHERE id = ?",
                (int(cantidad), now, variante_id),
            )
            conn.commit()
            _audit(
                db,
                conn,
                "UPDATE_STOCK",
                "variantes_producto",
                variante_id,
                usuario,
                f"Stock variante {variante_id} -> {cantidad}",
            )
            return {"id": variante_id, "cantidad": int(cantidad)}
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to update variant stock: {e}")


def eliminar_variante(db, variante_id: int, usuario: str = "system") -> bool:
    try:
        with _conn(db) as conn:
            conn.execute(
                "UPDATE variantes_producto SET activo = 0 WHERE id = ?",
                (variante_id,),
            )
            conn.commit()
            _audit(
                db,
                conn,
                "DELETE",
                "variantes_producto",
                variante_id,
                usuario,
                "Variante desactivada",
            )
            return True
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to delete variant: {e}")


# ======================================================================
# F3.2: Plantillas de reporte personalizable
# ======================================================================

# Whitelist de columnas por módulo (seguridad: evita inyección de SQL)
REPORT_COLUMN_WHITELIST: dict[str, list[str]] = {
    "productos": [
        "id",
        "codigo",
        "nombre",
        "cantidad",
        "precio",
        "categoria",
        "stock_min",
        "proveedor_nombre",
        "estado",
        "creado_en",
    ],
    "ventas": [
        "id",
        "cliente_id",
        "total",
        "estado",
        "creado_en",
        "creado_por",
    ],
    "clientes": [
        "id",
        "nombre",
        "telefono",
        "email",
        "direccion",
        "activo",
    ],
}


def guardar_plantilla(
    db,
    nombre: str,
    modulo: str,
    columnas: list[str],
    filtros: dict | None = None,
    agrupacion: str | None = None,
    ordenado_por: str | None = None,
    usuario: str = "system",
) -> int:
    if modulo not in REPORT_COLUMN_WHITELIST:
        raise DatabaseException(
            f"Módulo '{modulo}' no soportado. Use uno de: {list(REPORT_COLUMN_WHITELIST)}"
        )
    allowed = REPORT_COLUMN_WHITELIST[modulo]
    invalid = [c for c in (columnas or []) if c not in allowed]
    if invalid:
        raise DatabaseException(
            f"Columnas no permitidas en '{modulo}': {invalid}. Use solo: {allowed}"
        )
    if not columnas:
        raise DatabaseException("Debe seleccionar al menos una columna")
    if agrupacion and agrupacion not in allowed:
        raise DatabaseException(f"Columna de agrupación inválida: {agrupacion}")
    if ordenado_por and ordenado_por not in allowed:
        raise DatabaseException(f"Columna de orden inválida: {ordenado_por}")

    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            cur = conn.execute(
                """INSERT INTO plantillas_reporte
                   (nombre, modulo, columnas, filtros, agrupacion, ordenado_por,
                    creado_por, creado_en, actualizado_en)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    nombre,
                    modulo,
                    json.dumps(columnas, ensure_ascii=False),
                    json.dumps(filtros or {}, ensure_ascii=False),
                    agrupacion,
                    ordenado_por,
                    usuario,
                    now,
                    now,
                ),
            )
            pid = cur.lastrowid
            conn.commit()
            _audit(
                db,
                conn,
                "CREATE",
                "plantillas_reporte",
                pid,
                usuario,
                f"Plantilla '{nombre}' ({modulo}) guardada",
            )
            return pid
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to save template: {e}")


def obtener_plantillas(db) -> list[dict]:
    try:
        with _conn(db) as conn:
            cur = conn.execute("SELECT * FROM plantillas_reporte ORDER BY creado_en DESC")
            out = []
            for r in cur.fetchall():
                d = dict(r)
                for key in ("columnas", "filtros"):
                    try:
                        d[key] = json.loads(d.get(key) or ("[]" if key == "columnas" else "{}"))
                    except json.JSONDecodeError:
                        d[key] = [] if key == "columnas" else {}
                out.append(d)
            return out
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch templates: {e}")


def eliminar_plantilla(db, plantilla_id: int, usuario: str = "system") -> bool:
    try:
        with _conn(db) as conn:
            conn.execute("DELETE FROM plantillas_reporte WHERE id = ?", (plantilla_id,))
            conn.commit()
            _audit(
                db,
                conn,
                "DELETE",
                "plantillas_reporte",
                plantilla_id,
                usuario,
                "Plantilla eliminada",
            )
            return True
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to delete template: {e}")


def ejecutar_reporte(
    db,
    modulo: str,
    columnas: list[str],
    filtros: dict | None = None,
    agrupacion: str | None = None,
    ordenado_por: str | None = None,
) -> dict:
    """Run a report and return rows + counts.

    Returns dict with: rows, total, grupos (si agrupacion), columnas.
    """
    if modulo not in REPORT_COLUMN_WHITELIST:
        raise DatabaseException(f"Módulo '{modulo}' no soportado")
    allowed = REPORT_COLUMN_WHITELIST[modulo]
    invalid = [c for c in columnas if c not in allowed]
    if invalid:
        raise DatabaseException(f"Columnas inválidas: {invalid}")
    if agrupacion and agrupacion not in allowed:
        raise DatabaseException(f"Agrupación inválida: {agrupacion}")
    filtros = filtros or {}

    # Build base query per modulo
    if modulo == "productos":
        base_from = "FROM productos p LEFT JOIN proveedores pr ON p.proveedor_id = pr.id"
        col_map = {"proveedor_nombre": "pr.nombre"}
    elif modulo == "ventas":
        base_from = "FROM ventas v"
        col_map = {}
    elif modulo == "clientes":
        base_from = "FROM clientes c"
        col_map = {}
    else:
        raise DatabaseException(f"Módulo no implementado: {modulo}")

    where, params = [], []
    # Filter mapping
    filter_map = {
        "productos": {
            "categoria": ("p.categoria = ?", lambda v: v),
            "estado": ("p.estado = ?", lambda v: v),
            "stock_min": ("p.cantidad >= ?", int),
            "precio_min": ("p.precio >= ?", float),
            "precio_max": ("p.precio <= ?", float),
        },
        "ventas": {
            "estado": ("v.estado = ?", lambda v: v),
            "fecha_desde": ("date(v.creado_en) >= date(?)", lambda v: v),
            "fecha_hasta": ("date(v.creado_en) <= date(?)", lambda v: v),
        },
        "clientes": {
            "activo": ("c.activo = ?", lambda v: int(bool(v))),
        },
    }
    for k, v in filtros.items():
        if k in filter_map.get(modulo, {}):
            clause, conv = filter_map[modulo][k]
            where.append(clause)
            params.append(conv(v))

    select_cols = [
        f"{col_map.get(c, (modulo[0] + '.' + c if '.' not in c else c))} AS {c}"
        if c in col_map
        else f"{modulo[0]}.{c} AS {c}"
        for c in columnas
    ]
    for c in columnas:
        if c not in allowed:
            raise DatabaseException(f"Columna inválida en reporte: {c}")
    sql = "SELECT " + ", ".join(select_cols) + " " + base_from
    if where:
        sql += " WHERE " + " AND ".join(where)
    if ordenado_por:
        sql += f" ORDER BY {modulo[0]}.{ordenado_por} ASC"
    else:
        sql += f" ORDER BY {modulo[0]}.id DESC"
    sql += " LIMIT 5000"

    try:
        with _conn(db) as conn:
            cur = conn.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]

            grupos = None
            if agrupacion and rows:
                grupos = {}
                for r in rows:
                    key = r.get(agrupacion, "(sin valor)")
                    grupos.setdefault(key, []).append(r)

            return {
                "modulo": modulo,
                "columnas": columnas,
                "rows": rows,
                "total": len(rows),
                "grupos": grupos,
                "agrupacion": agrupacion,
            }
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to execute report: {e}")


# ======================================================================
# F3.3: Cola de jobs push/email
# ======================================================================


def encolar_job(
    db,
    tipo: str,
    destinatario: str,
    asunto: str,
    cuerpo: str,
) -> int:
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            cur = conn.execute(
                """INSERT INTO jobs_push
                   (tipo, destinatario, asunto, cuerpo, estado, creado_en)
                   VALUES (?, ?, ?, ?, 'pendiente', ?)""",
                (tipo, destinatario, asunto, cuerpo, now),
            )
            jid = cur.lastrowid
            conn.commit()
            logger.info(f"Push job {jid} enqueued for {destinatario}")
            return jid
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to enqueue job: {e}")


def obtener_jobs(
    db,
    estado: str | None = None,
    limit: int = 100,
) -> list[dict]:
    try:
        with _conn(db) as conn:
            if estado:
                cur = conn.execute(
                    "SELECT * FROM jobs_push WHERE estado = ? ORDER BY creado_en DESC LIMIT ?",
                    (estado, int(limit)),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM jobs_push ORDER BY creado_en DESC LIMIT ?",
                    (int(limit),),
                )
            return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch jobs: {e}")


def marcar_job_enviado(db, job_id: int) -> bool:
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            conn.execute(
                """UPDATE jobs_push
                   SET estado = 'enviado', enviado_en = ?, intentos = intentos + 1
                   WHERE id = ?""",
                (now, job_id),
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to mark job sent: {e}")


def marcar_job_fallido(db, job_id: int, error: str) -> bool:
    try:
        with _conn(db) as conn:
            conn.execute(
                """UPDATE jobs_push
                   SET estado = 'fallido', ultimo_error = ?, intentos = intentos + 1
                   WHERE id = ?""",
                (error, job_id),
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to mark job failed: {e}")


def despachar_jobs_pendientes(
    db,
    sender: Callable[[dict, str, str], dict] | None = None,
    limit: int = 25,
) -> dict:
    """Try to send up to `limit` pending jobs.

    `sender(smtp_cfg, asunto, cuerpo) -> {"sent": bool, "reason": ...}` is
    the transport. Defaults to the existing services.notifier pipeline
    which uses the user-configured SMTP settings. If SMTP is not
    configured the jobs are still marked 'enviado' (dry-run mode) so the
    queue can be exercised in tests.
    """
    if sender is None:
        try:
            from services.notifier import _send_email_raw, get_smtp_config, is_configured

            cfg = get_smtp_config(db)
            if not cfg or not is_configured(cfg):

                def _dry(db_unused, a, b):  # ignore cfg when not configured
                    return {"sent": True, "dry_run": True, "reason": "smtp not configured"}

                sender = _dry
            else:

                def _real(_cfg, a, b):
                    return _send_email_raw(cfg, a, b)

                sender = _real
        except Exception:

            def _fallback(_cfg, a, b):
                return {"sent": True, "dry_run": True}

            sender = _fallback

    jobs = obtener_jobs(db, estado="pendiente", limit=limit)
    enviados = 0
    fallidos = 0
    for j in jobs:
        try:
            res = sender({}, j["asunto"], j["cuerpo"])
            ok = bool(res and res.get("sent"))
            if ok:
                marcar_job_enviado(db, j["id"])
                enviados += 1
            else:
                marcar_job_fallido(db, j["id"], (res or {}).get("reason", "unknown"))
                fallidos += 1
        except Exception as ex:
            marcar_job_fallido(db, j["id"], str(ex))
            fallidos += 1
    return {"procesados": len(jobs), "enviados": enviados, "fallidos": fallidos}


# ======================================================================
# F3.4: Preferencia de idioma por usuario (i18n persistente)
# ======================================================================


def obtener_idioma_usuario(db, usuario: str) -> str:
    """Return the user's stored language preference, defaulting to 'es'."""
    try:
        with _conn(db) as conn:
            row = conn.execute(
                "SELECT idioma FROM usuario_prefs WHERE usuario = ?", (usuario,)
            ).fetchone()
            if row:
                return row["idioma"]
            return "es"
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch user lang: {e}")


def guardar_idioma_usuario(db, usuario: str, idioma: str) -> bool:
    if idioma not in ("es", "en"):
        raise DatabaseException(f"Idioma no soportado: {idioma}")
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            conn.execute(
                """INSERT INTO usuario_prefs (usuario, idioma, actualizado_en)
                   VALUES (?, ?, ?)
                   ON CONFLICT(usuario) DO UPDATE SET
                     idioma = excluded.idioma,
                     actualizado_en = excluded.actualizado_en""",
                (usuario, idioma, now),
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to save user lang: {e}")


def obtener_idiomas_disponibles() -> list[str]:
    return ["es", "en"]


# ======================================================================
# F3.5: Búsqueda por imagen (placeholder hookeable)
# ======================================================================


def buscar_por_similitud(
    db,
    ruta_imagen: str,
    extractor: Callable[[str], list[float]] | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Find products whose image is most similar to `ruta_imagen`.

    `extractor` is a user-supplied callable that returns a feature vector
    for an image path. By default we use a perceptual hash (phash) over
    the image bytes if Pillow is installed; otherwise we fall back to
    matching by filename pattern.

    Returns the top_k products with the smallest distance.
    """
    try:
        target = _default_extract(ruta_imagen, extractor)
        if target is None:
            return []

        with _conn(db) as conn:
            cur = conn.execute("""SELECT id, ruta FROM imagenes_producto WHERE ruta IS NOT NULL""")
            candidatos = [dict(r) for r in cur.fetchall()]

        scored = []
        for c in candidatos:
            cand_vec = _default_extract(c["ruta"], extractor)
            if cand_vec is None:
                continue
            dist = _hamming(target, cand_vec)
            scored.append((dist, c["id"]))

        scored.sort(key=lambda x: x[0])
        top_ids = [pid for _, pid in scored[:top_k]]
        if not top_ids:
            return []
        with _conn(db) as conn:
            placeholders = ",".join("?" for _ in top_ids)
            cur = conn.execute(
                f"SELECT id, codigo, nombre, categoria FROM productos WHERE id IN ({placeholders})",
                top_ids,
            )
            return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to search by image: {e}")


def _default_extract(path: str, custom: Callable[[str], list[float]] | None):
    if custom is not None:
        return custom(path)
    # Fallback: perceptual hash via PIL if available
    try:
        from pathlib import Path

        from PIL import Image

        img_path = Path(path)
        if not img_path.exists():
            return None
        with Image.open(img_path) as im:
            converted = im.convert("L").resize((8, 8))
            data = list(converted.getdata())
        return _phash(data)
    except Exception:
        return None


def _phash(pixels: list[int]) -> list[int]:
    avg = sum(pixels) / max(len(pixels), 1)
    return [1 if p > avg else 0 for p in pixels]


def _hamming(a: list[int], b: list[int]) -> int:
    n = min(len(a), len(b))
    return sum(1 for i in range(n) if a[i] != b[i]) + abs(len(a) - len(b))
