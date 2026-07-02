"""Tests for DocumentRepository: categories, documents, files."""

from __future__ import annotations

import pytest


@pytest.fixture
def doc_repo(ctrl):
    return ctrl.db.document_repo


class TestDocumentRepository:
    def test_crear_categoria(self, doc_repo):
        result = doc_repo.crear_categoria_documento(
            nombre="ReposFacturas", descripcion="Facturas emitidas"
        )
        assert "id" in result

    def test_crear_categoria_duplicate_raises(self, doc_repo):
        result = doc_repo.crear_categoria_documento(nombre="ReposUnica")
        assert "id" in result
        cats = doc_repo.obtener_categorias_documento()
        assert any(c["nombre"] == "ReposUnica" for c in cats)

    def test_obtener_categorias(self, doc_repo):
        doc_repo.crear_categoria_documento(nombre="Contratos")
        cats = doc_repo.obtener_categorias_documento()
        assert isinstance(cats, list)
        assert len(cats) >= 1

    def test_eliminar_categoria(self, doc_repo):
        created = doc_repo.crear_categoria_documento(nombre="TempCat")
        result = doc_repo.eliminar_categoria_documento(created["id"])
        assert result is True

    def test_crear_documento(self, doc_repo):
        cat = doc_repo.crear_categoria_documento(nombre="ReposDocs1")
        result = doc_repo.crear_documento(
            titulo="Contrato 2025",
            categoria_id=cat["id"],
            archivo_ruta="/tmp/contrato.pdf",
            usuario="tester",
        )
        assert "id" in result

    def test_obtener_documentos(self, doc_repo):
        cat = doc_repo.crear_categoria_documento(nombre="ReposDocs2")
        doc_repo.crear_documento(
            titulo="Doc 1", categoria_id=cat["id"], archivo_ruta="/tmp/doc1.pdf"
        )
        docs = doc_repo.obtener_documentos()
        assert isinstance(docs, list)
        assert len(docs) >= 1

    def test_eliminar_documento(self, doc_repo):
        cat = doc_repo.crear_categoria_documento(nombre="ReposDocs3")
        created = doc_repo.crear_documento(
            titulo="Del Doc", categoria_id=cat["id"], archivo_ruta="/tmp/del.pdf"
        )
        result = doc_repo.eliminar_documento(created["id"])
        assert result is True

    def test_actualizar_documento(self, doc_repo):
        cat = doc_repo.crear_categoria_documento(nombre="ReposDocs4")
        created = doc_repo.crear_documento(
            titulo="Old Name", categoria_id=cat["id"], archivo_ruta="/tmp/old.pdf"
        )
        result = doc_repo.actualizar_documento(created["id"], titulo="New Name")
        assert result is True
