"""
User registration view — graphical form for new user signup.

Provides a clean registration form with real-time validation,
password strength indicator, and email verification flow.
"""

import asyncio
import re

import flet as ft

from config.settings import THEME_PRIMARY_COLOR
from ui.components import SnackBarHelper
from utils.logger import setup_logger

logger = setup_logger(__name__)


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
    C = app._get_colors()

    # Form fields
    nombre_field = ft.TextField(
        label="Nombre completo",
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
        hint_text="Tu nombre",
    )

    email_field = ft.TextField(
        label="Email",
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
        hint_text="tu@email.com",
    )

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
        hint_text="letras, números, guiones",
    )

    password_field = ft.TextField(
        label="Contraseña",
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

    # Password strength indicator
    strength_bar = ft.ProgressBar(width=340, color="gray", value=0)
    strength_text = ft.Text("", size=11, color=C["text_muted"])

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

    error_text = ft.Text("", color=C["accent"], size=12)
    success_text = ft.Text("", color="green", size=12)

    async def handle_register(e):
        """Handle registration button click."""
        error_text.value = ""
        success_text.value = ""

        nombre = nombre_field.value.strip() if nombre_field.value else ""
        email = email_field.value.strip() if email_field.value else ""
        username = username_field.value.strip() if username_field.value else ""
        password = password_field.value or ""
        confirm = confirm_field.value or ""

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

            # Call registration API
            from api.rest import register, RegisterRequest

            req = RegisterRequest(
                username=username,
                password=password,
                nombre=nombre,
                email=email,
            )
            result = await register(req)

            success_text.value = "✓ Registro exitoso. Revisa tu email para verificar tu cuenta."
            SnackBarHelper.success(app.page, "Cuenta creada exitosamente")

            # Clear form
            nombre_field.value = ""
            email_field.value = ""
            username_field.value = ""
            password_field.value = ""
            confirm_field.value = ""
            strength_bar.value = 0
            strength_text.value = ""

            app.page.update()

        except Exception as ex:
            error_text.value = f"Error: {ex}"
            SnackBarHelper.error(app.page, f"Error de registro: {ex}")
        finally:
            register_btn.disabled = False
            app.page.update()

    def go_back_to_login(e):
        """Navigate back to login screen."""
        asyncio.create_task(app._show_login_screen())

    register_btn = ft.Button(
        content=ft.Text("Crear Cuenta"),
        width=340,
        height=50,
        on_click=handle_register,
        style=ft.ButtonStyle(
            color="white",
            bgcolor=C["primary"],
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
                            ft.Icon(ft.icons.Icons.PERSON_ADD, size=40, color=C["primary"]),
                            ft.Text(
                                "Crear Cuenta",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=C["primary"],
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "Regístrate para acceder al sistema",
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
        bgcolor=C["surface"],
        padding=30,
        border_radius=16,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=C["shadow"]),
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
        bgcolor=C["background"],
        alignment=ft.alignment.center,
    )

    if app.main_view:
        app.main_view.content = register_container
    else:
        app.page.clean()
        app.page.add(register_container)
    app.page.update()
