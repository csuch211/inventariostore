"""Employee repository for HR operations."""

import sqlite3
from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class EmployeeRepository(BaseRepository):
    """Repository for employee CRUD operations."""

    def _next_employee_number(self) -> str:
        """Generate the next sequential employee number."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM empleados").fetchone()
            seq = (row["cnt"] or 0) + 1
        return f"EMP-{seq:04d}"

    def crear_empleado(
        self,
        nombre: str,
        apellido: str,
        email: str = "",
        telefono: str = "",
        fecha_nacimiento: str = "",
        fecha_ingreso: str = "",
        puesto: str = "",
        departamento: str = "",
        salario_base: float = 0,
        notas: str = "",
        usuario: str = "system",
    ) -> dict:
        """Create a new employee."""
        numero = self._next_employee_number()
        now = datetime.now().isoformat()
        if not fecha_ingreso:
            fecha_ingreso = now

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO empleados
                       (numero_empleado, nombre, apellido, email, telefono,
                        fecha_nacimiento, fecha_ingreso, puesto, departamento,
                        salario_base, notas, creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (numero, nombre, apellido, email, telefono,
                     fecha_nacimiento, fecha_ingreso, puesto, departamento,
                     salario_base, notas, now, usuario),
                )
                empleado_id = cursor.lastrowid
                self._audit_log(conn, "CREATE", "empleados", empleado_id, usuario,
                               f"Empleado {numero} creado: {nombre} {apellido}")
                conn.commit()
            return {"id": empleado_id, "numero_empleado": numero}
        except sqlite3.IntegrityError:
            raise DatabaseException(f"Employee number {numero} already exists")
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create employee: {e}")

    def obtener_empleado(self, empleado_id: int) -> dict | None:
        """Get employee by ID."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM empleados WHERE id = ?", (empleado_id,)
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch employee: {e}")

    def obtener_empleados(self, departamento: str | None = None, estado: str = "activo") -> list[dict]:
        """List employees with optional filters."""
        try:
            with self._get_connection() as conn:
                where = ["estado = ?"]
                params = [estado]
                if departamento:
                    where.append("departamento = ?")
                    params.append(departamento)

                _allowed_columns = {"estado", "departamento"}
                for clause in where:
                    col = clause.split(None, 1)[0]
                    if col not in _allowed_columns:
                        raise ValueError(f"Columna no permitida en WHERE: {col}")
                where_clause = " AND ".join(where)
                cursor = conn.execute(
                    f"SELECT * FROM empleados WHERE {where_clause} ORDER BY apellido, nombre",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch employees: {e}")

    def actualizar_empleado(
        self,
        empleado_id: int,
        nombre: str | None = None,
        apellido: str | None = None,
        email: str | None = None,
        telefono: str | None = None,
        puesto: str | None = None,
        departamento: str | None = None,
        salario_base: float | None = None,
        usuario: str = "system",
    ) -> bool:
        """Update employee."""
        try:
            updates = []
            values = []
            if nombre is not None:
                updates.append("nombre = ?")
                values.append(nombre)
            if apellido is not None:
                updates.append("apellido = ?")
                values.append(apellido)
            if email is not None:
                updates.append("email = ?")
                values.append(email)
            if telefono is not None:
                updates.append("telefono = ?")
                values.append(telefono)
            if puesto is not None:
                updates.append("puesto = ?")
                values.append(puesto)
            if departamento is not None:
                updates.append("departamento = ?")
                values.append(departamento)
            if salario_base is not None:
                updates.append("salario_base = ?")
                values.append(salario_base)

            if not updates:
                return True

            values.append(empleado_id)
            with self._get_connection() as conn:
                conn.execute(
                    f"UPDATE empleados SET {', '.join(updates)} WHERE id = ?",
                    values,
                )
                self._audit_log(conn, "UPDATE", "empleados", empleado_id, usuario, "Empleado actualizado")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to update employee: {e}")

    def eliminar_empleado(self, empleado_id: int, usuario: str = "system") -> bool:
        """Soft-delete employee."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE empleados SET estado = 'inactivo' WHERE id = ?",
                    (empleado_id,),
                )
                self._audit_log(conn, "DELETE", "empleados", empleado_id, usuario, "Empleado desactivado")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to deactivate employee: {e}")

    def obtener_departamentos(self) -> list[str]:
        """Get list of unique departments."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT DISTINCT departamento FROM empleados WHERE estado = 'activo' ORDER BY departamento"
                )
                return [r["departamento"] for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch departments: {e}")

    def contar_empleados(self, departamento: str | None = None) -> int:
        """Count employees."""
        try:
            with self._get_connection() as conn:
                if departamento:
                    row = conn.execute(
                        "SELECT COUNT(*) as cnt FROM empleados WHERE estado = 'activo' AND departamento = ?",
                        (departamento,),
                    ).fetchone()
                else:
                    row = conn.execute(
                        "SELECT COUNT(*) as cnt FROM empleados WHERE estado = 'activo'"
                    ).fetchone()
                return row["cnt"] or 0
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to count employees: {e}")
