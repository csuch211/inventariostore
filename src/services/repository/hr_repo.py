"""HR repository for payroll, attendance, vacations, and evaluations."""

from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class HRRepository(BaseRepository):
    """Repository for HR operations (payroll, attendance, vacations, evaluations)."""

    # ============ Nómina ============

    def crear_nomina(
        self,
        empleado_id: int,
        periodo_inicio: str,
        periodo_fin: str,
        salario_bruto: float,
        deducciones: float = 0,
        bonificaciones: float = 0,
        notas: str = "",
        usuario: str = "system",
    ) -> dict:
        """Create a payroll record."""
        salario_neto = salario_bruto - deducciones + bonificaciones
        now = datetime.now().isoformat()

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO nomina
                       (empleado_id, periodo_inicio, periodo_fin, salario_bruto,
                        deducciones, bonificaciones, salario_neto, notas,
                        creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (empleado_id, periodo_inicio, periodo_fin, salario_bruto,
                     deducciones, bonificaciones, salario_neto, notas, now, usuario),
                )
                nomina_id = cursor.lastrowid
                self._audit_log(conn, "CREATE", "nomina", nomina_id, usuario,
                               f"Nómina creada para empleado {empleado_id}")
                conn.commit()
            return {"id": nomina_id, "salario_neto": salario_neto}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create payroll: {e}")

    def obtener_nomina(self, empleado_id: int | None = None, periodo: str | None = None) -> list[dict]:
        """List payroll records."""
        try:
            with self._get_connection() as conn:
                where = []
                params = []
                if empleado_id:
                    where.append("n.empleado_id = ?")
                    params.append(empleado_id)
                if periodo:
                    where.append("n.periodo_inicio <= ? AND n.periodo_fin >= ?")
                    params.extend([periodo, periodo])

                where_clause = " AND ".join(where) if where else "1=1"
                cursor = conn.execute(
                    f"""SELECT n.*, e.nombre, e.apellido, e.numero_empleado
                        FROM nomina n
                        JOIN empleados e ON n.empleado_id = e.id
                        WHERE {where_clause}
                        ORDER BY n.periodo_inicio DESC""",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch payroll: {e}")

    def aprobar_nomina(self, nomina_id: int, usuario: str = "system") -> bool:
        """Approve a payroll record."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE nomina SET estado = 'aprobada' WHERE id = ?",
                    (nomina_id,),
                )
                self._audit_log(conn, "UPDATE", "nomina", nomina_id, usuario, "Nómina aprobada")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to approve payroll: {e}")

    # ============ Asistencia ============

    def registrar_asistencia(
        self,
        empleado_id: int,
        fecha: str,
        hora_entrada: str = "",
        hora_salida: str = "",
        notas: str = "",
        usuario: str = "system",
    ) -> dict:
        """Register attendance for an employee."""
        now = datetime.now().isoformat()

        # Calculate hours worked
        horas_trabajadas = 0
        if hora_entrada and hora_salida:
            try:
                from datetime import datetime as dt
                entrada = dt.strptime(hora_entrada, "%H:%M")
                salida = dt.strptime(hora_salida, "%H:%M")
                diff = (salida - entrada).seconds / 3600
                horas_trabajadas = max(0, diff)
            except ValueError:
                pass

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO asistencia
                       (empleado_id, fecha, hora_entrada, hora_salida,
                        horas_trabajadas, notas)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (empleado_id, fecha, hora_entrada, hora_salida,
                     horas_trabajadas, notas),
                )
                asistencia_id = cursor.lastrowid
                conn.commit()
            return {"id": asistencia_id, "horas_trabajadas": horas_trabajadas}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to register attendance: {e}")

    def obtener_asistencia(
        self, empleado_id: int | None = None, fecha_inicio: str | None = None, fecha_fin: str | None = None
    ) -> list[dict]:
        """List attendance records."""
        try:
            with self._get_connection() as conn:
                where = []
                params = []
                if empleado_id:
                    where.append("a.empleado_id = ?")
                    params.append(empleado_id)
                if fecha_inicio:
                    where.append("a.fecha >= ?")
                    params.append(fecha_inicio)
                if fecha_fin:
                    where.append("a.fecha <= ?")
                    params.append(fecha_fin)

                where_clause = " AND ".join(where) if where else "1=1"
                cursor = conn.execute(
                    f"""SELECT a.*, e.nombre, e.apellido, e.numero_empleado
                        FROM asistencia a
                        JOIN empleados e ON a.empleado_id = e.id
                        WHERE {where_clause}
                        ORDER BY a.fecha DESC""",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch attendance: {e}")

    def calcular_horas_empleado(self, empleado_id: int, fecha_inicio: str, fecha_fin: str) -> dict:
        """Calculate total hours for an employee in a date range."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    """SELECT
                       COALESCE(SUM(horas_trabajadas), 0) as total_horas,
                       COALESCE(SUM(horas_extras), 0) as total_extras,
                       COUNT(*) as dias_trabajados
                       FROM asistencia
                       WHERE empleado_id = ? AND fecha BETWEEN ? AND ?""",
                    (empleado_id, fecha_inicio, fecha_fin),
                ).fetchone()
                return dict(row) if row else {"total_horas": 0, "total_extras": 0, "dias_trabajados": 0}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to calculate hours: {e}")

    # ============ Vacaciones ============

    def solicitar_vacaciones(
        self,
        empleado_id: int,
        fecha_inicio: str,
        fecha_fin: str,
        motivo: str = "",
        usuario: str = "system",
    ) -> dict:
        """Request vacation leave."""
        # Calculate days
        try:
            from datetime import datetime as dt
            inicio = dt.strptime(fecha_inicio, "%Y-%m-%d")
            fin = dt.strptime(fecha_fin, "%Y-%m-%d")
            dias = (fin - inicio).days + 1
        except ValueError:
            dias = 1

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO vacaciones
                       (empleado_id, fecha_inicio, fecha_fin, dias, motivo)
                       VALUES (?, ?, ?, ?, ?)""",
                    (empleado_id, fecha_inicio, fecha_fin, dias, motivo),
                )
                vacacion_id = cursor.lastrowid
                conn.commit()
            return {"id": vacacion_id, "dias": dias}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to request vacation: {e}")

    def obtener_vacaciones(self, empleado_id: int | None = None, estado: str | None = None) -> list[dict]:
        """List vacation requests."""
        try:
            with self._get_connection() as conn:
                where = []
                params = []
                if empleado_id:
                    where.append("v.empleado_id = ?")
                    params.append(empleado_id)
                if estado:
                    where.append("v.estado = ?")
                    params.append(estado)

                where_clause = " AND ".join(where) if where else "1=1"
                cursor = conn.execute(
                    f"""SELECT v.*, e.nombre, e.apellido, e.numero_empleado
                        FROM vacaciones v
                        JOIN empleados e ON v.empleado_id = e.id
                        WHERE {where_clause}
                        ORDER BY v.fecha_inicio DESC""",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch vacations: {e}")

    def aprobar_vacaciones(self, vacacion_id: int, aprobado_por: str, usuario: str = "system") -> bool:
        """Approve vacation request."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE vacaciones SET estado = 'aprobada', aprobado_por = ? WHERE id = ?",
                    (aprobado_por, vacacion_id),
                )
                self._audit_log(conn, "UPDATE", "vacaciones", vacacion_id, usuario, "Vacaciones aprobadas")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to approve vacation: {e}")

    def rechazar_vacaciones(self, vacacion_id: int, usuario: str = "system") -> bool:
        """Reject vacation request."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE vacaciones SET estado = 'rechazada' WHERE id = ?",
                    (vacacion_id,),
                )
                self._audit_log(conn, "UPDATE", "vacaciones", vacacion_id, usuario, "Vacaciones rechazadas")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to reject vacation: {e}")

    def dias_vacaciones_disponibles(self, empleado_id: int, anio: int | None = None) -> int:
        """Calculate available vacation days for an employee."""
        if anio is None:
            anio = datetime.now().year

        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    """SELECT COALESCE(SUM(dias), 0) as dias_tomados
                       FROM vacaciones
                       WHERE empleado_id = ? AND estado = 'aprobada'
                       AND strftime('%Y', fecha_inicio) = ?""",
                    (empleado_id, str(anio)),
                ).fetchone()
                dias_tomados = row["dias_tomados"] or 0
                return max(0, 15 - dias_tomados)  # 15 days default
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to calculate vacation days: {e}")

    # ============ Evaluaciones ============

    def crear_evaluacion(
        self,
        empleado_id: int,
        evaluador: str,
        fecha: str,
        periodo: str = "",
        puntuacion: float = 0,
        fortalezas: str = "",
        areas_mejora: str = "",
        objetivos: str = "",
        notas: str = "",
        usuario: str = "system",
    ) -> dict:
        """Create an employee evaluation."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO evaluaciones
                       (empleado_id, evaluador, fecha, periodo, puntuacion,
                        fortalezas, areas_mejora, objetivos, notas)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (empleado_id, evaluador, fecha, periodo, puntuacion,
                     fortalezas, areas_mejora, objetivos, notas),
                )
                evaluacion_id = cursor.lastrowid
                self._audit_log(conn, "CREATE", "evaluaciones", evaluacion_id, usuario,
                               f"Evaluación creada para empleado {empleado_id}")
                conn.commit()
            return {"id": evaluacion_id}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create evaluation: {e}")

    def obtener_evaluaciones(self, empleado_id: int | None = None) -> list[dict]:
        """List evaluations."""
        try:
            with self._get_connection() as conn:
                if empleado_id:
                    cursor = conn.execute(
                        """SELECT ev.*, e.nombre, e.apellido
                           FROM evaluaciones ev
                           JOIN empleados e ON ev.empleado_id = e.id
                           WHERE ev.empleado_id = ?
                           ORDER BY ev.fecha DESC""",
                        (empleado_id,),
                    )
                else:
                    cursor = conn.execute(
                        """SELECT ev.*, e.nombre, e.apellido
                           FROM evaluaciones ev
                           JOIN empleados e ON ev.empleado_id = e.id
                           ORDER BY ev.fecha DESC"""
                    )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch evaluations: {e}")

    def promedio_evaluaciones(self, empleado_id: int) -> float:
        """Get average evaluation score for an employee."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT COALESCE(AVG(puntuacion), 0) as promedio FROM evaluaciones WHERE empleado_id = ?",
                    (empleado_id,),
                ).fetchone()
                return round(row["promedio"] or 0, 2)
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to calculate average score: {e}")
