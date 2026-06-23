"""Tests for core schemas and error handler."""

from __future__ import annotations

import pytest
from core.schemas import (
    ProductoData,
    ProveedorData,
    ClienteData,
    VentaData,
    UserData,
    AlmacenData,
    TransferenciaData,
    DevolucionData,
    LoteData,
    VarianteData,
    PlantillaReporteData,
)
from core.error_handler import handle_controller_errors
from utils.exceptions import (
    InventarioError,
    DatabaseException,
    ValidationException,
)


class TestSchemas:
    def test_producto_data_defaults(self):
        p = ProductoData(codigo="T1", nombre="Test")
        assert p.codigo == "T1"
        assert p.descripcion == ""
        assert p.stock_min == 0
        assert p.unidad_medida == "unidad"

    def test_producto_data_immutable(self):
        p = ProductoData(codigo="T2", nombre="Immutable")
        with pytest.raises(AttributeError):
            p.codigo = "changed"

    def test_proveedor_data(self):
        p = ProveedorData(nombre="Prov1", email="prov@test.com")
        assert p.nombre == "Prov1"
        assert p.telefono == ""

    def test_cliente_data(self):
        c = ClienteData(nombre="Client1")
        assert c.nombre == "Client1"
        assert c.direccion == ""

    def test_venta_data_defaults(self):
        v = VentaData(cliente_id=1)
        assert v.metodo_pago == "efectivo"
        assert v.items == []

    def test_user_data_defaults(self):
        u = UserData(username="user1", password="pass", nombre="User 1")
        assert u.rol_nombre == "operador"

    def test_almacen_data(self):
        a = AlmacenData(nombre="WH1", ubicacion="Floor 2")
        assert a.nombre == "WH1"

    def test_transferencia_data(self):
        t = TransferenciaData(almacen_origen_id=1, almacen_destino_id=2, producto_id=3, cantidad=10)
        assert t.nota == ""

    def test_lote_data(self):
        l = LoteData(producto_id=1, codigo_lote="L001")
        assert l.fecha_vencimiento is None

    def test_variante_data(self):
        v = VarianteData(producto_id=1, sku="SKU-001", atributos='{"talla":"M"}')
        assert v.precio_override is None

    def test_plantilla_reporte_data(self):
        p = PlantillaReporteData(nombre="Report1")
        assert p.modulo == "productos"
        assert p.columnas == []


class TestErrorHandler:
    @pytest.mark.asyncio
    async def test_inventario_error_passthrough(self, ctrl):
        @handle_controller_errors
        async def raise_error(self):
            raise DatabaseException("test error")

        with pytest.raises(DatabaseException, match="test error"):
            await raise_error(ctrl)

    @pytest.mark.asyncio
    async def test_generic_exception_wrapped(self, ctrl):
        @handle_controller_errors
        async def raise_generic(self):
            raise RuntimeError("something broke")

        with pytest.raises(InventarioError, match="raise_generic failed"):
            await raise_generic(ctrl)

    @pytest.mark.asyncio
    async def test_validation_error_wrapped(self, ctrl):
        @handle_controller_errors
        async def raise_validation(self):
            raise KeyError("missing_field")

        with pytest.raises(ValidationException):
            await raise_validation(ctrl)

    def test_sync_function_error(self, ctrl):
        @handle_controller_errors
        def sync_error(self):
            raise sqlite3.IntegrityError("constraint")

        import sqlite3

        with pytest.raises(DatabaseException):
            sync_error(ctrl)
