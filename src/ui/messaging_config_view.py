"""Messaging configuration view — WhatsApp + Telegram setup form, refactored for clarity."""

import flet as ft

from core.theme_manager import theme_manager
from ui.components import AppHeader, SnackBarHelper
from utils.i18n import t

from ._utils import get_logger

logger = get_logger(__name__)


async def show_messaging_config(app):
    """Display messaging (WhatsApp / Telegram) configuration."""
    palette = theme_manager.palette(page=app.page)

    wa_cfg = {}
    tg_cfg = {}
    if app.controller.has_permission("whatsapp.configurar"):
        try:
            wa_cfg = await app.controller.obtener_config_whatsapp()
        except Exception as e:
            logger.error("Error al obtener config WhatsApp: %s", e)
            wa_cfg = {}
    if app.controller.has_permission("telegram.configurar"):
        try:
            tg_cfg = await app.controller.obtener_config_telegram()
        except Exception as e:
            logger.error("Error al obtener config Telegram: %s", e)
            tg_cfg = {}

    # --- WhatsApp fields ---
    wa_api_key = ft.TextField(
        label=t("messaging.whatsapp.api_key"),
        value=wa_cfg.get("wa_api_key", ""),
        width=400, password=True, can_reveal_password=True,
        border_color=palette["input_border"], focused_border_color=palette["focus_ring"],
        filled=True, fill_color=palette["input_fill"],
    )
    wa_phone_id = ft.TextField(
        label=t("messaging.whatsapp.phone_id"),
        value=wa_cfg.get("wa_phone_id", ""),
        width=400,
        border_color=palette["input_border"], focused_border_color=palette["focus_ring"],
        filled=True, fill_color=palette["input_fill"],
    )
    wa_api_url = ft.TextField(
        label=t("messaging.whatsapp.api_url"),
        value=wa_cfg.get("wa_api_url", "https://graph.facebook.com/v18.0"),
        width=400,
        border_color=palette["input_border"], focused_border_color=palette["focus_ring"],
        filled=True, fill_color=palette["input_fill"],
    )
    wa_enabled = ft.Switch(
        label=t("messaging.whatsapp.enabled"),
        value=wa_cfg.get("wa_enabled", "no") == "si",
    )
    wa_test_phone = ft.TextField(
        label=t("messaging.whatsapp.test_phone"),
        value="", width=400,
        border_color=palette["input_border"], focused_border_color=palette["focus_ring"],
        filled=True, fill_color=palette["input_fill"],
    )

    # --- Telegram fields ---
    tg_bot_token = ft.TextField(
        label=t("messaging.telegram.bot_token"),
        value=tg_cfg.get("tg_bot_token", ""),
        width=400, password=True, can_reveal_password=True,
        border_color=palette["input_border"], focused_border_color=palette["focus_ring"],
        filled=True, fill_color=palette["input_fill"],
    )
    tg_chat_id = ft.TextField(
        label=t("messaging.telegram.chat_id"),
        value=tg_cfg.get("tg_chat_id", ""),
        width=400,
        border_color=palette["input_border"], focused_border_color=palette["focus_ring"],
        filled=True, fill_color=palette["input_fill"],
    )
    tg_enabled = ft.Switch(
        label=t("messaging.telegram.enabled"),
        value=tg_cfg.get("tg_enabled", "no") == "si",
    )

    wa_status = ft.Text("", size=12)
    tg_status = ft.Text("", size=12)

    # --- Handlers ---

    async def _save_wa(e):
        try:
            await app.controller.guardar_config_whatsapp({
                "wa_api_key": wa_api_key.value,
                "wa_phone_id": wa_phone_id.value,
                "wa_api_url": wa_api_url.value,
                "wa_enabled": "si" if wa_enabled.value else "no",
            })
            SnackBarHelper.success(app.page, t("messaging.whatsapp.save_success"))
            wa_status.value = "✓ " + t("messaging.whatsapp.save_success")
            wa_status.color = "green"
            app.page.update()
        except Exception:
            SnackBarHelper.error(app.page, "Error al guardar configuración de WhatsApp.")
            wa_status.value = "✗ Error al guardar configuración."
            wa_status.color = "red"
            app.page.update()

    async def _test_wa(e):
        phone = wa_test_phone.value.strip()
        if not phone:
            wa_status.value = "✗ Ingresa un número de teléfono de prueba"
            wa_status.color = "red"
            app.page.update()
            return
        wa_status.value = "Enviando mensaje de prueba..."
        wa_status.color = palette["text_muted"]
        app.page.update()
        try:
            await app.controller.guardar_config_whatsapp({
                "wa_api_key": wa_api_key.value,
                "wa_phone_id": wa_phone_id.value,
                "wa_api_url": wa_api_url.value,
                "wa_enabled": "si",
            })
            from services.messaging import send_via_channel
            result = await send_via_channel(
                "whatsapp", phone, "Test",
                "Test message from InventarioStore",
                {"wa_api_key": wa_api_key.value, "wa_phone_id": wa_phone_id.value,
                 "wa_api_url": wa_api_url.value, "wa_enabled": "si"},
            )
            if result.get("sent"):
                wa_status.value = "✓ " + t("messaging.whatsapp.test_sent")
                wa_status.color = "green"
                SnackBarHelper.success(app.page, t("messaging.whatsapp.test_sent"))
            else:
                wa_status.value = f"✗ {result.get('reason', 'Error')}"
                wa_status.color = "red"
                SnackBarHelper.error(app.page, result.get("reason", "Error"))
        except Exception as ex:
            wa_status.value = f"✗ {ex}"
            wa_status.color = "red"
        app.page.update()

    async def _save_tg(e):
        try:
            await app.controller.guardar_config_telegram({
                "tg_bot_token": tg_bot_token.value,
                "tg_chat_id": tg_chat_id.value,
                "tg_enabled": "si" if tg_enabled.value else "no",
            })
            SnackBarHelper.success(app.page, t("messaging.telegram.save_success"))
            tg_status.value = "✓ " + t("messaging.telegram.save_success")
            tg_status.color = "green"
            app.page.update()
        except Exception:
            SnackBarHelper.error(app.page, "Error al guardar configuración de Telegram.")
            tg_status.value = "✗ Error al guardar configuración."
            tg_status.color = "red"
            app.page.update()

    async def _test_tg(e):
        tg_status.value = "Enviando mensaje de prueba..."
        tg_status.color = palette["text_muted"]
        app.page.update()
        try:
            await app.controller.guardar_config_telegram({
                "tg_bot_token": tg_bot_token.value,
                "tg_chat_id": tg_chat_id.value,
                "tg_enabled": "si",
            })
            from services.messaging import send_via_channel
            result = await send_via_channel(
                "telegram", tg_chat_id.value, "Test",
                "<b>Test message</b> from InventarioStore",
                {"tg_bot_token": tg_bot_token.value, "tg_chat_id": tg_chat_id.value,
                 "tg_enabled": "si"},
            )
            if result.get("sent"):
                tg_status.value = "✓ " + t("messaging.telegram.test_sent")
                tg_status.color = "green"
                SnackBarHelper.success(app.page, t("messaging.telegram.test_sent"))
            else:
                tg_status.value = f"✗ {result.get('reason', 'Error')}"
                tg_status.color = "red"
                SnackBarHelper.error(app.page, result.get("reason", "Error"))
        except Exception as ex:
            tg_status.value = f"✗ {ex}"
            tg_status.color = "red"
        app.page.update()

    # --- Layout ---
    content = ft.Column([
        AppHeader.create(t("messaging.title"), t("messaging.subtitle")),

        # WhatsApp section
        ft.Container(
            content=ft.Column([
                ft.Text(t("messaging.whatsapp.title"), size=16,
                        weight=ft.FontWeight.BOLD, color=palette["text_primary"]),
                wa_api_key, wa_phone_id, wa_api_url, wa_enabled, wa_test_phone,
                ft.Row([
                    ft.Button(
                        content=ft.Text("Guardar WhatsApp"),
                        on_click=_save_wa,
                        style=ft.ButtonStyle(bgcolor="#25D366", color="white"),
                    ),
                    ft.OutlinedButton(
                        content=ft.Text(t("messaging.whatsapp.test")),
                        on_click=_test_wa,
                    ),
                ], spacing=10),
                wa_status,
            ], spacing=12),
            padding=20, bgcolor=palette["surface"], border_radius=12,
        ),

        ft.Divider(height=20),

        # Telegram section
        ft.Container(
            content=ft.Column([
                ft.Text(t("messaging.telegram.title"), size=16,
                        weight=ft.FontWeight.BOLD, color=palette["text_primary"]),
                tg_bot_token, tg_chat_id, tg_enabled,
                ft.Row([
                    ft.Button(
                        content=ft.Text("Guardar Telegram"),
                        on_click=_save_tg,
                        style=ft.ButtonStyle(bgcolor="#0088cc", color="white"),
                    ),
                    ft.OutlinedButton(
                        content=ft.Text(t("messaging.telegram.test")),
                        on_click=_test_tg,
                    ),
                ], spacing=10),
                tg_status,
            ], spacing=12),
            padding=20, bgcolor=palette["surface"], border_radius=12,
        ),
    ], expand=True, scroll=ft.ScrollMode.AUTO)

    if app.main_view:
        app.main_view.content = content
        app.page.update()
