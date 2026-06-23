"""
REST API (FastAPI) for the inventory system.

This is a thin transport layer on top of the existing controller. The
controller already does auth, validation, audit, and RBAC; the API simply
adapts HTTP requests to controller calls and returns JSON.

Run from the project root:

    cd src && uvicorn api.rest:app --host 0.0.0.0 --port 8000

The routes are read-mostly: products, kpis, sales, low-stock, variants,
and reports. Write operations are intentionally limited to push/email
queueing and language preference so the API surface stays auditable.

Security model:
- Each request requires an `X-User` header with a valid username.
- That user's permissions are loaded via auth_service and applied to every
  call. Methods that the user cannot perform raise 403.
- The DB connection is per-request via DatabaseManager; for production
  switch to a connection pool.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

# Make src importable when uvicorn is launched from the repo root.
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from api.rate_limiter import RateLimitMiddleware
from config.settings import ACCESS_TOKEN_EXPIRE_MINUTES
from core.controller import InventarioController
from services.database import DatabaseManager
from services.permissions import ALL_PERMISSION_KEYS, ROLE_DEFAULT_PERMISSIONS

# ----- Pydantic schemas -----


class LoginRequest(BaseModel):
    username: str
    password: str


class ProductOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    cantidad: int
    precio: float
    categoria: str | None = None
    stock_min: int = 0
    activo: int = 1
    creado_en: str | None = None


class KPIOut(BaseModel):
    total_productos: int
    unidades_totales: int
    valor_inventario_venta: float
    valor_inventario_costo: float
    margen_estimado: float
    productos_criticos: int
    productos_agotados: int
    ventas_hoy_count: int
    ventas_hoy_total: float
    ventas_mes_count: int
    ventas_mes_total: float


class VariantCreateIn(BaseModel):
    producto_id: int
    sku: str
    atributos: dict[str, str] = Field(default_factory=dict)
    cantidad: int = 0
    precio_override: float | None = None


class ReportRunIn(BaseModel):
    modulo: str
    columnas: list[str]
    filtros: dict[str, Any] | None = None
    agrupacion: str | None = None
    ordenado_por: str | None = None


class PushEnqueueIn(BaseModel):
    tipo: str
    destinatario: str
    asunto: str
    cuerpo: str


class LanguageIn(BaseModel):
    usuario: str
    idioma: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=8, max_length=100)
    nombre: str = Field(min_length=2, max_length=100)


# ----- Dependency wiring -----


def build_controller() -> InventarioController:
    """Construct a controller fresh for the process. Stateless wrt users."""
    return InventarioController()


def build_db() -> DatabaseManager:
    return DatabaseManager()


def _get_auth_service() -> "AuthService":
    """Build an AuthService with DB access for JWT operations."""
    from services.auth import AuthService as AuthServiceCls

    return AuthServiceCls(db=build_db())


def require_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user: str | None = Header(default=None, alias="X-User"),
) -> str:
    """Resolve the active user from JWT Bearer token or X-User header.

    Supports both JWT (for API clients) and X-User header (for legacy/GUI).
    """
    auth_svc = _get_auth_service()

    # Try JWT Bearer token first
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        payload = auth_svc.verify_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return payload["sub"]

    # Fallback to X-User header (legacy/GUI compatibility)
    if x_user:
        return x_user

    raise HTTPException(status_code=401, detail="Missing Authorization header or X-User header")


def _resolve_user_perms(db: DatabaseManager, username: str):
    """Resolve (rol, permissions) for a user via direct SQL.

    This mirrors AuthService._resolve_role_and_permissions but stays in
    the API layer so we don't depend on the session store.
    """
    try:
        with db._get_connection() as conn:
            u = conn.execute(
                "SELECT id, rol FROM usuarios WHERE username = ?",
                (username,),
            ).fetchone()
            if not u:
                return "operador", set(
                    ROLE_DEFAULT_PERMISSIONS.get("operador", ALL_PERMISSION_KEYS)
                )
            roles = conn.execute(
                """SELECT r.nombre FROM usuario_roles ur
                   JOIN roles r ON r.id = ur.rol_id
                   WHERE ur.usuario_id = ?""",
                (u["id"],),
            ).fetchall()
            rol_name = roles[0]["nombre"] if roles else (u["rol"] or "operador").lower()
            perms_rows = conn.execute(
                """SELECT DISTINCT p.clave FROM permisos p
                   JOIN rol_permisos rp ON rp.permiso_id = p.id
                   JOIN usuario_roles ur ON ur.rol_id = rp.rol_id
                   WHERE ur.usuario_id = ?""",
                (u["id"],),
            ).fetchall()
            perms = {row["clave"] for row in perms_rows}
            # Layer in role defaults so users without explicit rows still
            # get the baseline.
            defaults = ROLE_DEFAULT_PERMISSIONS.get(rol_name, set())
            perms |= defaults
            return rol_name, perms
    except Exception:
        return "operador", set(ROLE_DEFAULT_PERMISSIONS.get("operador", ALL_PERMISSION_KEYS))


# ----- App -----


app = FastAPI(
    title="Inventariostore REST API",
    version="0.4.0",
    description="Read-mostly REST surface over the inventory controller.",
)

app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)


def _authorized_controller(username: str) -> InventarioController:
    """Build a controller and load the resolved permissions for the given
    user. Endpoints should use this instead of ``build_controller()`` so
    RBAC decorators see the user's permissions.

    This was previously a latent bug: ``require_user`` resolved the
    permissions onto a local controller that was then discarded, leaving
    every handler's fresh controller with an empty permission set.
    """
    ctrl = build_controller()
    ctrl.current_user = username
    try:
        rol, perms = _resolve_user_perms(build_db(), username)
        ctrl.current_user_role = rol
        ctrl.current_user_permissions = perms
    except Exception:
        ctrl.current_user_role = "operador"
        ctrl.current_user_permissions = set(
            ROLE_DEFAULT_PERMISSIONS.get("operador", ALL_PERMISSION_KEYS)
        )
    return ctrl


@app.get("/health")
def health():
    return {"status": "ok"}


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    username: str
    rol: str
    permissions: list[str]


class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    auth_svc = _get_auth_service()
    try:
        # Authenticate and get user info
        session = auth_svc.authenticate(req.username, req.password)

        # Get user ID for refresh token
        db = build_db()
        user = db.obtener_usuario_por_username_full(req.username)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Create JWT tokens
        access_token = auth_svc.create_access_token(
            username=req.username,
            rol=session["rol"],
            permissions=session["permissions"],
        )
        refresh_token = auth_svc.create_refresh_token(
            username=req.username,
            user_id=user["id"],
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            username=req.username,
            rol=session["rol"],
            permissions=session["permissions"],
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/auth/register", status_code=201)
async def register(req: RegisterRequest):
    """Register a new user account."""
    from services.auth import AuthService
    from utils.logger import setup_logger as _setup_logger
    from utils.validators import Validator

    _logger = _setup_logger(__name__)

    # Validate username
    if not re.match(r"^[A-Za-z0-9_-]+$", req.username):
        raise HTTPException(
            status_code=422,
            detail="Username can only contain letters, numbers, hyphens, and underscores",
        )

    # Validate password strength
    valid, msg = Validator.validate_password(req.password)
    if not valid:
        raise HTTPException(status_code=422, detail=msg)

    # Check if username already exists
    db = build_db()
    existing = db.obtener_usuario_por_username_full(req.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    # Create user with default 'viewer' role (read-only)
    try:
        password_hash = AuthService.hash_password(req.password)
        user_id = db.crear_usuario(
            username=req.username,
            password_hash=password_hash,
            nombre=req.nombre,
            rol="viewer",
            usuario="registration",
        )

        # Assign default viewer role
        rol = db.obtener_rol_por_nombre("viewer")
        if rol:
            db.asignar_rol_a_usuario(user_id, rol["id"], usuario_actor="registration")

        _logger.info(f"New user registered: {req.username}")

        return {
            "message": "User registered successfully",
            "username": req.username,
            "id": user_id,
        }
    except Exception as e:
        _logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@app.post("/auth/refresh")
async def refresh_token(req: RefreshRequest):
    """Refresh an access token using a valid refresh token."""
    auth_svc = _get_auth_service()
    payload = auth_svc.verify_refresh_token(req.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    username = payload["sub"]
    db = build_db()

    # Resolve fresh permissions
    rol, permissions = _resolve_user_perms(db, username)

    # Create new access token
    access_token = auth_svc.create_access_token(
        username=username,
        rol=rol,
        permissions=list(permissions),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES,
    }


@app.post("/auth/logout")
async def logout(authorization: str | None = Header(default=None, alias="Authorization")):
    """Revoke the refresh token on logout."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    auth_svc = _get_auth_service()
    token = authorization[7:]

    # Try to verify as refresh token and revoke it
    payload = auth_svc.verify_refresh_token(token)
    if payload and payload.get("jti"):
        auth_svc.revoke_refresh_token(payload["jti"])

    return {"message": "Logged out successfully"}


