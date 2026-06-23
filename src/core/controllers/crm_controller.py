"""CRM controller for customer relationship management."""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CRMController:
    """Controller for CRM operations."""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("CRM Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Contactos ============

    @require_permission(Perm.CLIENTES_GESTIONAR)
    async def crear_contacto(self, **kwargs) -> tuple[bool, dict]:
        """Create a new contact."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.crm_repo.crear_contacto(**kwargs)
            return True, result
        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CLIENTES_LEER)
    async def obtener_contacto(self, contacto_id: int) -> dict | None:
        """Get contact by ID."""
        try:
            return self.db.crm_repo.obtener_contacto(contacto_id)
        except Exception as e:
            logger.error(f"Error fetching contact: {e}")
            return None

    @require_permission(Perm.CLIENTES_LEER)
    async def obtener_contactos(
        self, empresa: str | None = None, estado: str = "activo"
    ) -> list[dict]:
        """List contacts."""
        try:
            return self.db.crm_repo.obtener_contactos(empresa=empresa, estado=estado)
        except Exception as e:
            logger.error(f"Error fetching contacts: {e}")
            return []

    @require_permission(Perm.CLIENTES_GESTIONAR)
    async def actualizar_contacto(self, contacto_id: int, **kwargs) -> tuple[bool, dict]:
        """Update contact."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            self.db.crm_repo.actualizar_contacto(contacto_id, **kwargs)
            return True, {"message": "Contact updated"}
        except Exception as e:
            logger.error(f"Error updating contact: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CLIENTES_GESTIONAR)
    async def eliminar_contacto(self, contacto_id: int) -> tuple[bool, dict]:
        """Deactivate contact."""
        try:
            self.db.crm_repo.eliminar_contacto(contacto_id, usuario=self.current_user or "system")
            return True, {"message": "Contact deactivated"}
        except Exception as e:
            logger.error(f"Error deactivating contact: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CLIENTES_LEER)
    async def buscar_contactos(self, query: str) -> list[dict]:
        """Search contacts."""
        try:
            return self.db.crm_repo.buscar_contactos(query)
        except Exception as e:
            logger.error(f"Error searching contacts: {e}")
            return []

    # ============ Oportunidades ============

    @require_permission(Perm.CLIENTES_GESTIONAR)
    async def crear_oportunidad(self, **kwargs) -> tuple[bool, dict]:
        """Create a new opportunity."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.crm_repo.crear_oportunidad(**kwargs)
            return True, result
        except Exception as e:
            logger.error(f"Error creating opportunity: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CLIENTES_LEER)
    async def obtener_oportunidades(
        self, estado: str | None = None, contacto_id: int | None = None
    ) -> list[dict]:
        """List opportunities."""
        try:
            return self.db.crm_repo.obtener_oportunidades(
                estado=estado, contacto_id=contacto_id
            )
        except Exception as e:
            logger.error(f"Error fetching opportunities: {e}")
            return []

    @require_permission(Perm.CLIENTES_GESTIONAR)
    async def actualizar_estado_oportunidad(
        self, oportunidad_id: int, nuevo_estado: str
    ) -> tuple[bool, dict]:
        """Update opportunity status."""
        try:
            self.db.crm_repo.actualizar_estado_oportunidad(
                oportunidad_id, nuevo_estado, usuario=self.current_user or "system"
            )
            return True, {"message": "Opportunity updated"}
        except Exception as e:
            logger.error(f"Error updating opportunity: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CLIENTES_GESTIONAR)
    async def eliminar_oportunidad(self, oportunidad_id: int) -> tuple[bool, dict]:
        """Delete opportunity."""
        try:
            self.db.crm_repo.eliminar_oportunidad(
                oportunidad_id, usuario=self.current_user or "system"
            )
            return True, {"message": "Opportunity deleted"}
        except Exception as e:
            logger.error(f"Error deleting opportunity: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CLIENTES_LEER)
    async def pipeline_oportunidades(self) -> dict:
        """Get opportunity pipeline summary."""
        try:
            return self.db.crm_repo.pipeline_oportunidades()
        except Exception as e:
            logger.error(f"Error fetching pipeline: {e}")
            return {}

    # ============ Actividades ============

    @require_permission(Perm.CLIENTES_GESTIONAR)
    async def crear_actividad(self, **kwargs) -> tuple[bool, dict]:
        """Create a follow-up activity."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.crm_repo.crear_actividad(**kwargs)
            return True, result
        except Exception as e:
            logger.error(f"Error creating activity: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CLIENTES_LEER)
    async def obtener_actividades(
        self, contacto_id: int | None = None, estado: str | None = None
    ) -> list[dict]:
        """List activities."""
        try:
            return self.db.crm_repo.obtener_actividades(
                contacto_id=contacto_id, estado=estado
            )
        except Exception as e:
            logger.error(f"Error fetching activities: {e}")
            return []

    @require_permission(Perm.CLIENTES_GESTIONAR)
    async def completar_actividad(
        self, actividad_id: int, resultado: str = ""
    ) -> tuple[bool, dict]:
        """Complete an activity."""
        try:
            self.db.crm_repo.completar_actividad(
                actividad_id, resultado=resultado, usuario=self.current_user or "system"
            )
            return True, {"message": "Activity completed"}
        except Exception as e:
            logger.error(f"Error completing activity: {e}")
            return False, {"error": str(e)}

    # ============ Notas ============

    @require_permission(Perm.CLIENTES_GESTIONAR)
    async def crear_nota(self, **kwargs) -> tuple[bool, dict]:
        """Create a CRM note."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.crm_repo.crear_nota(**kwargs)
            return True, result
        except Exception as e:
            logger.error(f"Error creating note: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CLIENTES_LEER)
    async def obtener_notas(
        self, contacto_id: int | None = None, oportunidad_id: int | None = None
    ) -> list[dict]:
        """List notes."""
        try:
            return self.db.crm_repo.obtener_notas(
                contacto_id=contacto_id, oportunidad_id=oportunidad_id
            )
        except Exception as e:
            logger.error(f"Error fetching notes: {e}")
            return []
