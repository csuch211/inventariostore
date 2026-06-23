"""
Phase 3 controller for variants, reports, push, i18n, and image search
"""

from collections.abc import Callable

from services import phase3_db
from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.i18n import set_locale
from utils.logger import setup_logger

logger = setup_logger(__name__)


class Phase3Controller:
    """Phase 3 features controller"""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Phase3 Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Fase 3: Variantes de producto ============

    @require_permission(Perm.VARIANTES_GESTIONAR)
    async def crear_variante(
        self,
        producto_id: int,
        sku: str,
        atributos: dict[str, str],
        cantidad: int = 0,
        precio_override: float | None = None,
    ) -> tuple[bool, dict]:
        try:
            vid = phase3_db.crear_variante(
                self.db,
                producto_id=producto_id,
                sku=sku,
                atributos=atributos,
                cantidad=cantidad,
                precio_override=precio_override,
                usuario=self.current_user or "system",
            )
            return True, {"id": vid}
        except Exception as e:
            logger.error(f"Error creating variant: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.VARIANTES_LEER)
    async def obtener_variantes(
        self,
        producto_id: int | None = None,
        sku: str | None = None,
        solo_activas: bool = True,
    ) -> list[dict]:
        try:
            return phase3_db.obtener_variantes(
                self.db,
                producto_id=producto_id,
                sku=sku,
                solo_activas=solo_activas,
            )
        except Exception as e:
            logger.error(f"Error fetching variants: {e}")
            return []

    @require_permission(Perm.VARIANTES_GESTIONAR)
    async def actualizar_stock_variante(
        self,
        variante_id: int,
        cantidad: int,
    ) -> tuple[bool, dict]:
        try:
            res = phase3_db.actualizar_stock_variante(
                self.db,
                variante_id=variante_id,
                cantidad=cantidad,
                usuario=self.current_user or "system",
            )
            return True, res
        except Exception as e:
            logger.error(f"Error updating variant stock: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.VARIANTES_GESTIONAR)
    async def eliminar_variante(self, variante_id: int) -> tuple[bool, dict]:
        try:
            phase3_db.eliminar_variante(
                self.db,
                variante_id=variante_id,
                usuario=self.current_user or "system",
            )
            return True, {"message": "Variante desactivada"}
        except Exception as e:
            logger.error(f"Error deleting variant: {e}")
            return False, {"error": str(e)}

    # ============ Fase 3: Reportes personalizables ============

    @require_permission(Perm.REPORTES_GUARDAR)
    async def guardar_plantilla_reporte(
        self,
        nombre: str,
        modulo: str,
        columnas: list[str],
        filtros: dict | None = None,
        agrupacion: str | None = None,
        ordenado_por: str | None = None,
    ) -> tuple[bool, dict]:
        try:
            pid = phase3_db.guardar_plantilla(
                self.db,
                nombre=nombre,
                modulo=modulo,
                columnas=columnas,
                filtros=filtros,
                agrupacion=agrupacion,
                ordenado_por=ordenado_por,
                usuario=self.current_user or "system",
            )
            return True, {"id": pid}
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.REPORTES_EJECUTAR)
    async def obtener_plantillas_reporte(self) -> list[dict]:
        try:
            return phase3_db.obtener_plantillas(self.db)
        except Exception as e:
            logger.error(f"Error fetching templates: {e}")
            return []

    @require_permission(Perm.REPORTES_GUARDAR)
    async def eliminar_plantilla_reporte(self, plantilla_id: int) -> tuple[bool, dict]:
        try:
            phase3_db.eliminar_plantilla(
                self.db,
                plantilla_id=plantilla_id,
                usuario=self.current_user or "system",
            )
            return True, {"message": "Plantilla eliminada"}
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.REPORTES_EJECUTAR)
    async def ejecutar_reporte(
        self,
        modulo: str,
        columnas: list[str],
        filtros: dict | None = None,
        agrupacion: str | None = None,
        ordenado_por: str | None = None,
    ) -> dict:
        try:
            return phase3_db.ejecutar_reporte(
                self.db,
                modulo=modulo,
                columnas=columnas,
                filtros=filtros,
                agrupacion=agrupacion,
                ordenado_por=ordenado_por,
            )
        except Exception as e:
            logger.error(f"Error executing report: {e}")
            return {"error": str(e)}

    @require_permission(Perm.REPORTES_EJECUTAR)
    async def obtener_modulos_reporte(self) -> list[dict]:
        """Return available report modules with their columns (whitelist)."""
        return [{"key": k, "columns": v} for k, v in phase3_db.REPORT_COLUMN_WHITELIST.items()]

    # ============ Fase 3: i18n persistente ============
    # These methods are intentionally not gated by a permission decorator.
    # Language is changed by the sidebar `LangSwitcher` (ui/components.py)
    # for any logged-in user. Keep the API available for the FastAPI routes.

    async def obtener_idioma_usuario(self, usuario: str) -> str:
        try:
            return phase3_db.obtener_idioma_usuario(self.db, usuario=usuario)
        except Exception as e:
            logger.error(f"Error fetching user lang: {e}")
            return "es"

    async def cambiar_idioma(self, usuario: str, idioma: str) -> tuple[bool, dict]:
        """Persist user's language preference and switch the active locale."""
        try:
            phase3_db.guardar_idioma_usuario(self.db, usuario=usuario, idioma=idioma)
            # Switch the global i18n singleton in the same process so the UI
            # re-renders with the new strings on the next `t()` call.

            set_locale(idioma)
            return True, {"idioma": idioma}
        except Exception as e:
            logger.error(f"Error changing lang: {e}")
            return False, {"error": str(e)}

    async def obtener_idiomas_disponibles(self) -> list[dict]:
        return [
            {"code": "es", "name": "Español"},
            {"code": "en", "name": "English"},
        ]

    # ============ Fase 3: Búsqueda por imagen ============

    @require_permission(Perm.IMAGE_SEARCH)
    async def buscar_por_imagen(
        self,
        ruta_imagen: str,
        extractor: Callable[[str], list[float]] | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        try:
            return phase3_db.buscar_por_similitud(
                self.db,
                ruta_imagen=ruta_imagen,
                extractor=extractor,
                top_k=top_k,
            )
        except Exception as e:
            logger.error(f"Error in image search: {e}")
            return []