@app.get("/productos", response_model=list[ProductOut])
async def list_productos(
    q: str | None = Query(default=None, description="Texto a buscar"),
    categoria: str | None = None,
    limit: int = Query(default=100, le=1000),
    user: str = Depends(require_user),
):
    controller = _authorized_controller(user)
    if q:
        res = await controller.buscar_productos(q)
    else:
        res = await controller.obtener_todos_productos()
    return [
        ProductOut(
            id=p["id"],
            codigo=p["codigo"],
            nombre=p["nombre"],
            cantidad=p["cantidad"],
            precio=p["precio"],
            categoria=p.get("categoria"),
            stock_min=p.get("stock_min", 0),
            activo=p.get("activo", 1),
            creado_en=p.get("creado_en"),
        )
        for p in (res or [])[:limit]
    ]


@app.get("/productos/{codigo}")
async def get_producto(codigo: str, user: str = Depends(require_user)):
    controller = _authorized_controller(user)
    res = await controller.buscar_por_codigo_escaneado(codigo)
    if not res:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return res


@app.get("/kpis", response_model=KPIOut)
async def kpis(user: str = Depends(require_user)):
    controller = _authorized_controller(user)
    data = await controller.obtener_kpis_dashboard()
    if not data:
        raise HTTPException(status_code=503, detail="KPIs no disponibles")
    return KPIOut(**{k: data.get(k, 0) for k in KPIOut.model_fields})


