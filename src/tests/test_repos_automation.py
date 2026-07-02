"""Tests for AutomationRepository: config, forecasts, ABC, pricing."""

from __future__ import annotations

import pytest


@pytest.fixture
def automation_repo(ctrl):
    return ctrl.db.automation_repo


class TestAutomationRepository:
    def test_guardar_y_obtener_config(self, automation_repo):
        result = automation_repo.guardar_config("forecast_model", "prophet")
        assert result is True
        config = automation_repo.obtener_config()
        assert config.get("forecast_model") == "prophet"

    def test_guardar_config_overwrite(self, automation_repo):
        automation_repo.guardar_config("key1", "value1")
        automation_repo.guardar_config("key1", "value2")
        config = automation_repo.obtener_config()
        assert config["key1"] == "value2"

    def test_guardar_pronostico(self, automation_repo):
        forecast_id = automation_repo.guardar_pronostico(
            producto_id=1, periodo="2025-01", demanda=100.0
        )
        assert forecast_id > 0

    def test_obtener_pronosticos(self, automation_repo):
        automation_repo.guardar_pronostico(1, "2025-01", 100)
        forecasts = automation_repo.obtener_pronosticos(producto_id=1)
        assert len(forecasts) >= 1

    def test_clasificacion_abc(self, automation_repo):
        result = automation_repo.guardar_clasificacion_abc(1, "A", 50.0, 1)
        assert result is True

    def test_obtener_clasificaciones_abc(self, automation_repo):
        automation_repo.guardar_clasificacion_abc(1, "A", 50.0, 1)
        clasif = automation_repo.obtener_clasificaciones_abc()
        assert isinstance(clasif, list)

    def test_sugerencia_precio(self, automation_repo):
        result = automation_repo.guardar_sugerencia_precio(
            1, 15.0, 12.0, confianza=0.5, motivo="price_elasticity"
        )
        assert result > 0

    def test_obtener_sugerencias_precio(self, automation_repo):
        automation_repo.guardar_sugerencia_precio(1, 15.0, 12.0, 18.0, "elasticity")
        sugerencias = automation_repo.obtener_sugerencias_precio()
        assert isinstance(sugerencias, list)
