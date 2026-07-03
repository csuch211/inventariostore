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
from datetime import datetime
from pathlib import Path
from typing import Any

# Make src importable when uvicorn is launched from the repo root.
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from api.rate_limiter import RateLimitMiddleware
from config.settings import ACCESS_TOKEN_EXPIRE_MINUTES, CORS_ORIGINS, DEBUG
from core.controller import InventarioController
from services.database import DatabaseManager
from services.messaging import send_via_channel
from services.notifier import get_smtp_config, is_configured, send_custom_alert
from services.permissions import ALL_PERMISSION_KEYS, ROLE_DEFAULT_PERMISSIONS
from utils.crypto import encrypt_value
from utils.logger import setup_logger

logger = setup_logger(__name__)

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
    email: str = Field(max_length=200)


# ----- Dependency wiring -----

# Cached DatabaseManager instance (avoids re-initialization on every request)
_db_instance: DatabaseManager | None = None


def build_db() -> DatabaseManager:
    """Get or create a cached DatabaseManager instance."""
    inst = _db_instance
    if inst is None:
        inst = DatabaseManager()
        globals()['_db_instance'] = inst
    return inst


def build_controller() -> InventarioController:
    """Construct a controller with cached DB. Stateless wrt users."""
    return InventarioController()


def _get_auth_service():
    """Build an AuthService with DB access for JWT operations."""
    from services.auth import AuthService

    return AuthService(db=build_db())


def require_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str:
    """Resolve the active user from JWT Bearer token.

    All API endpoints require JWT authentication. The X-User header
    fallback has been removed for security.
    """
    auth_svc = _get_auth_service()

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization[7:]
    payload = auth_svc.verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload["sub"]


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
    except Exception as exc:
        logger.warning("Failed to resolve user perms, falling back to operador: %s", exc)
        return "operador", set(ROLE_DEFAULT_PERMISSIONS.get("operador", ALL_PERMISSION_KEYS))


# ----- App -----

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Inventariostore REST API",
    version="0.5.0",
    description="Read-mostly REST surface over the inventory controller.",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Health check that verifies database connectivity."""
    try:
        db = build_db()
        with db._get_connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        msg = f"Service unhealthy: {e}" if DEBUG else "Service unhealthy"
        raise HTTPException(status_code=503, detail=msg)


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
async def login(req: LoginRequest, request: Request):
    from api.rate_limiter import login_rate_limiter

    client_ip = request.client.host if request.client else "unknown"
    if not login_rate_limiter.check(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again in 1 minute.",
        )

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
        msg = str(e) if DEBUG else "Invalid credentials"
        raise HTTPException(status_code=401, detail=msg)


@app.post("/auth/register", status_code=201)
async def register(req: RegisterRequest):
    """Register a new user account. Account is inactive until email is verified."""
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

    # Validate email format
    valid_email, email_msg = Validator.validate_email(req.email)
    if not valid_email:
        raise HTTPException(status_code=422, detail=email_msg)

    # Validate password strength
    valid, msg = Validator.validate_password(req.password)
    if not valid:
        raise HTTPException(status_code=422, detail=msg)

    # Check if username already exists
    db = build_db()
    existing = db.obtener_usuario_por_username_full(req.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    # Create user as INACTIVE (requires email verification)
    try:
        password_hash = AuthService.hash_password(req.password)
        user_id = db.crear_usuario(
            username=req.username,
            password_hash=password_hash,
            nombre=req.nombre,
            rol="viewer",
            usuario="registration",
        )

        # Deactivate the user until email is verified
        with db._get_connection() as conn:
            conn.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (user_id,))
            conn.commit()

        # Assign default viewer role
        rol = db.obtener_rol_por_nombre("viewer")
        if rol:
            db.asignar_rol_a_usuario(user_id, rol["id"], usuario_actor="registration")

        # Create verification token and send email
        auth_svc = AuthService(db=db)
        token = auth_svc.create_email_verification_token(user_id)

        if token:
            # Send verification email if SMTP is configured

            cfg = get_smtp_config(db)
            if is_configured(cfg):
                send_custom_alert(
                    db,
                    subject="Verify Your Email - InventarioStore",
                    body=f"Hola {req.nombre},\n\n"
                    f"Gracias por registrarte en InventarioStore.\n\n"
                    f"Para activar tu cuenta, usa este token:\n\n"
                    f"{token}\n\n"
                    f"Este token expira en 24 horas.\n\n"
                    f"-- InventarioStore",
                )

        _logger.info(f"New user registered (pending verification): {req.username}")

        return {
            "message": "Registration successful. Please check your email to verify your account.",
            "username": req.username,
            "id": user_id,
            "email_sent": token is not None and is_configured(get_smtp_config(db)),
        }
    except Exception as e:
        _logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


# ----- Email Verification -----


class VerifyEmailRequest(BaseModel):
    token: str


@app.post("/auth/verify-email")
async def verify_email(req: VerifyEmailRequest):
    """Verify a user's email address and activate their account."""
    auth_svc = _get_auth_service()
    success = auth_svc.confirm_email(req.token)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    return {"message": "Email verified successfully. Your account is now active."}


