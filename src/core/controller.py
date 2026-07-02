"""
Lightweight facade that exposes domain controllers as public attributes.

InventarioController instantiates 19 domain controllers and delegates
``login``/``logout`` (the only methods with real logic).  All other calls
are resolved via ``__getattr__`` for backward compatibility — existing code
like ``await ctrl.crear_producto(...)`` continues to work without changes.

``current_user`` / ``current_user_permissions`` are propagated to all
children whenever they change (see ``_sync_children``).
"""

from core.controllers.accounting_controller import AccountingController
from core.controllers.admin_controller import AdminController
from core.controllers.advanced_inventory_controller import AdvancedInventoryController
from core.controllers.automation_controller import AutomationController
from core.controllers.cart_controller import CartController
from core.controllers.crm_controller import CRMController
from core.controllers.document_controller import DocumentController
from core.controllers.extended_features_controller import ExtendedFeaturesController
from core.controllers.hr_controller import HRController
from core.controllers.inventory_controller import InventoryController
from core.controllers.invoice_controller import InvoiceController
from core.controllers.notification_controller import NotificationController
from core.controllers.product_controller import ProductController
from core.controllers.purchasing_controller import PurchasingController
from core.controllers.report_controller import ReportController
from core.controllers.sales_controller import SalesController
from core.controllers.store_controller import StoreController
from core.controllers.warehouse_controller import WarehouseController
from modules.auth.controllers.auth_controller import AuthController
from modules.auth.services.auth_service import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from utils.logger import setup_logger

logger = setup_logger(__name__)


class InventarioController:
    """Main controller — thin facade over domain controllers."""

    def __init__(self):
        self.db = DatabaseManager()
        self.auth_service = AuthService(db=self.db)
        self.export_service = ExportService()

        deps = (self.db, self.auth_service, self.export_service)

        # Public sub-controllers (accessible as ctrl.products, ctrl.sales, …)
        self.auth = AuthController(*deps)
        self.products = ProductController(*deps)
        self.sales = SalesController(*deps)
        self.warehouse = WarehouseController(*deps)
        self.reports = ReportController(*deps)
        self.admin = AdminController(*deps)
        self.advanced_inventory = AdvancedInventoryController(*deps)
        self.extended_features = ExtendedFeaturesController(*deps)
        self.invoices = InvoiceController(*deps)
        self.accounting = AccountingController(*deps)
        self.inventory = InventoryController(*deps)
        self.hr = HRController(*deps)
        self.purchasing = PurchasingController(*deps)
        self.crm = CRMController(*deps)
        self.documents = DocumentController(*deps)
        self.notifications = NotificationController(*deps)
        self.cart = CartController(*deps)
        self.store = StoreController(*deps)
        self.automation = AutomationController(*deps)

        self._sub_controllers = [
            self.auth, self.products, self.sales, self.warehouse,
            self.reports, self.admin, self.advanced_inventory, self.extended_features,
            self.invoices, self.accounting, self.inventory, self.hr,
            self.purchasing, self.crm, self.documents, self.notifications,
            self.cart, self.store, self.automation,
        ]

        # Private aliases for backward compatibility (tests access these)
        self._auth = self.auth
        self._products = self.products
        self._sales = self.sales
        self._warehouse = self.warehouse
        self._reports = self.reports
        self._admin = self.admin
        self._advanced_inventory = self.advanced_inventory
        self._extended_features = self.extended_features
        self._invoices = self.invoices
        self._accounting = self.accounting
        self._inventory = self.inventory
        self._hr = self.hr
        self._purchasing = self.purchasing
        self._crm = self.crm
        self._documents = self.documents
        self._notifications = self.notifications
        self._cart = self.cart
        self._store = self.store
        self._automation = self.automation

        # Method aliases where the old facade renamed methods
        self.obtener_config_automation = self.automation.obtener_config
        self.guardar_config_automation = self.automation.guardar_config
        self.iniciar_motor_automation = self.automation.iniciar_motor
        self.detener_motor_automation = self.automation.detener_motor
        self.motor_automation_activo = self.automation.motor_esta_corriendo
        self.ejecutar_todas_automatizaciones = self.automation.ejecutar_todo
        self.obtener_reordenes = self.automation.obtener_reordenes
        self.sincronizar_stock_tienda = self.automation.sincronizar_stock_tienda
        self.generar_pronosticos_demanda = self.automation.generar_pronosticos
        self.ejecutar_clasificacion_abc = self.automation.ejecutar_clasificacion_abc
        self.generar_sugerencias_precio = self.automation.generar_sugerencias_precio
        self.aplicar_sugerencia_precio = self.automation.aplicar_sugerencia_precio
        self.rechazar_sugerencia_precio = self.automation.rechazar_sugerencia_precio
        self.ejecutar_segmentacion_clientes = self.automation.ejecutar_segmentacion_clientes
        self.obtener_segmentos_clientes = self.automation.obtener_segmentos_clientes

        # Notification aliases (old facade added _notificacion suffix)
        self.crear_plantilla_notificacion = self.notifications.crear_plantilla
        self.obtener_plantillas_notificacion = self.notifications.obtener_plantillas
        self.eliminar_plantilla_notificacion = self.notifications.eliminar_plantilla
        self.crear_canal_notificacion = self.notifications.crear_canal
        self.obtener_canales_notificacion = self.notifications.obtener_canales
        self.obtener_preferencias_notificacion = self.notifications.obtener_preferencias
        self.guardar_preferencias_notificacion = self.notifications.guardar_preferencias

        self._current_user = None
        self._current_user_role = None
        self._current_user_permissions: set[str] = set()
        logger.info("Inventory Controller initialized")

    # ---- Properties with child sync ----

    @property
    def current_user(self):
        return self._current_user

    @current_user.setter
    def current_user(self, value):
        self._current_user = value
        self._sync_children()

    @property
    def current_user_role(self):
        return self._current_user_role

    @current_user_role.setter
    def current_user_role(self, value):
        self._current_user_role = value

    @property
    def current_user_permissions(self):
        return self._current_user_permissions

    @current_user_permissions.setter
    def current_user_permissions(self, value):
        self._current_user_permissions = value
        self._sync_children()

    def _sync_children(self):
        for ctrl in self._sub_controllers:
            ctrl.current_user = self._current_user
            ctrl.current_user_role = self._current_user_role
            ctrl.current_user_permissions = self._current_user_permissions

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ---- Authentication (only methods with real logic) ----

    async def login(self, username: str, password: str) -> dict:
        result = await self.auth.login(username, password)
        self._current_user = username
        self._current_user_role = result.get("rol", "operador")
        self._current_user_permissions = set(result.get("permissions", []))
        self._sync_children()
        return result

    async def logout(self, token: str):
        await self.auth.logout(token)
        self._current_user = None
        self._current_user_role = None
        self._current_user_permissions = set()
        self._sync_children()

    # ---- Backward compatibility: delegate unknown attrs to sub-controllers ----

    def __getattr__(self, name: str):
        # Avoid infinite recursion on already-set private attrs
        if name.startswith("_"):
            raise AttributeError(f"'InventarioController' has no attribute '{name}'")
        for sub in self._sub_controllers:
            if hasattr(sub, name):
                return getattr(sub, name)
        raise AttributeError(f"'InventarioController' has no attribute '{name}'")
