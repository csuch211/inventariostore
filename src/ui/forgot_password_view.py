"""
Forgot password view — screen for requesting password reset.

Shows a form where the user enters their username to receive
a password reset token via email.
"""

import asyncio

import flet as ft

from config.settings import THEME_PRIMARY_COLOR
from ui.components import SnackBarHelper
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def show_forgot_password(app):
    """Display forgot password form."""
    C = app._get_colors()

    username_field = ft.TextField(
        label="Usuario",
        width=340,
        border_color=C["input_border"],
        focused_border_color=C["focus_ring"],
        filled=True,
        fill_color=C["input_fill"],
        color=C["text_on_input"],
        cursor_color=C["cursor"],
        label_style=ft.TextStyle(color=C["text_secondary"]),
        hint_style=ft.TextStyle(color=C["text_muted"]),
        text_style=ft.TextStyle(color=C["text_on_input"], size=14),
        hint_text="Tu usuario",
    )

    error_text = ft.Text("", color=C["accent"], size=12)
    success_text = ft.Text("", color="green", size=12)

    async def handle_request(e):
        """Handle reset request button click."""
        error_text.value = ""
        success_text.value = ""

        username = username_field.value.strip() if username_field.value else ""

        if not username:
            error_text.value = "El usuario es requerido"
            app.page.update()
            return

        try:
            request_btn.disabled = True
            app.page.update()

            # Call forgot-password API
            from api.rest import ForgotPasswordRequest, forgot_password

            req = ForgotPasswordRequest(username=username)
            result = await forgot_password(req)

            # Always show success to prevent user enumeration
            success_text.value = "✓ Si el usuario existe, se envió un email con instrucciones."
            SnackBarHelper.success(app.page, "Solicitud enviada")

            app.page.update()

        except Exception as ex:
            error_text.value = f"Error: {ex}"
            SnackBarHelper.error(app.page, f"Error: {ex}")
        finally:
            request_btn.disabled = False
            app.page.update()

    def go_to_reset(e):
        """Navigate to reset password screen."""
        asyncio.create_task(show_reset_password(app, username_field.value or ""))

    def go_back_to_login(e):
        """Navigate back to login screen."""
        asyncio.create_task(app._show_login_screen())

    request_btn = ft.Button(
        content=ft.Text("Enviar Instrucciones"),
        width=340,
        height=50,
        on_click=handle_request,
        style=ft.ButtonStyle(
            color="white",
            bgcolor=THEME_PRIMARY_COLOR,
        ),
    )

    reset_btn = ft.TextButton(
        content=ft.Text(
            "¿Ya tienes el token? Restablecer contraseña",
            color=C["primary"],
            size=12,
        ),
        on_click=go_to_reset,
    )

    back_btn = ft.TextButton(
        content=ft.Text("Volver al login"),
        on_click=go_back_to_login,
    )

    card_width = min(380, app.page.width * 0.85) if app.page.width else 340

    forgot_card = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.Icons.LOCK_RESET, size=40, color=THEME_PRIMARY_COLOR),
                            ft.Text(
                                "Recuperar Contraseña",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=THEME_PRIMARY_COLOR,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "Ingresa tu usuario para recibir instrucciones",
                                size=12,
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
                error_text,
                success_text,
                ft.Container(height=5),
                request_btn,
                reset_btn,
                back_btn,
            ],
            spacing=10,
            width=card_width,
        ),
        bgcolor=C["surface"],
        padding=30,
        border_radius=16,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=C["shadow"]),
    )

    container = ft.Container(
        content=ft.Column(
            [
                ft.Container(expand=True),
                forgot_card,
                ft.Container(expand=True),
            ],
            expand=True,
        ),
        expand=True,
        bgcolor=C["background"],
        alignment=ft.alignment.center,
    )

    if app.main_view:
        app.main_view.content = container
    else:
        app.page.clean()
        app.page.add(container)
    app.page.update()