@app.post("/auth/resend-verification")
async def resend_verification(req: ForgotPasswordRequest):
    """Resend email verification token. Always returns success to prevent enumeration."""

    db = build_db()
    user = db.obtener_usuario_por_username_full(req.username)

    if not user or user.get("activo") == 1:
        # User not found or already verified - return success anyway
        return {
            "message": "If the username exists and needs verification, a new link has been sent"
        }

    # Create new verification token
    auth_svc = _get_auth_service()
    token = auth_svc.create_email_verification_token(user["id"])

    if token:
        cfg = get_smtp_config(db)
        if is_configured(cfg):
            send_custom_alert(
                db,
                subject="Verify Your Email - InventarioStore",
                body=f"Hola {user.get('nombre', req.username)},\n\n"
                f"Usa este token para verificar tu cuenta:\n\n"
                f"{token}\n\n"
                f"Este token expira en 24 horas.\n\n"
                f"-- InventarioStore",
            )

    return {"message": "If the username exists and needs verification, a new link has been sent"}


# ----- Password Reset -----


class ForgotPasswordRequest(BaseModel):
    username: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=100)


@app.post("/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """Request a password reset token. Always returns success to prevent user enumeration."""

    auth_svc = _get_auth_service()

    # Create the reset token (returns None if user not found, but we don't reveal that)
    token = auth_svc.create_password_reset_token(req.username)

    # Always return success message to prevent user enumeration
    response = {"message": "If the username exists, a reset link has been sent"}

    # If token was created and email is configured, send the reset email
    if token:
        db = build_db()
        cfg = get_smtp_config(db)
        if is_configured(cfg):
            user = db.obtener_usuario_por_username_full(req.username)
            if user:
                reset_link = f"Use this token to reset your password: {token}"
                send_custom_alert(
                    db,
                    subject="Password Reset Request - InventarioStore",
                    body=f"Hola {user.get('nombre', req.username)},\n\n"
                    f"Recibimos una solicitud para restablecer tu contraseña.\n\n"
                    f"{reset_link}\n\n"
                    f"Este token expira en 1 hora.\n\n"
                    f"Si no solicitaste este cambio, ignora este mensaje.\n\n"
                    f"-- InventarioStore",
                )

    return response


# ----- SMTP Configuration -----


class SMTPConfigIn(BaseModel):
    host: str = Field(min_length=1, max_length=200)
    port: int = Field(ge=1, le=65535, default=587)
    user: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=200)
    from_email: str = Field(min_length=1, max_length=200)
    enabled: bool = False


@app.get("/smtp/config")
async def get_smtp_config_endpoint(user: str = Depends(require_user)):
    """Get current SMTP configuration (password masked)."""
    db = build_db()

    cfg = get_smtp_config(db)
    return {
        "host": cfg.get("host", ""),
        "port": int(cfg.get("port", 587)),
        "user": cfg.get("user", ""),
        "password": "***" if cfg.get("password") else "",
        "from_email": cfg.get("from_email", ""),
        "to_email": cfg.get("to_email", ""),
        "enabled": cfg.get("enabled", "no") == "si",
    }


@app.post("/smtp/config")
async def save_smtp_config(req: SMTPConfigIn, user: str = Depends(require_user)):
    """Save SMTP configuration."""
    db = build_db()
    try:
        db.guardar_config("smtp_host", req.host)
        db.guardar_config("smtp_port", str(req.port))
        db.guardar_config("smtp_user", req.user)
        db.guardar_config("smtp_password", encrypt_value(req.password))
        db.guardar_config("smtp_from_email", req.from_email)
        db.guardar_config("smtp_to_email", req.from_email)  # Default to from_email
        db.guardar_config("notify_low_stock", "si" if req.enabled else "no")

        logger.info(f"SMTP config updated by {user}")

        return {"message": "SMTP configuration saved successfully"}
    except Exception as e:
        logger.error(f"Failed to save SMTP config: {e}")
        raise HTTPException(status_code=500, detail="Failed to save SMTP configuration")


@app.post("/smtp/test")
async def test_smtp_connection(user: str = Depends(require_user)):
    """Test SMTP connection without sending an email."""
    db = build_db()

    cfg = get_smtp_config(db)
    if not is_configured(cfg):
        raise HTTPException(status_code=400, detail="SMTP not fully configured")

    try:
        import smtplib
        import ssl

        context = ssl.create_default_context()
        with smtplib.SMTP(cfg["host"], int(cfg["port"]), timeout=10) as server:
            server.starttls(context=context)
            server.login(cfg["user"], cfg["password"])

        return {"message": "SMTP connection successful", "host": cfg["host"], "port": cfg["port"]}
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(
            status_code=400, detail="SMTP authentication failed - check username/password"
        )
    except smtplib.SMTPConnectError:
        raise HTTPException(
            status_code=400, detail="Cannot connect to SMTP server - check host/port"
        )
    except Exception as e:
        msg = f"SMTP connection failed: {e}" if DEBUG else "SMTP connection failed"
        raise HTTPException(status_code=400, detail=msg)


@app.post("/smtp/send-test")
async def send_test_email(user: str = Depends(require_user)):
    """Send a test email to verify SMTP configuration."""
    db = build_db()

    result = send_custom_alert(
        db,
        subject="Test Email - InventarioStore",
        body=f"Hello!\n\n"
        f"This is a test email from InventarioStore.\n\n"
        f"If you received this, your SMTP configuration is working correctly.\n\n"
        f"Sent at: {datetime.now(datetime.UTC).isoformat()}\n\n"
        f"-- InventarioStore",
    )

    if result.get("sent"):
        return {"message": "Test email sent successfully", "to": result.get("to")}
    else:
        raise HTTPException(
            status_code=500, detail=f"Failed to send test email: {result.get('reason')}"
        )


# ----- WhatsApp Configuration -----


class WhatsAppConfigIn(BaseModel):
    api_key: str = Field(default="", max_length=500)
    phone_id: str = Field(default="", max_length=100)
    api_url: str = Field(default="https://graph.facebook.com/v18.0", max_length=300)
    enabled: bool = False


@app.get("/messaging/whatsapp/config")
async def get_whatsapp_config(user: str = Depends(require_user)):
    """Get WhatsApp configuration."""
    ctrl = InventarioController()
    ctrl.current_user = user
    cfg = await ctrl.obtener_config_whatsapp()
    return {
        "api_key": "***" if cfg.get("wa_api_key") else "",
        "phone_id": cfg.get("wa_phone_id", ""),
        "api_url": cfg.get("wa_api_url", "https://graph.facebook.com/v18.0"),
        "enabled": cfg.get("wa_enabled", "no") == "si",
    }


@app.post("/messaging/whatsapp/config")
async def save_whatsapp_config(req: WhatsAppConfigIn, user: str = Depends(require_user)):
    """Save WhatsApp configuration."""
    ctrl = InventarioController()
    ctrl.current_user = user
    config = {}
    # Only update keys that are non-empty (allow clearing)
    config["wa_api_key"] = req.api_key
    config["wa_phone_id"] = req.phone_id
    config["wa_api_url"] = req.api_url
    config["wa_enabled"] = "si" if req.enabled else "no"
    ok, result = await ctrl.guardar_config_whatsapp(config)
    if ok:
        return {"message": "WhatsApp configuration saved successfully"}
    raise HTTPException(status_code=500, detail=result.get("error", "Failed to save"))


@app.post("/messaging/whatsapp/test")
async def test_whatsapp(req: WhatsAppConfigIn, user: str = Depends(require_user)):
    """Send a test WhatsApp message."""
    ctrl = InventarioController()
    ctrl.current_user = user
    # Save temporarily, send test, then report
    config = {
        "wa_api_key": req.api_key,
        "wa_phone_id": req.phone_id,
        "wa_api_url": req.api_url,
        "wa_enabled": "si",
    }
    result = await send_via_channel("whatsapp", req.phone_id, "Test", "Test from InventarioStore", config)
    if result.get("sent"):
        return {"message": "WhatsApp test message sent", "message_id": result.get("message_id")}
    raise HTTPException(status_code=400, detail=result.get("reason", "Failed"))


# ----- Telegram Configuration -----


class TelegramConfigIn(BaseModel):
    bot_token: str = Field(default="", max_length=500)
    chat_id: str = Field(default="", max_length=100)
    enabled: bool = False


@app.get("/messaging/telegram/config")
async def get_telegram_config(user: str = Depends(require_user)):
    """Get Telegram configuration."""
    ctrl = InventarioController()
    ctrl.current_user = user
    cfg = await ctrl.obtener_config_telegram()
    return {
        "bot_token": "***" if cfg.get("tg_bot_token") else "",
        "chat_id": cfg.get("tg_chat_id", ""),
        "enabled": cfg.get("tg_enabled", "no") == "si",
    }


@app.post("/messaging/telegram/config")
async def save_telegram_config(req: TelegramConfigIn, user: str = Depends(require_user)):
    """Save Telegram configuration."""
    ctrl = InventarioController()
    ctrl.current_user = user
    config = {
        "tg_bot_token": req.bot_token,
        "tg_chat_id": req.chat_id,
        "tg_enabled": "si" if req.enabled else "no",
    }
    ok, result = await ctrl.guardar_config_telegram(config)
    if ok:
        return {"message": "Telegram configuration saved successfully"}
    raise HTTPException(status_code=500, detail=result.get("error", "Failed to save"))


@app.post("/messaging/telegram/test")
async def test_telegram(req: TelegramConfigIn, user: str = Depends(require_user)):
    """Send a test Telegram message."""
    ctrl = InventarioController()
    ctrl.current_user = user
    config = {
        "tg_bot_token": req.bot_token,
        "tg_chat_id": req.chat_id,
        "tg_enabled": "si",
    }
    result = await send_via_channel("telegram", req.chat_id, "Test", "<b>Test</b> from InventarioStore", config)
    if result.get("sent"):
        return {"message": "Telegram test message sent", "message_id": result.get("message_id")}
    raise HTTPException(status_code=400, detail=result.get("reason", "Failed"))


@app.post("/auth/reset-password")
async def reset_password(req: ResetPasswordRequest):
    """Reset a user's password using a valid reset token."""
    from utils.validators import Validator

    # Validate new password strength
    valid, msg = Validator.validate_password(req.new_password)
    if not valid:
        raise HTTPException(status_code=422, detail=msg)

    auth_svc = _get_auth_service()
    success = auth_svc.reset_password(req.token, req.new_password)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    return {"message": "Password reset successfully"}


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
