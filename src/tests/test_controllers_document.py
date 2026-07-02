"""Tests for DocumentController."""

from __future__ import annotations

import pytest


class TestDocumentController:
    @pytest.mark.asyncio
    async def test_crear_categoria_documento(self, ctrl):
        success, _result = await ctrl.crear_categoria_documento(
            nombre="Facturas", descripcion="Facturas emitidas"
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_categorias_documento(self, ctrl):
        result = await ctrl.obtener_categorias_documento()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_crear_documento(self, ctrl):
        _, cat = await ctrl.crear_categoria_documento(nombre="Docs")
        success, _result = await ctrl.crear_documento(
            titulo="Contrato.pdf", categoria_id=cat["id"],
            archivo_ruta="/tmp/contrato.pdf"
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_documentos(self, ctrl):
        result = await ctrl.obtener_documentos()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_eliminar_documento(self, ctrl):
        _, cat = await ctrl.crear_categoria_documento(nombre="DelCat")
        _, doc = await ctrl.crear_documento(
            titulo="DelMe.pdf", categoria_id=cat["id"], archivo_ruta="/tmp/del.pdf"
        )
        success, _ = await ctrl.eliminar_documento(doc["id"])
        assert success is True
