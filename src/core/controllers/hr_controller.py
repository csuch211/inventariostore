"""HR controller for human resources management."""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


class HRController:
    """Controller for HR operations."""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("HR Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Empleados ============

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def crear_empleado(self, **kwargs) -> tuple[bool, dict]:
        """Create a new employee."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.employee_repo.crear_empleado(**kwargs)
            return True, result
        except Exception as e:
            logger.exception(f"Error creating employee: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_LEER)
    async def obtener_empleado(self, empleado_id: int) -> dict | None:
        """Get employee by ID."""
        try:
            return self.db.employee_repo.obtener_empleado(empleado_id)
        except Exception as e:
            logger.exception(f"Error fetching employee: {e}")
            return None

    @require_permission(Perm.USUARIOS_LEER)
    async def obtener_empleados(
        self, departamento: str | None = None, estado: str = "activo"
    ) -> list[dict]:
        """List employees."""
        try:
            return self.db.employee_repo.obtener_empleados(departamento=departamento, estado=estado)
        except Exception as e:
            logger.exception(f"Error fetching employees: {e}")
            return []

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def actualizar_empleado(self, empleado_id: int, **kwargs) -> tuple[bool, dict]:
        """Update employee."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            self.db.employee_repo.actualizar_empleado(empleado_id, **kwargs)
            return True, {"message": "Employee updated"}
        except Exception as e:
            logger.exception(f"Error updating employee: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def eliminar_empleado(self, empleado_id: int) -> tuple[bool, dict]:
        """Deactivate employee."""
        try:
            self.db.employee_repo.eliminar_empleado(empleado_id, usuario=self.current_user or "system")
            return True, {"message": "Employee deactivated"}
        except Exception as e:
            logger.exception(f"Error deactivating employee: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_LEER)
    async def obtener_departamentos(self) -> list[str]:
        """Get list of departments."""
        try:
            return self.db.employee_repo.obtener_departamentos()
        except Exception as e:
            logger.exception(f"Error fetching departments: {e}")
            return []

    # ============ Nómina ============

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def crear_nomina(self, **kwargs) -> tuple[bool, dict]:
        """Create payroll record."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.hr_repo.crear_nomina(**kwargs)
            return True, result
        except Exception as e:
            logger.exception(f"Error creating payroll: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_LEER)
    async def obtener_nomina(
        self, empleado_id: int | None = None, periodo: str | None = None
    ) -> list[dict]:
        """List payroll records."""
        try:
            return self.db.hr_repo.obtener_nomina(empleado_id=empleado_id, periodo=periodo)
        except Exception as e:
            logger.exception(f"Error fetching payroll: {e}")
            return []

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def aprobar_nomina(self, nomina_id: int) -> tuple[bool, dict]:
        """Approve payroll."""
        try:
            self.db.hr_repo.aprobar_nomina(nomina_id, usuario=self.current_user or "system")
            return True, {"message": "Payroll approved"}
        except Exception as e:
            logger.exception(f"Error approving payroll: {e}")
            return False, {"error": str(e)}

    # ============ Asistencia ============

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def registrar_asistencia(self, **kwargs) -> tuple[bool, dict]:
        """Register attendance."""
        try:
            result = self.db.hr_repo.registrar_asistencia(**kwargs)
            return True, result
        except Exception as e:
            logger.exception(f"Error registering attendance: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_LEER)
    async def obtener_asistencia(
        self, empleado_id: int | None = None,
        fecha_inicio: str | None = None, fecha_fin: str | None = None
    ) -> list[dict]:
        """List attendance records."""
        try:
            return self.db.hr_repo.obtener_asistencia(
                empleado_id=empleado_id, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin
            )
        except Exception as e:
            logger.exception(f"Error fetching attendance: {e}")
            return []

    @require_permission(Perm.USUARIOS_LEER)
    async def calcular_horas_empleado(
        self, empleado_id: int, fecha_inicio: str, fecha_fin: str
    ) -> dict:
        """Calculate employee hours."""
        try:
            return self.db.hr_repo.calcular_horas_empleado(empleado_id, fecha_inicio, fecha_fin)
        except Exception as e:
            logger.exception(f"Error calculating hours: {e}")
            return {"total_horas": 0, "total_extras": 0, "dias_trabajados": 0}

    # ============ Vacaciones ============

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def solicitar_vacaciones(self, **kwargs) -> tuple[bool, dict]:
        """Request vacation."""
        try:
            result = self.db.hr_repo.solicitar_vacaciones(**kwargs)
            return True, result
        except Exception as e:
            logger.exception(f"Error requesting vacation: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_LEER)
    async def obtener_vacaciones(
        self, empleado_id: int | None = None, estado: str | None = None
    ) -> list[dict]:
        """List vacation requests."""
        try:
            return self.db.hr_repo.obtener_vacaciones(empleado_id=empleado_id, estado=estado)
        except Exception as e:
            logger.exception(f"Error fetching vacations: {e}")
            return []

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def aprobar_vacaciones(self, vacacion_id: int) -> tuple[bool, dict]:
        """Approve vacation."""
        try:
            self.db.hr_repo.aprobar_vacaciones(
                vacacion_id, aprobado_por=self.current_user or "system",
                usuario=self.current_user or "system"
            )
            return True, {"message": "Vacation approved"}
        except Exception as e:
            logger.exception(f"Error approving vacation: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def rechazar_vacaciones(self, vacacion_id: int) -> tuple[bool, dict]:
        """Reject vacation."""
        try:
            self.db.hr_repo.rechazar_vacaciones(vacacion_id, usuario=self.current_user or "system")
            return True, {"message": "Vacation rejected"}
        except Exception as e:
            logger.exception(f"Error rejecting vacation: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_LEER)
    async def dias_vacaciones_disponibles(self, empleado_id: int) -> int:
        """Get available vacation days."""
        try:
            return self.db.hr_repo.dias_vacaciones_disponibles(empleado_id)
        except Exception as e:
            logger.exception(f"Error calculating vacation days: {e}")
            return 0

    # ============ Evaluaciones ============

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def crear_evaluacion(self, **kwargs) -> tuple[bool, dict]:
        """Create evaluation."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.hr_repo.crear_evaluacion(**kwargs)
            return True, result
        except Exception as e:
            logger.exception(f"Error creating evaluation: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_LEER)
    async def obtener_evaluaciones(self, empleado_id: int | None = None) -> list[dict]:
        """List evaluations."""
        try:
            return self.db.hr_repo.obtener_evaluaciones(empleado_id=empleado_id)
        except Exception as e:
            logger.exception(f"Error fetching evaluations: {e}")
            return []

    @require_permission(Perm.USUARIOS_LEER)
    async def promedio_evaluaciones(self, empleado_id: int) -> float:
        """Get average evaluation score."""
        try:
            return self.db.hr_repo.promedio_evaluaciones(empleado_id)
        except Exception as e:
            logger.exception(f"Error calculating average score: {e}")
            return 0
