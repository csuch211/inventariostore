"""
Email verification view — screen for entering verification token.

Shown after user registration. Allows entering the token received
via email to activate the account.
"""

import asyncio

import flet as ft

from config.settings import THEME_PRIMARY_COLOR
from ui.components import SnackBarHelper
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def show_verify_email(app, username: str = "", email: str = ""):
    """Display email verification form."""
    C = app._get_colors()

    token_field = ft.TextField(
        label="Token de verificación",
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
        multiline=False,
    )

    error_text = ft.Text("", color=C["accent"], size=12)
    success_text = ft.Text("", color="green", size=12)

    async def handle_verify(e):
        """Handle verification button click."""
        error_text.value = ""
        success_text.value = ""

        token = token_field.value.strip() if token_field.value else ""

        if not token:
            error_text.value = "El token es requerido"
            app.page.update()
            return

        try:
            verify_btn.disabled = True
            app.page.update()

            # Call verify-email API
            from api.rest import VerifyEmailRequest, verify_email

            req = VerifyEmailRequest(token=token)
            result = await verify_email(req)

            success_text.value = "✓ Email verificado exitosamente. Ahora puedes iniciar sesión."
            SnackBarHelper.success(app.page, "Cuenta activada")

            app.page.update()

            # Redirect to login after 2 seconds
            await asyncio.sleep(2)
            await app._show_login_screen()

        except Exception as ex:
            error_text.value = f"Error: {ex}"
            SnackBarHelper.error(app.page, f"Error de verificación: {ex}")
        finally:
            verify_btn.disabled = False
            app.page.update()

    async def handle_resend(e):
        """Resend verification email."""
        resend_btn.disabled = True
        app.page.update()

        try:
            from api.rest import ForgotPasswordRequest, resend_verification

            req = ForgotPasswordRequest(username=username)
            await resend_verification(req)

            success_text.value = "✓ Email de verificación reenviado"
            SnackBarHelper.success(app.page, "Email reenviado")
        except Exception as ex:
            error_text.value = f"Error al reenviar: {ex}"
        finally:
            resend_btn.disabled = False
            app.page.update()

    def go_back_to_login(e):
        """Navigate back to login screen."""
        asyncio.create_task(app._show_login_screen())

    verify_btn = ft.Button(
        content=ft.Text("Verificar Cuenta"),
        width=340,
        height=50,
        on_click=handle_verify,
        style=ft.ButtonStyle(
            color="white",
            bgcolor=THEME_PRIMARY_COLOR,
        ),
    )

    resend_btn = ft.OutlinedButton(
        content=ft.Text("Reenviar email de verificación"),
        width=340,
        on_click=handle_resend,
    )

    back_btn = ft.TextButton(
        content=ft.Text("Volver al login"),
        on_click=go_back_to_login,
    )

    card_width = min(380, app.page.width * 0.85) if app.page.width else 340

    verify_card = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.Icons.MAIL_LOCK, size=40, color=THEME_PRIMARY_COLOR),
                            ft.Text(
                                "Verificar Email",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=THEME_PRIMARY_COLOR,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "Revisa tu email y pega el token de verificación",
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
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.Icons.INFO_OUTLINE, size=20, color=C["text_muted"]),
                            ft.Text(
                                "Se envió un email de verificación a:",
                                size=11,
                                color=C["text_muted"],
                            ),
                            ft.Text(
                                email or "tu email",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=C["text_primary"],
                            ),
                            ft.Text(
                                "El token expira en 24 horas",
                                size=10,
                                color=C["text_muted"],
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=10,
                    bgcolor=C["input_fill"],
                    border_radius=8,
                ),
                ft.Container(height=5),
                token_field,
                error_text,
                success_text,
                ft.Container(height=5),
                verify_btn,
                resend_btn,
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

    verify_container = ft.Container(
        content=ft.Column(
            [
                ft.Container(expand=True),
                verify_card,
                ft.Container(expand=True),
            ],
            expand=True,
        ),
        expand=True,
        bgcolor=C["background"],
        alignment=ft.alignment.center,
    )

    if app.main_view:
        app.main_view.content = verify_container
    else:
        app.page.clean()
        app.page.add(verify_container)
    app.page.update()