async def show_reset_password(app, username: str = ""):
    """Display reset password form with token and new password."""
    C = app._get_colors()

    token_field = ft.TextField(
        label="Token de recuperación",
        width=340,
        border_color=C["input_border"],
        focused_border_color=C["focus_ring"],
        filled=True,
        fill_color=C["input_fill"],
        color=C["text_on_input"],
        cursor_color=C["cursor"],
        label_style=ft.TextStyle(color=C["text_secondary"]),
        hint_style=ft.TextStyle(color=C["text_muted"]),
        text_style=ft.TextStyle(color=C["text_on_input"], size=14),
        hint_text="Pega el token de tu email",
    )

    password_field = ft.TextField(
        label="Nueva contraseña",
        width=340,
        password=True,
        can_reveal_password=True,
        border_color=C["input_border"],
        focused_border_color=C["focus_ring"],
        filled=True,
        fill_color=C["input_fill"],
        color=C["text_on_input"],
        cursor_color=C["cursor"],
        label_style=ft.TextStyle(color=C["text_secondary"]),
        hint_style=ft.TextStyle(color=C["text_muted"]),
        text_style=ft.TextStyle(color=C["text_on_input"], size=14),
        hint_text="Mínimo 8 caracteres",
    )

    confirm_field = ft.TextField(
        label="Confirmar contraseña",
        width=340,
        password=True,
        can_reveal_password=True,
        border_color=C["input_border"],
        focused_border_color=C["focus_ring"],
        filled=True,
        fill_color=C["input_fill"],
        color=C["text_on_input"],
        cursor_color=C["cursor"],
        label_style=ft.TextStyle(color=C["text_secondary"]),
        hint_style=ft.TextStyle(color=C["text_muted"]),
        text_style=ft.TextStyle(color=C["text_on_input"], size=14),
        hint_text="Repite tu contraseña",
    )

    error_text = ft.Text("", color=C["accent"], size=12)
    success_text = ft.Text("", color="green", size=12)

    async def handle_reset(e):
        """Handle reset password button click."""
        error_text.value = ""
        success_text.value = ""

        token = token_field.value.strip() if token_field.value else ""
        password = password_field.value or ""
        confirm = confirm_field.value or ""

        if not token:
            error_text.value = "El token es requerido"
            app.page.update()
            return

        if len(password) < 8:
            error_text.value = "La contraseña debe tener al menos 8 caracteres"
            app.page.update()
            return

        import re

        if not re.search(r"[A-Z]", password):
            error_text.value = "La contraseña debe contener al menos una mayúscula"
            app.page.update()
            return

        if not re.search(r"[0-9]", password):
            error_text.value = "La contraseña debe contener al menos un número"
            app.page.update()
            return

        if password != confirm:
            error_text.value = "Las contraseñas no coinciden"
            app.page.update()
            return

        try:
            reset_btn.disabled = True
            app.page.update()

            # Call reset-password API
            from api.rest import ResetPasswordRequest, reset_password

            req = ResetPasswordRequest(token=token, new_password=password)
            result = await reset_password(req)

            success_text.value = "✓ Contraseña restablecida exitosamente"
            SnackBarHelper.success(app.page, "Contraseña actualizada")

            app.page.update()

            # Redirect to login after 2 seconds
            await asyncio.sleep(2)
            await app._show_login_screen()

        except Exception as ex:
            error_text.value = f"Error: {ex}"
            SnackBarHelper.error(app.page, f"Error: {ex}")
        finally:
            reset_btn.disabled = False
            app.page.update()

    def go_back_to_login(e):
        """Navigate back to login screen."""
        asyncio.create_task(app._show_login_screen())

    reset_btn = ft.Button(
        content=ft.Text("Restablecer Contraseña"),
        width=340,
        height=50,
        on_click=handle_reset,
        style=ft.ButtonStyle(
            color="white",
            bgcolor=THEME_PRIMARY_COLOR,
        ),
    )

    back_btn = ft.TextButton(
        content=ft.Text("Volver al login"),
        on_click=go_back_to_login,
    )

    card_width = min(380, app.page.width * 0.85) if app.page.width else 340

    reset_card = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.Icons.PASSWORD, size=40, color=THEME_PRIMARY_COLOR),
                            ft.Text(
                                "Restablecer Contraseña",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=THEME_PRIMARY_COLOR,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "Ingresa el token y tu nueva contraseña",
                                size=12,
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
                token_field,
                password_field,
                confirm_field,
                error_text,
                success_text,
                ft.Container(height=5),
                reset_btn,
                back_btn,
            ],
            spacing=10,
            width=card_width,
        ),
        bgcolor=C["surface"],
        padding=30,
        border_radius=16,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=C["shadow"]),
    )

    container = ft.Container(
        content=ft.Column(
            [
                ft.Container(expand=True),
                reset_card,
                ft.Container(expand=True),
            ],
            expand=True,
        ),
        expand=True,
        bgcolor=C["background"],
        alignment=ft.alignment.center,
    )

    if app.main_view:
        app.main_view.content = container
    else:
        app.page.clean()
        app.page.add(container)
    app.page.update()
