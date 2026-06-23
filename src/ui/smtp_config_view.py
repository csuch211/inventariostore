"""
SMTP Configuration view — graphical form for setting up email.

Provides presets for common providers (Gmail, Outlook, Yahoo),
connection testing, and test email sending.
"""

import flet as ft

from config.settings import THEME_PRIMARY_COLOR
from ui.components import AppHeader, SnackBarHelper
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Preset configurations for common SMTP providers
SMTP_PRESETS = {
    "Gmail": {
        "host": "smtp.gmail.com",
        "port": "587",
        "note": "Requiere App Password (myaccount.google.com/apppasswords)",
    },
    "Outlook / Hotmail": {
        "host": "smtp.office365.com",
        "port": "587",
        "note": "Usa tu contraseña normal de Outlook",
    },
    "Yahoo": {
        "host": "smtp.mail.yahoo.com",
        "port": "587",
        "note": "Requiere App Password",
    },
    "Zoho Mail": {
        "host": "smtp.zoho.com",
        "port": "587",
        "note": "Usa tu contraseña de Zoho",
    },
    "Custom": {
        "host": "",
        "port": "587",
        "note": "Configura manualmente",
    },
}


async def show_smtp_config(app):
    """Display SMTP configuration form with provider presets."""
    C = app._get_colors()

    # Load current config
    smtp_cfg = {}
    if app.controller.has_permission("notificaciones.configurar"):
        try:
            smtp_cfg = await app.controller.obtener_config_smtp()
        except Exception:
            smtp_cfg = {}

    # Create form fields
    provider_dropdown = ft.Dropdown(
        label="Proveedor de Email",
        options=[ft.dropdown.Option(key=k) for k in SMTP_PRESETS.keys()],
        value="Gmail",
        border_color=C["input_border"],
        focused_border_color=C["focus_ring"],
        filled=True,
        fill_color=C["input_fill"],
        on_change=lambda e: _apply_preset(e.control.value),
        width=300,
    )

    host_field = ft.TextField(
        label="Servidor SMTP (Host)",
        value=smtp_cfg.get("host", SMTP_PRESETS["Gmail"]["host"]),
        width=300,
        border_color=C["input_border"],
        focused_border_color=C["focus_ring"],
        filled=True,
        fill_color=C["input_fill"],
    )

    port_field = ft.TextField(
        label="Puerto",
        value=smtp_cfg.get("port", SMTP_PRESETS["Gmail"]["port"]),
        width=100,
        border_color=C["input_border"],
        focused_border_color=C["focus_ring"],
        filled=True,
        fill_color=C["input_fill"],
    )

    user_field = ft.TextField(
        label="Usuario / Email",
        value=smtp_cfg.get("user", ""),
        width=420,
        border_color=C["input_border"],
        focused_border_color=C["focus_ring"],
        filled=True,
        fill_color=C["input_fill"],
    )

    password_field = ft.TextField(
        label="Contraseña / App Password",
        value=smtp_cfg.get("password", "") if smtp_cfg.get("password") else "",
        width=420,
        password=True,
        can_reveal_password=True,
        border_color=C["input_border"],
        focused_border_color=C["focus_ring"],
        filled=True,
        fill_color=C["input_fill"],
    )

    from_email_field = ft.TextField(
        label="Email del Remitente",
        value=smtp_cfg.get("from_email", ""),
        width=420,
        border_color=C["input_border"],
        focused_border_color=C["focus_ring"],
        filled=True,
        fill_color=C["input_fill"],
    )

    enabled_switch = ft.Switch(
        label="Habilitar notificaciones por email",
        value=smtp_cfg.get("enabled") == "si",
    )

    note_text = ft.Text(
        SMTP_PRESETS["Gmail"]["note"],
        size=12,
        color=C["text_muted"],
        italic=True,
    )

    status_text = ft.Text("", size=12)

    def _apply_preset(provider_name):
        preset = SMTP_PRESETS.get(provider_name, {})
        host_field.value = preset.get("host", "")
        port_field.value = preset.get("port", "587")
        note_text.value = preset.get("note", "")
        app.page.update()

    async def handle_save(e):
        """Save SMTP configuration."""
        try:
            await app.controller.guardar_config_smtp(
                {
                    "smtp_host": host_field.value,
                    "smtp_port": port_field.value,
                    "smtp_user": user_field.value,
                    "smtp_password": password_field.value,
                    "smtp_from_email": from_email_field.value,
                    "smtp_to_email": from_email_field.value,
                    "notify_low_stock": "si" if enabled_switch.value else "no",
                }
            )
            SnackBarHelper.success(app.page, "Configuración SMTP guardada")
            status_text.value = "✓ Configuración guardada"
            status_text.color = "green"
            app.page.update()
        except Exception as ex:
            SnackBarHelper.error(app.page, f"Error al guardar: {ex}")
            status_text.value = f"✗ Error: {ex}"
            status_text.color = "red"
            app.page.update()

    async def handle_test_connection(e):
        """Test SMTP connection."""
        status_text.value = "Probando conexión..."
        status_text.color = C["text_muted"]
        app.page.update()

        try:
            import smtplib
            import ssl

            context = ssl.create_default_context()
            with smtplib.SMTP(host_field.value, int(port_field.value), timeout=10) as server:
                server.starttls(context=context)
                server.login(user_field.value, password_field.value)

            status_text.value = "✓ Conexión SMTP exitosa"
            status_text.color = "green"
            SnackBarHelper.success(app.page, "Conexión SMTP exitosa")
        except smtplib.SMTPAuthenticationError:
            status_text.value = "✗ Error de autenticación — verifica usuario/contraseña"
            status_text.color = "red"
            SnackBarHelper.error(app.page, "Error de autenticación SMTP")
        except smtplib.SMTPConnectError:
            status_text.value = "✗ No se pudo conectar — verifica host/puerto"
            status_text.color = "red"
            SnackBarHelper.error(app.page, "Error de conexión SMTP")
        except Exception as ex:
            status_text.value = f"✗ Error: {ex}"
            status_text.color = "red"
            SnackBarHelper.error(app.page, f"Error SMTP: {ex}")

        app.page.update()

    async def handle_send_test(e):
        """Send a test email."""
        status_text.value = "Enviando email de prueba..."
        status_text.color = C["text_muted"]
        app.page.update()

        try:
            # Save config first
            await app.controller.guardar_config_smtp(
                {
                    "smtp_host": host_field.value,
                    "smtp_port": port_field.value,
                    "smtp_user": user_field.value,
                    "smtp_password": password_field.value,
                    "smtp_from_email": from_email_field.value,
                    "smtp_to_email": from_email_field.value,
                    "notify_low_stock": "si" if enabled_switch.value else "no",
                }
            )

            result = await app.controller.enviar_alerta_stock()
            if result.get("sent"):
                status_text.value = "✓ Email de prueba enviado"
                status_text.color = "green"
                SnackBarHelper.success(app.page, "Email de prueba enviado")
            else:
                status_text.value = f"✗ No enviado: {result.get('reason', 'unknown')}"
                status_text.color = "red"
                SnackBarHelper.error(app.page, f"Error: {result.get('reason')}")
        except Exception as ex:
            status_text.value = f"✗ Error: {ex}"
            status_text.color = "red"
            SnackBarHelper.error(app.page, f"Error: {ex}")

        app.page.update()

    # Build the form layout
    content = ft.Column(
        [
            AppHeader.create(
                "Configuración de Email", "Configura el servidor SMTP para notificaciones"
            ),
            ft.Container(
                content=ft.Column(
                    [
                        # Provider preset
                        ft.Text(
                            "Proveedor", size=14, weight=ft.FontWeight.BOLD, color=C["text_primary"]
                        ),
                        provider_dropdown,
                        note_text,
                        ft.Divider(),
                        # Server settings
                        ft.Text(
                            "Servidor SMTP",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=C["text_primary"],
                        ),
                        ft.Row([host_field, port_field], spacing=10),
                        ft.Divider(),
                        # Credentials
                        ft.Text(
                            "Credenciales",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=C["text_primary"],
                        ),
                        user_field,
                        password_field,
                        ft.Divider(),
                        # Sender
                        ft.Text(
                            "Remitente", size=14, weight=ft.FontWeight.BOLD, color=C["text_primary"]
                        ),
                        from_email_field,
                        ft.Divider(),
                        # Options
                        ft.Text(
                            "Opciones", size=14, weight=ft.FontWeight.BOLD, color=C["text_primary"]
                        ),
                        enabled_switch,
                        ft.Divider(),
                        # Action buttons
                        ft.Row(
                            [
                                ft.Button(
                                    content=ft.Text("Guardar"),
                                    on_click=handle_save,
                                    style=ft.ButtonStyle(
                                        bgcolor=THEME_PRIMARY_COLOR, color="white"
                                    ),
                                ),
                                ft.OutlinedButton(
                                    content=ft.Text("Probar Conexión"),
                                    on_click=handle_test_connection,
                                ),
                                ft.OutlinedButton(
                                    content=ft.Text("Enviar Email de Prueba"),
                                    on_click=handle_send_test,
                                ),
                            ],
                            spacing=10,
                        ),
                        status_text,
                    ],
                    spacing=12,
                ),
                padding=20,
                bgcolor=C["surface"],
                border_radius=12,
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()