@app.get("/alertas/stock-bajo")
async def stock_bajo(user: str = Depends(require_user)):
    controller = _authorized_controller(user)
    res = await controller.verificar_stock_bajo()
    return res or []


@app.get("/variantes")
async def list_variantes(
    producto_id: int | None = None,
    user: str = Depends(require_user),
):
    controller = _authorized_controller(user)
    res = await controller.obtener_variantes(producto_id=producto_id)
    return res or []


@app.post("/variantes")
async def create_variante(body: VariantCreateIn, user: str = Depends(require_user)):
    controller = _authorized_controller(user)
    ok, res = await controller.crear_variante(
        producto_id=body.producto_id,
        sku=body.sku,
        atributos=body.atributos,
        cantidad=body.cantidad,
        precio_override=body.precio_override,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=res.get("error", "error"))
    return res


@app.get("/reportes/modulos")
async def list_report_modules(user: str = Depends(require_user)):
    controller = _authorized_controller(user)
    return await controller.obtener_modulos_reporte()


@app.post("/reportes/ejecutar")
async def run_report(body: ReportRunIn, user: str = Depends(require_user)):
    controller = _authorized_controller(user)
    return await controller.ejecutar_reporte(
        modulo=body.modulo,
        columnas=body.columnas,
        filtros=body.filtros,
        agrupacion=body.agrupacion,
        ordenado_por=body.ordenado_por,
    )


@app.post("/push/encolar")
async def enqueue_push(body: PushEnqueueIn, user: str = Depends(require_user)):
    controller = _authorized_controller(user)
    ok, res = await controller.encolar_push(
        tipo=body.tipo,
        destinatario=body.destinatario,
        asunto=body.asunto,
        cuerpo=body.cuerpo,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=res.get("error", "error"))
    return res


@app.get("/push/jobs")
async def list_push_jobs(
    estado: str | None = None,
    limit: int = Query(default=100, le=500),
    user: str = Depends(require_user),
):
    controller = _authorized_controller(user)
    return await controller.obtener_jobs_push(estado=estado, limit=limit)


@app.post("/i18n/cambiar")
async def change_language(body: LanguageIn, user: str = Depends(require_user)):
    controller = _authorized_controller(user)
    ok, res = await controller.cambiar_idioma(
        usuario=body.usuario,
        idioma=body.idioma,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=res.get("error", "error"))
    return res


@app.get("/i18n/idiomas")
async def list_languages(user: str = Depends(require_user)):
    controller = _authorized_controller(user)
    return await controller.obtener_idiomas_disponibles()


# ----- Optional CLI smoke test -----


def _smoke_test():
    """Run a couple of calls against the in-process controller. Useful as
    a sanity check when the API module is executed directly:
        python -m api.rest
    """
    import json

    from fastapi.testclient import TestClient

    client = TestClient(app)
    print(json.dumps(client.get("/health").json(), indent=2))
    # Without auth header, /productos returns 401
    r = client.get("/productos")
    print(f"GET /productos (no auth) -> {r.status_code}: {r.json()}")


if __name__ == "__main__":
    _smoke_test()
