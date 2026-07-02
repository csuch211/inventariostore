"""Document repository for document management operations."""

import sqlite3
from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class DocumentRepository(BaseRepository):
    """Repository for document management operations."""

    # ============ Categorías de Documentos ============

    def crear_categoria_documento(
        self, nombre: str, descripcion: str = "", icono: str = "folder",
        color: str = "#2563EB", padre_id: int | None = None, usuario: str = "system",
    ) -> dict:
        """Create a document category."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO categorias_documentos
                       (nombre, descripcion, icono, color, padre_id, creado_en)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (nombre, descripcion, icono, color, padre_id, now),
                )
                categoria_id = cursor.lastrowid
                self._audit_log(conn, "CREATE", "categorias_documentos", categoria_id, usuario,
                               f"Categoría '{nombre}' creada")
                conn.commit()
            return {"id": categoria_id}
        except sqlite3.IntegrityError:
            raise DatabaseException(f"Category '{nombre}' already exists")
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create category: {e}")

    def obtener_categorias_documento(self) -> list[dict]:
        """List document categories."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT * FROM categorias_documentos WHERE activo = 1
                       ORDER BY nombre"""
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch categories: {e}")

    def eliminar_categoria_documento(self, categoria_id: int, usuario: str = "system") -> bool:
        """Soft-delete document category."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE categorias_documentos SET activo = 0 WHERE id = ?",
                    (categoria_id,),
                )
                self._audit_log(conn, "DELETE", "categorias_documentos", categoria_id, usuario,
                               "Categoría eliminada")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete category: {e}")

    # ============ Documentos ============

    def crear_documento(
        self,
        titulo: str,
        descripcion: str = "",
        categoria_id: int | None = None,
        tipo: str = "documento",
        archivo_nombre: str = "",
        archivo_ruta: str = "",
        archivo_tamano: int = 0,
        mime_type: str = "",
        tags: str = "",
        visibilidad: str = "privado",
        usuario: str = "system",
    ) -> dict:
        """Create a new document."""
        now = datetime.now().isoformat()

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO documentos
                       (titulo, descripcion, categoria_id, tipo, archivo_nombre,
                        archivo_ruta, archivo_tamano, mime_type, tags, visibilidad,
                        autor, creado_en, actualizado_en)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (titulo, descripcion, categoria_id, tipo, archivo_nombre,
                     archivo_ruta, archivo_tamano, mime_type, tags, visibilidad,
                     usuario, now, now),
                )
                documento_id = cursor.lastrowid

                # Create initial version
                conn.execute(
                    """INSERT INTO versiones_documento
                       (documento_id, numero_version, archivo_nombre, archivo_ruta,
                        archivo_tamano, cambios, autor, creado_en)
                       VALUES (?, 1, ?, ?, ?, ?, ?, ?)""",
                    (documento_id, archivo_nombre, archivo_ruta, archivo_tamano,
                     "Versión inicial", usuario, now),
                )

                self._audit_log(conn, "CREATE", "documentos", documento_id, usuario,
                               f"Documento '{titulo}' creado")
                conn.commit()
            return {"id": documento_id, "version": 1}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create document: {e}")

    def obtener_documento(self, documento_id: int) -> dict | None:
        """Get document by ID with tags."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    """SELECT d.*, cd.nombre as categoria_nombre
                       FROM documentos d
                       LEFT JOIN categorias_documentos cd ON d.categoria_id = cd.id
                       WHERE d.id = ?""",
                    (documento_id,),
                ).fetchone()
                if not row:
                    return None

                doc = dict(row)
                tags = conn.execute(
                    "SELECT tag FROM tags_documento WHERE documento_id = ?",
                    (documento_id,),
                ).fetchall()
                doc["tags_list"] = [t["tag"] for t in tags]
                return doc
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch document: {e}")

    def obtener_documentos(
        self,
        categoria_id: int | None = None,
        tipo: str | None = None,
        estado: str | None = None,
        autor: str | None = None,
    ) -> list[dict]:
        """List documents with filters."""
        try:
            with self._get_connection() as conn:
                where = []
                params = []
                if categoria_id:
                    where.append("d.categoria_id = ?")
                    params.append(categoria_id)
                if tipo:
                    where.append("d.tipo = ?")
                    params.append(tipo)
                if estado:
                    where.append("d.estado = ?")
                    params.append(estado)
                if autor:
                    where.append("d.autor = ?")
                    params.append(autor)

                _allowed_columns = {"d.categoria_id", "d.tipo", "d.estado", "d.autor"}
                for clause in where:
                    col = clause.split(None, 1)[0]
                    if col not in _allowed_columns:
                        raise ValueError(f"Columna no permitida en WHERE: {col}")
                where_clause = " AND ".join(where) if where else "1=1"
                cursor = conn.execute(
                    f"""SELECT d.*, cd.nombre as categoria_nombre
                        FROM documentos d
                        LEFT JOIN categorias_documentos cd ON d.categoria_id = cd.id
                        WHERE {where_clause}
                        ORDER BY d.actualizado_en DESC""",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch documents: {e}")

    def actualizar_documento(self, documento_id: int, **kwargs) -> bool:
        """Update document metadata."""
        try:
            updates = []
            values = []
            for key in ["titulo", "descripcion", "categoria_id", "tipo", "tags",
                        "estado", "visibilidad"]:
                if key in kwargs and kwargs[key] is not None:
                    updates.append(f"{key} = ?")
                    values.append(kwargs[key])

            if not updates:
                return True

            updates.append("actualizado_en = ?")
            values.append(datetime.now().isoformat())
            values.append(documento_id)

            with self._get_connection() as conn:
                conn.execute(
                    f"UPDATE documentos SET {', '.join(updates)} WHERE id = ?",
                    values,
                )
                self._audit_log(conn, "UPDATE", "documentos", documento_id,
                               kwargs.get("usuario", "system"), "Documento actualizado")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to update document: {e}")

    def eliminar_documento(self, documento_id: int, usuario: str = "system") -> bool:
        """Delete document."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM documentos WHERE id = ?", (documento_id,))
                self._audit_log(conn, "DELETE", "documentos", documento_id, usuario,
                               "Documento eliminado")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete document: {e}")

    def buscar_documentos(self, query: str) -> list[dict]:
        """Search documents by title, description, or tags."""
        try:
            search_term = f"%{query}%"
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT d.*, cd.nombre as categoria_nombre
                       FROM documentos d
                       LEFT JOIN categorias_documentos cd ON d.categoria_id = cd.id
                       WHERE d.titulo LIKE ? OR d.descripcion LIKE ? OR d.tags LIKE ?
                       ORDER BY d.actualizado_en DESC""",
                    (search_term, search_term, search_term),
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to search documents: {e}")

    # ============ Versiones ============

    def crear_version(
        self,
        documento_id: int,
        archivo_nombre: str = "",
        archivo_ruta: str = "",
        archivo_tamano: int = 0,
        cambios: str = "",
        usuario: str = "system",
    ) -> dict:
        """Create a new document version."""
        now = datetime.now().isoformat()

        try:
            with self._get_connection() as conn:
                # Get current version number
                row = conn.execute(
                    "SELECT version_actual FROM documentos WHERE id = ?",
                    (documento_id,),
                ).fetchone()
                new_version = (row["version_actual"] or 0) + 1 if row else 1

                # Create version record
                conn.execute(
                    """INSERT INTO versiones_documento
                       (documento_id, numero_version, archivo_nombre, archivo_ruta,
                        archivo_tamano, cambios, autor, creado_en)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (documento_id, new_version, archivo_nombre, archivo_ruta,
                     archivo_tamano, cambios, usuario, now),
                )

                # Update document version
                conn.execute(
                    "UPDATE documentos SET version_actual = ?, actualizado_en = ? WHERE id = ?",
                    (new_version, now, documento_id),
                )

                self._audit_log(conn, "CREATE", "versiones_documento", documento_id, usuario,
                               f"Versión {new_version} creada")
                conn.commit()
            return {"version": new_version}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create version: {e}")

    def obtener_versiones(self, documento_id: int) -> list[dict]:
        """List document versions."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT * FROM versiones_documento
                       WHERE documento_id = ?
                       ORDER BY numero_version DESC""",
                    (documento_id,),
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch versions: {e}")

    # ============ Tags ============

    def agregar_tag(self, documento_id: int, tag: str) -> bool:
        """Add a tag to a document."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO tags_documento (documento_id, tag) VALUES (?, ?)",
                    (documento_id, tag),
                )
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to add tag: {e}")

    def eliminar_tag(self, documento_id: int, tag: str) -> bool:
        """Remove a tag from a document."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "DELETE FROM tags_documento WHERE documento_id = ? AND tag = ?",
                    (documento_id, tag),
                )
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to remove tag: {e}")

    def buscar_por_tag(self, tag: str) -> list[dict]:
        """Find documents by tag."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT d.* FROM documentos d
                       JOIN tags_documento t ON d.id = t.documento_id
                       WHERE t.tag = ?
                       ORDER BY d.actualizado_en DESC""",
                    (tag,),
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to search by tag: {e}")

    def obtener_tags_populares(self, limit: int = 20) -> list[dict]:
        """Get most popular tags."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT tag, COUNT(*) as count
                       FROM tags_documento
                       GROUP BY tag
                       ORDER BY count DESC
                       LIMIT ?""",
                    (limit,),
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch popular tags: {e}")
