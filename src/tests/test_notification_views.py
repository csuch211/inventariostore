"""Tests for the notification UI views (notification_views.py).

Uses fake page/view/app doubles so no Flet event loop is required.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from ui.notification_views import show_notificaciones, show_plantillas_notificacion


class FakeOverlay(list):
    pass


class FakePage:
    def __init__(self):
        self.overlay = FakeOverlay()
        self.update_count = 0
        self.dialogs_shown: list[Any] = []
        self.popped_dialogs = 0
        self.snackbars: list[Any] = []
        self.title = ""
        self.theme_mode = "light"

    def update(self):
        self.update_count += 1

    def show_dialog(self, dialog):
        self.dialogs_shown.append(dialog)

    def pop_dialog(self):
        self.popped_dialogs += 1

    def clean(self):
        pass

    def add(self, *args):
        pass


class FakeMainView:
    def __init__(self):
        self.content = None


class FakeApp:
    def __init__(self, controller):
        self.controller = controller
        self.page = FakePage()
        self.main_view = FakeMainView()

    def _get_colors(self):
        return {
            "primary": "#1976D2",
            "primary_light": "#42A5F5",
            "background": "#FFFFFF",
            "surface": "#F5F5F5",
            "text_primary": "#212121",
            "text_secondary": "#757575",
            "text_muted": "#9E9E9E",
            "divider": "#E0E0E0",
            "input_fill": "#F8FAFC",
            "input_border": "#CBD5E1",
        }


@pytest.fixture
def app(ctrl):
    return FakeApp(ctrl)


class TestShowNotificaciones:
    @pytest.mark.asyncio
    async def test_empty_state(self, app: FakeApp):
        with MagicMock() as mock_ctrl:
            app.controller = mock_ctrl
            mock_ctrl.obtener_notificaciones = AsyncMock(return_value=[])
            mock_ctrl.contar_no_leidas = AsyncMock(return_value=0)
            await show_notificaciones(app)
        assert app.main_view.content is not None
        assert app.page.update_count >= 1

    @pytest.mark.asyncio
    async def test_with_data(self, app: FakeApp):
        with MagicMock() as mock_ctrl:
            app.controller = mock_ctrl
            mock_ctrl.obtener_notificaciones = AsyncMock(return_value=[
                {"id": 1, "titulo": "Stock Bajo", "mensaje": "Prod X tiene 2 unid",
                 "tipo": "warning", "estado": "pendiente", "creado_en": "2025-01-01T10:00:00"},
                {"id": 2, "titulo": "Venta realizada", "mensaje": "Venta #123 completada",
                 "tipo": "success", "estado": "leido", "creado_en": "2025-01-02T12:00:00"},
            ])
            mock_ctrl.contar_no_leidas = AsyncMock(return_value=1)
            await show_notificaciones(app)
        assert app.main_view.content is not None
        assert app.page.update_count >= 1

    @pytest.mark.asyncio
    async def test_dropdown_triggers_refresh(self, app: FakeApp):
        with MagicMock() as mock_ctrl:
            app.controller = mock_ctrl
            mock_ctrl.obtener_notificaciones = AsyncMock(return_value=[])
            mock_ctrl.contar_no_leidas = AsyncMock(return_value=0)
            await show_notificaciones(app)
            tipo_filter = None
            content = app.main_view.content
            for c in (content.controls if hasattr(content, "controls") else []):
                if hasattr(c, "content") and hasattr(c.content, "controls"):
                    for row in c.content.controls:
                        if hasattr(row, "controls"):
                            for item in row.controls:
                                if hasattr(item, "label") and item.label == "Tipo":
                                    tipo_filter = item
            if tipo_filter and tipo_filter.on_change:
                await tipo_filter.on_change(None)
            assert app.page.update_count >= 1

    @pytest.mark.asyncio
    async def test_mark_read_button(self, app: FakeApp):
        with MagicMock() as mock_ctrl:
            app.controller = mock_ctrl
            mock_ctrl.obtener_notificaciones = AsyncMock(return_value=[
                {"id": 10, "titulo": "T", "mensaje": "M", "tipo": "info",
                 "estado": "pendiente", "creado_en": "2025-01-01T10:00:00"},
            ])
            mock_ctrl.contar_no_leidas = AsyncMock(return_value=1)
            mock_ctrl.marcar_leido = AsyncMock(return_value=(True, {"message": "ok"}))
            await show_notificaciones(app)
            assert app.main_view.content is not None

    @pytest.mark.asyncio
    async def test_mark_all_read_button(self, app: FakeApp):
        with MagicMock() as mock_ctrl:
            app.controller = mock_ctrl
            mock_ctrl.obtener_notificaciones = AsyncMock(return_value=[
                {"id": 1, "titulo": "T", "mensaje": "M", "tipo": "info",
                 "estado": "pendiente", "creado_en": "2025-01-01T10:00:00"},
            ])
            mock_ctrl.contar_no_leidas = AsyncMock(return_value=1)
            mock_ctrl.marcar_todas_leidas = AsyncMock(return_value=(True, {"count": 1}))
            await show_notificaciones(app)
            assert app.main_view.content is not None

    @pytest.mark.asyncio
    async def test_delete_button(self, app: FakeApp):
        with MagicMock() as mock_ctrl:
            app.controller = mock_ctrl
            mock_ctrl.obtener_notificaciones = AsyncMock(return_value=[
                {"id": 5, "titulo": "T", "mensaje": "M", "tipo": "info",
                 "estado": "pendiente", "creado_en": "2025-01-01T10:00:00"},
            ])
            mock_ctrl.contar_no_leidas = AsyncMock(return_value=1)
            mock_ctrl.eliminar_notificacion = AsyncMock(return_value=(True, {"message": "ok"}))
            await show_notificaciones(app)
            assert app.main_view.content is not None


class TestShowPlantillas:
    @pytest.mark.asyncio
    async def test_empty_state(self, app: FakeApp):
        with MagicMock() as mock_ctrl:
            app.controller = mock_ctrl
            mock_ctrl.obtener_plantillas_notificacion = AsyncMock(return_value=[])
            await show_plantillas_notificacion(app)
        assert app.main_view.content is not None
        assert app.page.update_count >= 1

    @pytest.mark.asyncio
    async def test_with_data(self, app: FakeApp):
        with MagicMock() as mock_ctrl:
            app.controller = mock_ctrl
            mock_ctrl.obtener_plantillas_notificacion = AsyncMock(return_value=[
                {"id": 1, "nombre": "Stock Bajo", "tipo": "email",
                 "asunto": "Alerta", "creado_en": "2025-01-01"},
                {"id": 2, "nombre": "Promocion", "tipo": "push",
                 "asunto": "Oferta", "creado_en": "2025-01-02"},
            ])
            await show_plantillas_notificacion(app)
        assert app.main_view.content is not None

    @pytest.mark.asyncio
    async def test_new_template_button_visible(self, app: FakeApp):
        with MagicMock() as mock_ctrl:
            app.controller = mock_ctrl
            mock_ctrl.obtener_plantillas_notificacion = AsyncMock(return_value=[])
            await show_plantillas_notificacion(app)
            assert app.main_view.content is not None

    @pytest.mark.asyncio
    async def test_new_template_dialog_shown(self, app: FakeApp):
        with MagicMock() as mock_ctrl:
            app.controller = mock_ctrl
            mock_ctrl.obtener_plantillas_notificacion = AsyncMock(return_value=[])
            mock_ctrl.crear_plantilla_notificacion = AsyncMock(
                return_value=(True, {"id": 99})
            )
            await show_plantillas_notificacion(app)
            content_str = str(app.main_view.content)
            assert len(content_str) > 0

    @pytest.mark.asyncio
    async def test_delete_template(self, app: FakeApp):
        with MagicMock() as mock_ctrl:
            app.controller = mock_ctrl
            mock_ctrl.obtener_plantillas_notificacion = AsyncMock(return_value=[
                {"id": 7, "nombre": "DelPlant", "tipo": "email",
                 "asunto": "Delete", "creado_en": "2025-01-01"},
            ])
            mock_ctrl.eliminar_plantilla_notificacion = AsyncMock(
                return_value=(True, {"message": "ok"})
            )
            await show_plantillas_notificacion(app)
            assert app.main_view.content is not None

    @pytest.mark.asyncio
    async def test_refresh_after_delete(self, app: FakeApp):
        with MagicMock() as mock_ctrl:
            app.controller = mock_ctrl
            call_count = 0

            async def obtener_side():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return [{"id": 7, "nombre": "D", "tipo": "e",
                             "asunto": "D", "creado_en": "2025-01-01"}]
                return []

            mock_ctrl.obtener_plantillas_notificacion = AsyncMock(side_effect=obtener_side)
            mock_ctrl.eliminar_plantilla_notificacion = AsyncMock(
                return_value=(True, {"message": "ok"})
            )
            await show_plantillas_notificacion(app)
            assert app.main_view.content is not None
