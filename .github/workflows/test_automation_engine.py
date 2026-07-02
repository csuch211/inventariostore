"""
Tests for the automation engine and its individual tasks.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.controllers.automation_controller import AutomationController
from services.permissions import Perm


@pytest.fixture
def automation_controller(ctrl) -> AutomationController:
    """Provides an AutomationController instance with mocked dependencies."""
    # Mock repositories to isolate controller logic
    ctrl.db.product_repo = MagicMock()
    ctrl.db.config_repo = MagicMock()
    ctrl.db.sale_repo = MagicMock()
    ctrl.db.client_repo = MagicMock()

    # Mock config to enable all automation tasks and set a short interval
    def get_config_side_effect(key, default=None):
        if key.endswith("_enabled"):
            return "true"
        if key == "auto_run_interval":
            return "0.01"  # Use a very short interval for testing
        return default

    ctrl.db.config_repo.obtener_config.side_effect = get_config_side_effect

    return AutomationController(
        db=ctrl.db,
        user_repo=ctrl.db.user_repo,
        current_user="test_automation_user",
        current_user_permissions=set(Perm.get_all()),
    )


@pytest.mark.asyncio
async def test_run_single_automation_task_abc_classification(automation_controller):
    """Verify that a single automation task (ABC classification) can be executed."""
    # --- Arrange ---
    controller = automation_controller
    # Mock the underlying repo method to check if it's called
    controller.db.product_repo.actualizar_clasificacion_abc = AsyncMock()

    # --- Act ---
    await controller.ejecutar_clasificacion_abc()

    # --- Assert ---
    controller.db.product_repo.actualizar_clasificacion_abc.assert_awaited_once()


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_automation_engine_runs_tasks_in_loop(mock_sleep, automation_controller):
    """
    Verify that the automation engine starts, runs enabled tasks in a loop,
    and can be stopped.
    """
    # --- Arrange ---
    controller = automation_controller

    # Patch the individual task methods to check if they are called by the engine
    controller.ejecutar_clasificacion_abc = AsyncMock()
    controller.generar_pronosticos_demanda = AsyncMock()

    # --- Act ---
    # Start the engine in the background
    engine_task = asyncio.create_task(controller.iniciar_motor_automation())

    # Let the engine run for a couple of "ticks"
    await asyncio.sleep(0.03)

    # Stop the engine
    await controller.detener_motor_automation()
    await engine_task  # Wait for the engine task to finish cleanly

    # --- Assert ---
    # Verify that the tasks were called at least once
    controller.ejecutar_clasificacion_abc.assert_awaited()
    controller.generar_pronosticos_demanda.assert_awaited()
    # Verify that asyncio.sleep was called, indicating the loop was running
    mock_sleep.assert_awaited()