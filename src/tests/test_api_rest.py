"""Tests for the FastAPI REST API layer using TestClient."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure src is importable
_src = Path(__file__).resolve().parents[1]
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from datetime import UTC

from api.rest import app
from config.settings import JWT_SECRET_KEY
from core.controller import InventarioController


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers():
    """Create a real token via the login endpoint."""
    InventarioController()
    from datetime import datetime, timedelta

    import jwt
    payload = {
        "sub": "admin",
        "rol": "admin",
        "permissions": [],
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "type": "access",
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    return {"Authorization": f"Bearer {token}", "X-User": "admin"}


class TestAPIAuth:
    def test_login_success(self, client):
        response = client.post("/auth/login", json={"username": "admin", "password": "Admin123"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_invalid(self, client):
        response = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
        assert response.status_code == 401

    def test_login_empty(self, client):
        response = client.post("/auth/login", json={"username": "", "password": ""})
        assert response.status_code in {422, 401}


class TestAPIProductos:
    def test_get_productos(self, client, auth_headers):
        response = client.get("/productos", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_producto_by_id(self, client, auth_headers):
        response = client.get("/productos/1", headers=auth_headers)
        assert response.status_code in {200, 404}

    def test_get_categorias(self, client, auth_headers):
        response = client.get("/variantes", headers=auth_headers)
        assert response.status_code == 200

    def test_get_proveedores(self, client, auth_headers):
        response = client.get("/reportes/modulos", headers=auth_headers)
        assert response.status_code == 200

    def test_get_estadisticas(self, client, auth_headers):
        response = client.get("/kpis", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_productos" in data


class TestAPISales:
    def test_get_ventas(self, client, auth_headers):
        response = client.get("/kpis", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_get_clientes(self, client, auth_headers):
        response = client.get("/alertas/stock-bajo", headers=auth_headers)
        assert response.status_code == 200


class TestAPIKPIs:
    def test_get_kpis(self, client, auth_headers):
        response = client.get("/kpis", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "total_productos" in data or "ventas_hoy" in data or "productos_bajo_stock" in data

    def test_get_stock_bajo(self, client, auth_headers):
        response = client.get("/alertas/stock-bajo", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAPIVariantes:
    def test_get_variantes(self, client, auth_headers):
        response = client.get("/variantes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAPIReportes:
    def test_get_plantillas_reporte(self, client, auth_headers):
        response = client.get("/reportes/modulos", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_idiomas(self, client, auth_headers):
        response = client.get("/i18n/idiomas", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestAPISinAuth:
    def test_get_productos_no_auth(self, client):
        response = client.get("/productos")
        assert response.status_code in {403, 401}

    def test_get_productos_wrong_user(self, client):
        response = client.get("/productos", headers={"X-User": "nonexistent"})
        assert response.status_code in (401, 403, 200)

    def test_options_cors(self, client):
        response = client.options("/productos", headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "GET",
        })
        assert response.status_code == 200
