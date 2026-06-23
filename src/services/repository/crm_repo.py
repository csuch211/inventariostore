"""CRM repository for contacts, opportunities, and activities."""

from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CRMRepository(BaseRepository):
    """Repository for CRM operations."""

    # ============ Contactos ============

    def crear_contacto(
        self,
        nombre: str,
        apellido: str,
        email: str = "",
        telefono: str = "",
        cargo: str = "",
        empresa: str = "",
        fuente: str = "directo",
        cliente_id: int | None = None,
        notas: str = "",
        usuario: str = "system",
    ) -> dict:
        """Create a new contact."""
        now = datetime.now().isoformat()

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO contactos
                       (cliente_id, nombre, apellido, email, telefono, cargo,
                        empresa, fuente, notas, creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (cliente_id, nombre, apellido, email, telefono, cargo,
                     empresa, fuente, notas, now, usuario),
                )
                contacto_id = cursor.lastrowid
                self._audit_log(conn, "CREATE", "contactos", contacto_id, usuario,
                               f"Contacto {nombre} {apellido} creado")
                conn.commit()
            return {"id": contacto_id}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create contact: {e}")

    def obtener_contacto(self, contacto_id: int) -> dict | None:
        """Get contact by ID."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    """SELECT c.*, cl.nombre as cliente_nombre
                       FROM contactos c
                       LEFT JOIN clientes cl ON c.cliente_id = cl.id
                       WHERE c.id = ?""",
                    (contacto_id,),
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch contact: {e}")

    def obtener_contactos(self, empresa: str | None = None, estado: str = "activo") -> list[dict]:
        """List contacts."""
        try:
            with self._get_connection() as conn:
                where = ["c.estado = ?"]
                params = [estado]
                if empresa:
                    where.append("c.empresa = ?")
                    params.append(empresa)

                where_clause = " AND ".join(where)
                cursor = conn.execute(
                    f"""SELECT c.*, cl.nombre as cliente_nombre
                        FROM contactos c
                        LEFT JOIN clientes cl ON c.cliente_id = cl.id
                        WHERE {where_clause}
                        ORDER BY c.apellido, c.nombre""",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch contacts: {e}")

    def actualizar_contacto(self, contacto_id: int, **kwargs) -> bool:
        """Update contact."""
        try:
            updates = []
            values = []
            for key in ["nombre", "apellido", "email", "telefono", "cargo", "empresa", "fuente", "notas"]:
                if key in kwargs and kwargs[key] is not None:
                    updates.append(f"{key} = ?")
                    values.append(kwargs[key])

            if not updates:
                return True

            values.append(contacto_id)
            with self._get_connection() as conn:
                conn.execute(
                    f"UPDATE contactos SET {', '.join(updates)} WHERE id = ?",
                    values,
                )
                self._audit_log(conn, "UPDATE", "contactos", contacto_id,
                               kwargs.get("usuario", "system"), "Contacto actualizado")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to update contact: {e}")

    def eliminar_contacto(self, contacto_id: int, usuario: str = "system") -> bool:
        """Soft-delete contact."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE contactos SET estado = 'inactivo' WHERE id = ?",
                    (contacto_id,),
                )
                self._audit_log(conn, "DELETE", "contactos", contacto_id, usuario, "Contacto desactivado")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to deactivate contact: {e}")

    def buscar_contactos(self, query: str) -> list[dict]:
        """Search contacts by name, email, or company."""
        try:
            search_term = f"%{query}%"
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT c.*, cl.nombre as cliente_nombre
                       FROM contactos c
                       LEFT JOIN clientes cl ON c.cliente_id = cl.id
                       WHERE c.estado = 'activo' AND (
                           c.nombre LIKE ? OR c.apellido LIKE ? OR
                           c.email LIKE ? OR c.empresa LIKE ?
                       )
                       ORDER BY c.apellido, c.nombre""",
                    (search_term, search_term, search_term, search_term),
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to search contacts: {e}")

    # ============ Oportunidades ============

    def crear_oportunidad(
        self,
        contacto_id: int,
        titulo: str,
        monto: float = 0,
        prioridad: str = "media",
        fecha_cierre_estimada: str = "",
        notas: str = "",
        usuario: str = "system",
    ) -> dict:
        """Create a new opportunity."""
        now = datetime.now().isoformat()

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO oportunidades
                       (contacto_id, titulo, monto, prioridad,
                        fecha_cierre_estimada, notas, creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (contacto_id, titulo, monto, prioridad,
                     fecha_cierre_estimada, notas, now, usuario),
                )
                oportunidad_id = cursor.lastrowid
                self._audit_log(conn, "CREATE", "oportunidades", oportunidad_id, usuario,
                               f"Oportunidad '{titulo}' creada")
                conn.commit()
            return {"id": oportunidad_id}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create opportunity: {e}")

    def obtener_oportunidades(self, estado: str | None = None, contacto_id: int | None = None) -> list[dict]:
        """List opportunities."""
        try:
            with self._get_connection() as conn:
                where = []
                params = []
                if estado:
                    where.append("o.estado = ?")
                    params.append(estado)
                if contacto_id:
                    where.append("o.contacto_id = ?")
                    params.append(contacto_id)

                where_clause = " AND ".join(where) if where else "1=1"
                cursor = conn.execute(
                    f"""SELECT o.*, c.nombre, c.apellido, c.empresa
                        FROM oportunidades o
                        LEFT JOIN contactos c ON o.contacto_id = c.id
                        WHERE {where_clause}
                        ORDER BY o.fecha_cierre_estimada ASC""",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch opportunities: {e}")

    def actualizar_estado_oportunidad(
        self, oportunidad_id: int, nuevo_estado: str, usuario: str = "system"
    ) -> bool:
        """Update opportunity status."""
        valid_states = {"abierta", "ganada", "perdida", "cancelada"}
        if nuevo_estado not in valid_states:
            raise DatabaseException(f"Invalid opportunity state: {nuevo_estado}")

        try:
            updates = {"estado": nuevo_estado}
            if nuevo_estado in ("ganada", "perdida", "cancelada"):
                updates["fecha_cierre_real"] = datetime.now().isoformat()

            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [oportunidad_id]

            with self._get_connection() as conn:
                conn.execute(
                    f"UPDATE oportunidades SET {set_clause} WHERE id = ?",
                    values,
                )
                self._audit_log(conn, "UPDATE", "oportunidades", oportunidad_id, usuario,
                               f"Estado cambiado a {nuevo_estado}")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to update opportunity: {e}")

    def eliminar_oportunidad(self, oportunidad_id: int, usuario: str = "system") -> bool:
        """Delete opportunity."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM oportunidades WHERE id = ?", (oportunidad_id,))
                self._audit_log(conn, "DELETE", "oportunidades", oportunidad_id, usuario, "Oportunidad eliminada")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete opportunity: {e}")

    def pipeline_oportunidades(self) -> dict:
        """Get opportunity pipeline summary."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT estado, COUNT(*) as cantidad, COALESCE(SUM(monto), 0) as total
                       FROM oportunidades
                       GROUP BY estado"""
                )
                pipeline = {}
                for row in cursor.fetchall():
                    pipeline[row["estado"]] = {
                        "cantidad": row["cantidad"],
                        "total": row["total"],
                    }
                return pipeline
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch pipeline: {e}")

    # ============ Actividades de Seguimiento ============

    def crear_actividad(
        self,
        contacto_id: int,
        tipo: str,
        titulo: str,
        descripcion: str = "",
        fecha_programada: str = "",
        oportunidad_id: int | None = None,
        usuario: str = "system",
    ) -> dict:
        """Create a follow-up activity."""
        now = datetime.now().isoformat()

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO actividades_seguimiento
                       (contacto_id, oportunidad_id, tipo, titulo, descripcion,
                        fecha_programada, creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (contacto_id, oportunidad_id, tipo, titulo, descripcion,
                     fecha_programada, now, usuario),
                )
                actividad_id = cursor.lastrowid
                self._audit_log(conn, "CREATE", "actividades_seguimiento", actividad_id, usuario,
                               f"Actividad '{titulo}' creada")
                conn.commit()
            return {"id": actividad_id}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create activity: {e}")

    def obtener_actividades(
        self, contacto_id: int | None = None, estado: str | None = None
    ) -> list[dict]:
        """List follow-up activities."""
        try:
            with self._get_connection() as conn:
                where = []
                params = []
                if contacto_id:
                    where.append("a.contacto_id = ?")
                    params.append(contacto_id)
                if estado:
                    where.append("a.estado = ?")
                    params.append(estado)

                where_clause = " AND ".join(where) if where else "1=1"
                cursor = conn.execute(
                    f"""SELECT a.*, c.nombre, c.apellido
                        FROM actividades_seguimiento a
                        LEFT JOIN contactos c ON a.contacto_id = c.id
                        WHERE {where_clause}
                        ORDER BY a.fecha_programada ASC""",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch activities: {e}")

    def completar_actividad(
        self, actividad_id: int, resultado: str = "", usuario: str = "system"
    ) -> bool:
        """Mark activity as completed."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE actividades_seguimiento
                       SET estado = 'completada', fecha_completada = ?, resultado = ?
                       WHERE id = ?""",
                    (datetime.now().isoformat(), resultado, actividad_id),
                )
                self._audit_log(conn, "UPDATE", "actividades_seguimiento", actividad_id,
                               usuario, "Actividad completada")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to complete activity: {e}")

    # ============ Notas CRM ============

    def crear_nota(
        self,
        titulo: str,
        contenido: str,
        contacto_id: int | None = None,
        oportunidad_id: int | None = None,
        campana_id: int | None = None,
        tipo: str = "general",
        usuario: str = "system",
    ) -> dict:
        """Create a CRM note."""
        now = datetime.now().isoformat()

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO notas_crm
                       (contacto_id, oportunidad_id, campana_id, titulo, contenido, tipo,
                        creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (contacto_id, oportunidad_id, campana_id, titulo, contenido, tipo,
                     now, usuario),
                )
                nota_id = cursor.lastrowid
                conn.commit()
            return {"id": nota_id}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create note: {e}")

    def obtener_notas(
        self, contacto_id: int | None = None, oportunidad_id: int | None = None
    ) -> list[dict]:
        """List notes."""
        try:
            with self._get_connection() as conn:
                where = []
                params = []
                if contacto_id:
                    where.append("n.contacto_id = ?")
                    params.append(contacto_id)
                if oportunidad_id:
                    where.append("n.oportunidad_id = ?")
                    params.append(oportunidad_id)

                where_clause = " AND ".join(where) if where else "1=1"
                cursor = conn.execute(
                    f"""SELECT n.* FROM notas_crm n
                        WHERE {where_clause}
                        ORDER BY n.creado_en DESC""",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch notes: {e}")
