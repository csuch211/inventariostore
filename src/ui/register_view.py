"""User registration view, refactored for clarity.
User registration view — graphical form for new user signup.

Provides a clean registration form with real-time validation,
password strength indicator, and email verification flow.
"""

import asyncio
import re

import flet as ft

from ui.components import SnackBarHelper

from ._utils import get_logger

logger = get_logger(__name__)


def _check_password_strength(password: str) -> tuple[int, str, str]:
    """Check password strength. Returns (score 0-4, label, color)."""
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"[0-9]", password):
        score += 1
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 1

    if score <= 1:
        return score, "Débil", "red"
    elif score <= 2:
        return score, "Regular", "orange"
    elif score <= 3:
        return score, "Buena", "yellow"
    else:
        return score, "Fuerte", "green"


async def show_register_form(app):
    """Display user registration form."""
    from core.theme_manager import theme_manager
    palette = theme_manager.palette(page=app.page)

    # Form fields
    nombre_field = ft.TextField(
        label="Nombre completo",
        width=340,
        border_color=palette["input_border"],
        focused_border_color=palette["focus_ring"],
        filled=True,
        fill_color=palette["input_fill"],
        color=palette["text_on_input"],
        cursor_color=palette["cursor"],
        label_style=ft.TextStyle(color=palette["text_secondary"]),
        hint_style=ft.TextStyle(color=palette["text_muted"]),
        text_style=ft.TextStyle(color=palette["text_on_input"], size=14),
        hint_text="Tu nombre",
    )

    email_field = ft.TextField(
        label="Email",
        width=340,
        border_color=palette["input_border"],
        focused_border_color=palette["focus_ring"],
        filled=True,
        fill_color=palette["input_fill"],
        color=palette["text_on_input"],
        cursor_color=palette["cursor"],
        label_style=ft.TextStyle(color=palette["text_secondary"]),
        hint_style=ft.TextStyle(color=palette["text_muted"]),
        text_style=ft.TextStyle(color=palette["text_on_input"], size=14),
        hint_text="tu@email.com",
    )

    username_field = ft.TextField(
        label="Usuario",
        width=340,
        border_color=palette["input_border"],
        focused_border_color=palette["focus_ring"],
        filled=True,
        fill_color=palette["input_fill"],
        color=palette["text_on_input"],
        cursor_color=palette["cursor"],
        label_style=ft.TextStyle(color=palette["text_secondary"]),
        hint_style=ft.TextStyle(color=palette["text_muted"]),
        text_style=ft.TextStyle(color=palette["text_on_input"], size=14),
        hint_text="letras, números, guiones",
    )

    password_field = ft.TextField(
        label="Contraseña",
        width=340,
        password=True,
        can_reveal_password=True,
        border_color=palette["input_border"],
        focused_border_color=palette["focus_ring"],
        filled=True,
        fill_color=palette["input_fill"],
        color=palette["text_on_input"],
        cursor_color=palette["cursor"],
        label_style=ft.TextStyle(color=palette["text_secondary"]),
        hint_style=ft.TextStyle(color=palette["text_muted"]),
        text_style=ft.TextStyle(color=palette["text_on_input"], size=14),
        hint_text="Mínimo 8 caracteres",
    )

    confirm_field = ft.TextField(
        label="Confirmar contraseña",
        width=340,
        password=True,
        can_reveal_password=True,
        border_color=palette["input_border"],
        focused_border_color=palette["focus_ring"],
        filled=True,
        fill_color=palette["input_fill"],
        color=palette["text_on_input"],
        cursor_color=palette["cursor"],
        label_style=ft.TextStyle(color=palette["text_secondary"]),
        hint_style=ft.TextStyle(color=palette["text_muted"]),
        text_style=ft.TextStyle(color=palette["text_on_input"], size=14),
        hint_text="Repite tu contraseña",
    )

    # Password strength indicator
    strength_bar = ft.ProgressBar(width=340, color="gray", value=0)
    strength_text = ft.Text("", size=11, color=palette["text_muted"])

    def update_strength(e):
        pwd = password_field.value or ""
        if pwd:
            score, label, color = _check_password_strength(pwd)
            strength_bar.value = score / 5
            strength_bar.color = color
            strength_text.value = f"Seguridad: {label}"
            strength_text.color = color
        else:
            strength_bar.value = 0
            strength_bar.color = "gray"
            strength_text.value = ""
        app.page.update()

    password_field.on_change = update_strength

    error_text = ft.Text("", color=palette["accent"], size=12)
    success_text = ft.Text("", color="green", size=12)

    async def handle_register(e):
        """Handle registration button click."""
        error_text.value = ""
        success_text.value = ""
        app.page.update() # Ensure previous errors are cleared immediately

        nombre = nombre_field.value.strip() if nombre_field.value else ""
        email = email_field.value.strip() if email_field.value else ""
        username = username_field.value.strip() if username_field.value else ""
        password = password_field.value or ""
        confirm = confirm_field.value or ""

        logger.info(f"Attempting registration for username: {username}, email: {email}")

        # Validation
        if not nombre or len(nombre) < 2:
            error_text.value = "El nombre debe tener al menos 2 caracteres"
            app.page.update()
            return

        if not email or "@" not in email:
            error_text.value = "Email inválido"
            app.page.update()
            return

        if not username or len(username) < 3:
            error_text.value = "El usuario debe tener al menos 3 caracteres"
            app.page.update()
            return

        if not re.match(r"^[A-Za-z0-9_-]+$", username):
            error_text.value = "El usuario solo puede contener letras, números, guiones"
            app.page.update()
            return

        if len(password) < 8:
            error_text.value = "La contraseña debe tener al menos 8 caracteres"
            app.page.update()
            return

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
            register_btn.disabled = True
            app.page.update()
            logger.info("Client-side validation passed. Calling backend registration API.")

            # Call registration API
            from api.rest import RegisterRequest, register

            req = RegisterRequest(
                username=username,
                password=password,
                nombre=nombre,
                email=email,
            )
            await register(req)
            logger.info("Backend registration API call successful.")

            SnackBarHelper.success(app.page, "Cuenta creada exitosamente")

            # Redirect to email verification screen
            from ui.verify_email_view import show_verify_email

            await show_verify_email(app, username=username, email=email)

        except Exception as ex:
            logger.exception(f"Error during user registration for {username}: {ex}")
            error_text.value = f"Error de registro: {ex}" # Display the actual exception message
            SnackBarHelper.error(app.page, "Error de registro. Verifique sus datos e intente nuevamente.")
        finally:
            register_btn.disabled = False
            app.page.update()

    def go_back_to_login(e):
        """Navigate back to login screen."""
        task = asyncio.create_task(app._show_login_screen())
        task.add_done_callback(lambda t: None)

    register_btn = ft.Button(
        content=ft.Text("Crear Cuenta"),
        width=340,
        height=50,
        on_click=handle_register,
        style=ft.ButtonStyle(
            color="white",
            bgcolor=palette["primary"],
        ),
    )

    back_btn = ft.TextButton(
        content=ft.Text("¿Ya tienes cuenta? Inicia sesión"),
        on_click=go_back_to_login,
    )

    card_width = min(380, app.page.width * 0.85) if app.page.width else 340

    register_card = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.Icons.PERSON_ADD, size=40, color=palette["primary"]),
                            ft.Text(
                                "Crear Cuenta",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=palette["primary"],
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "Regístrate para acceder al sistema",
                                size=12,
                                color=palette["text_muted"],
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                    ),
                    padding=ft.padding.Padding(left=0, right=0, top=0, bottom=10),
                ),
                ft.Divider(height=1, color=palette["divider"]),
                ft.Container(height=5),
                nombre_field,
                email_field,
                username_field,
                password_field,
                strength_bar,
                strength_text,
                confirm_field,
                error_text,
                success_text,
                ft.Container(height=5),
                register_btn,
                back_btn,
            ],
            spacing=10,
            width=card_width,
        ),
        bgcolor=palette["surface"],
        padding=30,
        border_radius=16,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=palette["shadow"]),
    )

    register_container = ft.Container(
        content=ft.Column(
            [
                ft.Container(expand=True),
                register_card,
                ft.Container(expand=True),
            ],
            expand=True,
        ),
        expand=True,
        bgcolor=palette["background"],
        alignment=ft.alignment.Alignment.CENTER,
    )

    # Simplified rendering logic: always clear and add directly
    app.page.clean()
    app.page.add(register_container)
    logger.info("RegisterView: Page cleared, register_container added, and update requested.")
    app.page.update()
