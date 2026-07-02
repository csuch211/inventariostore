"""Controller for automation features — delegates to AutomationEngine + repo."""

from services.auth import AuthService
from services.automation.engine import AutomationEngine
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AutomationController:
    """Automation controller: rules engine, forecasting, ABC, segmentation, pricing."""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        self.engine = AutomationEngine(db)
        logger.info("Automation Controller initialized")

    # ── Config ─────────────────────────────────────────────────────────

    @require_permission(Perm.AUTOMATION_CONFIGURAR)
    async def obtener_config(self) -> dict[str, str]:
        return self.db.automation_repo.obtener_config()

    @require_permission(Perm.AUTOMATION_CONFIGURAR)
    async def guardar_config(self, clave: str, valor: str) -> bool:
        return self.db.automation_repo.guardar_config(clave, valor)

    # ── Engine lifecycle ───────────────────────────────────────────────

    @require_permission(Perm.AUTOMATION_EJECUTAR)
    async def iniciar_motor(self) -> bool:
        self.engine.start()
        return True

    @require_permission(Perm.AUTOMATION_EJECUTAR)
    async def detener_motor(self) -> bool:
        self.engine.stop()
        return True

    @require_permission(Perm.AUTOMATION_EJECUTAR)
    async def motor_esta_corriendo(self) -> bool:
        return self.engine._running

    @require_permission(Perm.AUTOMATION_EJECUTAR)
    async def ejecutar_todo(self) -> dict:
        return await self.engine.run_all()

    # ── Auto Reorder ───────────────────────────────────────────────────

    @require_permission(Perm.AUTOMATION_EJECUTAR)
    async def ejecutar_reorden_automatico(self, min_stock: int = 5) -> int:
        return self.engine.auto_reorder(min_stock)

    @require_permission(Perm.AUTOMATION_LEER)
    async def obtener_reordenes(self, estado: str | None = None) -> list[dict]:
        return self.db.automation_repo.obtener_reordenes(estado=estado)

    # ── Store Sync ─────────────────────────────────────────────────────

    @require_permission(Perm.AUTOMATION_EJECUTAR)
    async def sincronizar_stock_tienda(self) -> int:
        return self.engine.sync_store_stock()

    # ── Demand Forecast ────────────────────────────────────────────────

    @require_permission(Perm.AUTOMATION_EJECUTAR)
    async def generar_pronosticos(self) -> int:
        return self.engine.generate_forecasts()

    @require_permission(Perm.AUTOMATION_LEER)
    async def obtener_pronosticos(self, producto_id: int | None = None,
                                   periodo: str | None = None) -> list[dict]:
        return self.db.automation_repo.obtener_pronosticos(
            producto_id=producto_id, periodo=periodo
        )

    # ── ABC Classification ─────────────────────────────────────────────

    @require_permission(Perm.AUTOMATION_EJECUTAR)
    async def ejecutar_clasificacion_abc(self) -> int:
        return self.engine.classify_abc()

    @require_permission(Perm.AUTOMATION_LEER)
    async def obtener_clasificacion_abc(self, clasificacion: str | None = None) -> list[dict]:
        return self.db.automation_repo.obtener_clasificaciones_abc(clasificacion=clasificacion)

    # ── Pricing Suggestions ────────────────────────────────────────────

    @require_permission(Perm.AUTOMATION_EJECUTAR)
    async def generar_sugerencias_precio(self) -> int:
        return self.engine.suggest_prices()

    @require_permission(Perm.AUTOMATION_LEER)
    async def obtener_sugerencias_precio(self, estado: str | None = None) -> list[dict]:
        return self.db.automation_repo.obtener_sugerencias_precio(estado=estado)

    @require_permission(Perm.AUTOMATION_EJECUTAR)
    async def aplicar_sugerencia_precio(self, sugerencia_id: int) -> bool:
        return self.db.automation_repo.aplicar_sugerencia_precio(sugerencia_id)

    @require_permission(Perm.AUTOMATION_EJECUTAR)
    async def rechazar_sugerencia_precio(self, sugerencia_id: int) -> bool:
        return self.db.automation_repo.rechazar_sugerencia_precio(sugerencia_id)

    # ── Customer Segmentation ──────────────────────────────────────────

    @require_permission(Perm.AUTOMATION_EJECUTAR)
    async def ejecutar_segmentacion_clientes(self) -> int:
        return self.engine.segment_customers()

    @require_permission(Perm.AUTOMATION_LEER)
    async def obtener_segmentos_clientes(self, segmento: str | None = None) -> list[dict]:
        return self.db.automation_repo.obtener_segmentos_clientes(segmento=segmento)
