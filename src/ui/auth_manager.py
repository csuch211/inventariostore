"""
Authentication UI: login screen, register, forgot password, logout.

All functions receive the AppView instance as first parameter.
"""

import asyncio
import contextlib
import time
from collections import defaultdict

import flet as ft

from config.settings import APP_NAME, APP_VERSION
from core.theme_manager import theme_manager
from ui.components import FormField, SnackBarHelper
from ui.typography import T
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)

_login_attempts: dict = defaultdict(list)
_MAX_LOGIN_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 300  # 5 minutes


def _check_login_rate_limit(username: str) -> bool:
    now = time.time()
    attempts = _login_attempts[username]
    _login_attempts[username] = [t for t in attempts if now - t < _LOGIN_WINDOW_SECONDS]
    if len(_login_attempts[username]) >= _MAX_LOGIN_ATTEMPTS:
        return False
    _login_attempts[username].append(now)
    return True


async def show_login_screen(app_view) -> None:
    """Display login screen with validation."""
    app_view._current_route = "dashboard"
    C = theme_manager.palette(page=app_view.page)
    username_field = FormField.create_text_field(
        label="Usuario",
        hint="Ingresa tu usuario",
        required=True,
        autofocus=True,
    )
    error_text = ft.Text("", color=C["accent"], size=12)

    async def handle_login(e):
        error_text.value = ""
        username = username_field.value.strip()
        password = password_field.value

        if not _check_login_rate_limit(username):
            error_text.value = "Demasiados intentos. Intenta de nuevo en 5 minutos."
            app_view.page.update()
            return

        if not username:
            error_text.value = "El usuario es requerido"
            app_view.page.update()
            return

        if not password:
            error_text.value = "La contraseña es requerida"
            app_view.page.update()
            return

        if len(password) < 6:
            error_text.value = "La contraseña debe tener al menos 6 caracteres"
            app_view.page.update()
            return

        try:
            login_btn.disabled = True
            app_view.show_loading()

            session = await app_view.controller.login(username, password)
            logger.info(f"login flow: controller.login OK for {username}")
            app_view.current_user = username
            app_view.current_token = session.get("token")

            theme_mode = await app_view.controller.obtener_tema_usuario()
            logger.info(f"login flow: theme fetched ({theme_mode})")
            app_view.page.theme_mode = (
                ft.ThemeMode.DARK if theme_mode == "dark" else ft.ThemeMode.LIGHT
            )
            C_inner = theme_manager.palette(page=app_view.page)
            app_view.page.bgcolor = C_inner["background"]

            SnackBarHelper.success(app_view.page, f"¡Bienvenido, {username}!")
            logger.info("login flow: entering _show_main_view")
            await app_view._show_main_view()
            logger.info("login flow: _show_main_view returned")

            await app_view._start_stock_monitor()
            initial_alerts = await app_view.controller.obtener_alertas_stock()
            await show_login_alert_banner(app_view, initial_alerts)

        except Exception as ex:
            logger.exception(f"login flow: failure during post-login steps: {ex}")
            app_view.current_user = None
            app_view.current_token = None
            SnackBarHelper.error(app_view.page, "Error de inicio de sesión. Verifique sus credenciales.")
            login_btn.disabled = False
            await show_login_screen(app_view)

    password_field = ft.TextField(
        label="Contraseña",
        password=True,
        can_reveal_password=True,
        border_color=C["input_border"],
        focused_border_color=C["focus_ring"],
        filled=True,
        fill_color=C["input_fill"],
        color=C["text_on_input"],
        cursor_color=C["cursor"],
        selection_color=C["selection"],
        label_style=ft.TextStyle(color=C["text_secondary"]),
        hint_style=ft.TextStyle(color=C["text_muted"]),
        text_style=ft.TextStyle(color=C["text_on_input"], size=14),
        hint_text="Ingresa tu contraseña",
        on_submit=handle_login,
    )

    login_btn = ft.Button(
        content=ft.Text("Ingresar"),
        width=300,
        height=50,
        on_click=handle_login,
        style=ft.ButtonStyle(color="white", bgcolor=C["primary"]),
    )

    card_width = min(380, app_view.page.width * 0.85) if app_view.page.width else 340

    login_card = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.Icons.INVENTORY_2, size=40, color=C["primary"]),
                            T.h1(
                                APP_NAME,
                                page=app_view.page,
                                text_align=ft.TextAlign.CENTER,
                                data="login_title",
                            ),
                            ft.Text(
                                f"v{APP_VERSION}",
                                size=11,
                                color=C["text_muted"],
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                    ),
                    padding=ft.padding.Padding(left=0, right=0, top=0, bottom=10),
                ),
                ft.Divider(height=1, color=C["divider"]),
                ft.Container(height=5),
                username_field,
                password_field,
                error_text,
                ft.Container(height=5),
                login_btn,
                ft.TextButton(
                    content=ft.Text("¿Olvidaste tu contraseña?", color=C["primary"], size=12),
                    on_click=lambda e: asyncio.create_task(show_forgot_password(app_view)),
                ),
                ft.TextButton(
                    content=ft.Text("¿No tienes cuenta? Regístrate", color=C["primary"], size=12),
                    on_click=lambda e: asyncio.create_task(show_register_form(app_view)),
                ),
            ],
            spacing=12,
            width=card_width,
        ),
        bgcolor=C["surface"],
        padding=30,
        border_radius=16,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=C["shadow"]),
    )

    login_container = ft.Container(
        content=ft.Column(
            [
                ft.Container(expand=True),
                login_card,
                ft.Container(expand=True),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        expand=True,
        bgcolor=C["background"],
    )

    app_view.page.clean()
    app_view._drain_dialogs()
    app_view._ensure_file_pickers_in_overlay()
    app_view.page.add(login_container)
    logger.info("login screen rendered")


async def show_register_form(app_view) -> None:
    """Display user registration form."""
    logger.info("Attempting to show register form.")
    try:
        from ui.register_view import show_register_form as _show

        await _show(app_view)
        logger.info("Register form shown successfully.")
    except Exception as e:
        logger.exception(f"Error showing register form: {e}")
        SnackBarHelper.error(app_view.page, "Error al cargar el formulario de registro.")
    app_view.page.update()


async def show_forgot_password(app_view) -> None:
    """Display forgot password form."""
    from ui.forgot_password_view import show_forgot_password as _show

    await _show(app_view)


async def logout(app_view) -> None:
    """Logout and return to login screen."""
    logger.info("logout: starting")
    app_view._current_route = "dashboard"
    try:
        if app_view.current_token:
            await app_view.controller.logout(app_view.current_token)
    except Exception as logout_err:
        logger.exception(f"logout: backend logout failed: {logout_err}")
    finally:
        app_view.current_user = None
        app_view.current_token = None
        app_view.controller.current_user = None
        app_view.controller.current_user_role = None
        app_view.controller.current_user_permissions = set()
    with contextlib.suppress(Exception):
        await app_view._stop_stock_monitor()
    app_view._drain_dialogs()
    app_view.page.clean()
    app_view._ensure_file_pickers_in_overlay()
    try:
        await show_login_screen(app_view)
    except Exception as e:
        logger.exception(f"logout: failed to show login screen: {e}")
        SnackBarHelper.error(app_view.page, "Error al cerrar sesión.")


async def show_login_alert_banner(app_view, alertas: list[dict]) -> None:
    """Show a dismissable banner at the top of the page after login."""
    if not alertas:
        return
    C_banner = theme_manager.palette(page=app_view.page)
    criticas = sum(1 for a in alertas if a.get("alert_level") == "critical")
    bajas = sum(1 for a in alertas if a.get("alert_level") == "low")
    color = C_banner["danger"] if criticas > 0 else C_banner["warning"]
    banner_text = t(
        "stock_alerts.login_banner",
        criticals=criticas,
        lows=bajas,
        total=len(alertas),
    )
    icon = ft.icons.Icons.ERROR if criticas > 0 else ft.icons.Icons.WARNING_AMBER

    async def _view_alerts(_e):
        try:
            await app_view._navigate_to("stock_alerts")
        finally:
            close_login_banner(app_view)

    def _dismiss(_e):
        close_login_banner(app_view)

    close_login_banner(app_view)

    actions = [
        ft.TextButton(t("stock_alerts.view"), on_click=_view_alerts),
        ft.TextButton(t("common.close"), on_click=_dismiss),
    ]
    banner = ft.Banner(
        bgcolor=color,
        leading=ft.Icon(icon, color="white", size=28),
        content=ft.Text(banner_text, color="white", size=14),
        actions=actions,
    )
    app_view._login_alert_banner = banner
    app_view.page.show_dialog(banner)
    app_view.page.update()


def close_login_banner(app_view) -> None:
    """Remove the login alert banner if one is on screen."""
    banner = getattr(app_view, "_login_alert_banner", None)
    if banner is None:
        return
    with contextlib.suppress(Exception):
        app_view.page.pop_dialog()
    app_view._login_alert_banner = None
