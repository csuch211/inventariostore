# Arquitectura Modular por Funcionalidades — InventarioStore

## Objetivo

Organizar el sistema en módulos cohesivos basados en funcionalidades del negocio, mejorando la separación de responsabilidades y facilitando el mantenimiento.

---

## Estructura Modular Propuesta

```
src/
├── modules/
│   ├── auth/                    # Módulo de Autenticación y Usuarios
│   │   ├── controllers/
│   │   │   └── auth_controller.py
│   │   ├── services/
│   │   │   └── auth_service.py
│   │   ├── repositories/
│   │   │   └── user_repository.py
│   │   ├── ui/
│   │   │   ├── login_view.py
│   │   │   ├── register_view.py
│   │   │   └── forgot_password_view.py
│   │   └── __init__.py
│   │
│   ├── products/                # Módulo de Productos
│   │   ├── controllers/
│   │   │   └── product_controller.py
│   │   ├── services/
│   │   │   └── product_service.py
│   │   ├── repositories/
│   │   │   └── product_repository.py
│   │   ├── ui/
│   │   │   ├── product_list_view.py
│   │   │   ├── product_form_view.py
│   │   │   └── category_view.py
│   │   └── __init__.py
│   │
│   ├── inventory/               # Módulo de Inventario
│   │   ├── controllers/
│   │   │   └── inventory_controller.py
│   │   ├── services/
│   │   │   ├── inventory_service.py
│   │   │   ├── inventory_analysis.py
│   │   │   └── inventory_valuation.py
│   │   ├── repositories/
│   │   │   └── inventory_repository.py
│   │   ├── ui/
│   │   │   ├── stock_view.py
│   │   │   ├── inventory_operations.py
│   │   │   └── inventory_analysis_views.py
│   │   └── __init__.py
│   │
│   ├── warehouses/              # Módulo de Almacenes
│   │   ├── controllers/
│   │   │   └── warehouse_controller.py
│   │   ├── services/
│   │   │   └── warehouse_service.py
│   │   ├── repositories/
│   │   │   └── warehouse_repository.py
│   │   ├── ui/
│   │   │   ├── warehouse_view.py
│   │   │   └── transfer_view.py
│   │   └── __init__.py
│   │
│   ├── sales/                   # Módulo de Ventas
│   │   ├── controllers/
│   │   │   ├── sales_controller.py
│   │   │   └── sales_enhanced_controller.py
│   │   ├── services/
│   │   │   └── sales_service.py
│   │   ├── repositories/
│   │   │   └── sale_repository.py
│   │   ├── ui/
│   │   │   ├── sales_view.py
│   │   │   ├── pos_view.py
│   │   │   └── cart_views.py
│   │   └── __init__.py
│   │
│   ├── purchasing/              # Módulo de Compras
│   │   ├── controllers/
│   │   │   └── purchasing_controller.py
│   │   ├── services/
│   │   │   and purchasing_service.py
│   │   ├── repositories/
│   │   │   └── purchasing_repository.py
│   │   ├── ui/
│   │   │   └── purchasing_views.py
│   │   └── __init__.py
│   │
│   ├── invoicing/              # Módulo de Facturación
│   │   ├── controllers/
│   │   │   └── invoice_controller.py
│   │   ├── services/
│   │   │   └── invoice_service.py
│   │   ├── repositories/
│   │   │   └── invoice_repository.py
│   │   ├── ui/
│   │   │   └── invoice_views.py
│   │   └── __init__.py
│   │
│   ├── reports/                 # Módulo de Reportes
│   │   ├── controllers/
│   │   │   └── report_controller.py
│   │   ├── services/
│   │   │   ├── export_strategy.py
│   │   │   ├── financial_report_export.py
│   │   │   └── inventory_report_export.py
│   │   ├── ui/
│   │   │   ├── product_reports.py
│   │   │   ├── financial_reports.py
│   │   │   └── charts.py
│   │   └── __init__.py
│   │
│   ├── accounting/             # Módulo de Contabilidad
│   │   ├── controllers/
│   │   │   └── accounting_controller.py
│   │   ├── services/
│   │   │   └── accounting_service.py
│   │   ├── repositories/
│   │   │   └── accounting_repository.py
│   │   ├── ui/
│   │   │   └── accounting_views.py
│   │   └── __init__.py
│   │
│   ├── hr/                      # Módulo de Recursos Humanos
│   │   ├── controllers/
│   │   │   └── hr_controller.py
│   │   ├── services/
│   │   │   └── hr_service.py
│   │   ├── repositories/
│   │   │   └── hr_repository.py
│   │   ├── ui/
│   │   │   └── hr_views.py
│   │   └── __init__.py
│   │
│   ├── crm/                     # Módulo de CRM
│   │   ├── controllers/
│   │   │   └── crm_controller.py
│   │   ├── services/
│   │   │   └── crm_service.py
│   │   ├── repositories/
│   │   │   └── crm_repository.py
│   │   ├── ui/
│   │   │   └── crm_views.py
│   │   └── __init__.py
│   │
│   ├── documents/               # Módulo de Documentos
│   │   ├── controllers/
│   │   │   └── document_controller.py
│   │   ├── services/
│   │   │   └── document_service.py
│   │   ├── repositories/
│   │   │   └── document_repository.py
│   │   ├── ui/
│   │   │   └── document_views.py
│   │   └── __init__.py
│   │
│   ├── notifications/          # Módulo de Notificaciones
│   │   ├── controllers/
│   │   │   └── notification_controller.py
│   │   ├── services/
│   │   │   ├── notifier.py
│   │   │   └── messaging/
│   │   ├── repositories/
│   │   │   └── notification_repository.py
│   │   ├── ui/
│   │   │   ├── notification_views.py
│   │   │   └── messaging_config_view.py
│   │   └── __init__.py
│   │
│   ├── automation/             # Módulo de Automatización
│   │   ├── controllers/
│   │   │   └── automation_controller.py
│   │   ├── services/
│   │   │   └── automation/
│   │   ├── repositories/
│   │   │   └── automation_repository.py
│   │   ├── ui/
│   │   │   └── automation_views.py
│   │   └── __init__.py
│   │
│   ├── store/                  # Módulo de Tienda Pública
│   │   ├── controllers/
│   │   │   └── store_controller.py
│   │   ├── services/
│   │   │   └── store_service.py
│   │   ├── repositories/
│   │   │   └── store_repository.py
│   │   ├── ui/
│   │   │   ├── store_views.py
│   │   │   └── store_public.py
│   │   └── __init__.py
│   │
│   └── admin/                  # Módulo de Administración
│       ├── controllers/
│       │   └── admin_controller.py
│       ├── services/
│       │   ├── backup.py
│       │   └── permissions.py
│       ├── repositories/
│       │   └── config_repository.py
│       ├── ui/
│       │   └── admin.py
│       └── __init__.py
│
├── core/                        # Core compartido
│   ├── controller.py            # Fachada principal
│   ├── events.py               # Event Bus
│   ├── error_handler.py        # Manejo de errores
│   └── schemas.py              # DTOs compartidos
│
├── services/                    # Servicios transversales
│   ├── database.py             # Gestión de BD
│   ├── migrator.py             # Migraciones
│   ├── migrations/             # Scripts de migración
│   └── repository/             # Repositorios base
│
├── ui/                          # UI compartida
│   ├── app_view.py             # App shell
│   ├── components.py           # Componentes reutilizables
│   ├── typography.py           # Estilos tipográficos
│   └── views/                  # Vistas genéricas
│
├── utils/                       # Utilidades
│   ├── logger.py
│   ├── crypto.py
│   └── validators.py
│
└── config/                      # Configuración
    └── settings.py
```

---

## Descripción de Módulos

### 1. Módulo de Autenticación (`auth/`)
**Responsabilidad**: Gestión de usuarios, autenticación, autorización y sesiones.
- **Controladores**: `AuthController`
- **Servicios**: Login, logout, registro, recuperación de contraseña, verificación de email
- **Repositorios**: `UserRepository` (usuarios, roles, permisos, sesiones)
- **UI**: Login, registro, forgot password, verify email

### 2. Módulo de Productos (`products/`)
**Responsabilidad**: Gestión del catálogo de productos.
- **Controladores**: `ProductController`
- **Servicios**: CRUD productos, categorías, proveedores, códigos de barras
- **Repositorios**: `ProductRepository`
- **UI**: Lista de productos, formulario de producto, gestión de categorías

### 3. Módulo de Inventario (`inventory/`)
**Responsabilidad**: Gestión de stock y operaciones de inventario.
- **Controladores**: `InventoryController`
- **Servicios**: Stock, valoración, análisis de inventario, alertas
- **Repositorios**: `InventoryRepository`
- **UI**: Gestión de stock, operaciones de inventario, análisis

### 4. Módulo de Almacenes (`warehouses/`)
**Responsabilidad**: Gestión de almacenes y transferencias.
- **Controladores**: `WarehouseController`
- **Servicios**: Gestión de almacenes, transferencias, lotes
- **Repositorios**: `WarehouseRepository`
- **UI**: Vista de almacenes, transferencias entre almacenes

### 5. Módulo de Ventas (`sales/`)
**Responsabilidad**: Gestión de ventas y POS.
- **Controladores**: `SalesController`, `SalesEnhancedController`
- **Servicios**: Ventas, POS, carrito de compras, clientes
- **Repositorios**: `SaleRepository`
- **UI**: Vista de ventas, POS, carrito

### 6. Módulo de Compras (`purchasing/`)
**Responsabilidad**: Gestión de compras y órdenes de compra.
- **Controladores**: `PurchasingController`
- **Servicios**: Órdenes de compra, proveedores
- **Repositorios**: `PurchasingRepository`
- **UI**: Vista de compras

### 7. Módulo de Facturación (`invoicing/`)
**Responsabilidad**: Gestión de facturas.
- **Controladores**: `InvoiceController`
- **Servicios**: Facturación, generación de facturas
- **Repositorios**: `InvoiceRepository`
- **UI**: Vista de facturas

### 8. Módulo de Reportes (`reports/`)
**Responsabilidad**: Generación de reportes y exportaciones.
- **Controladores**: `ReportController`
- **Servicios**: Exportación (CSV, PDF, XLSX, JSON), reportes financieros, reportes de inventario
- **UI**: Reportes de productos, reportes financieros, gráficos

### 9. Módulo de Contabilidad (`accounting/`)
**Responsabilidad**: Gestión contable.
- **Controladores**: `AccountingController`
- **Servicios**: Asientos contables, balances
- **Repositorios**: `AccountingRepository`
- **UI**: Vista de contabilidad

### 10. Módulo de RRHH (`hr/`)
**Responsabilidad**: Gestión de recursos humanos.
- **Controladores**: `HRController`
- **Servicios**: Empleados, nómina
- **Repositorios**: `HRRepository`
- **UI**: Vista de RRHH

### 11. Módulo de CRM (`crm/`)
**Responsabilidad**: Gestión de relaciones con clientes.
- **Controladores**: `CRMController`
- **Servicios**: Clientes, seguimiento
- **Repositorios**: `CRMRepository`
- **UI**: Vista de CRM

### 12. Módulo de Documentos (`documents/`)
**Responsabilidad**: Gestión de documentos.
- **Controladores**: `DocumentController`
- **Servicios**: Almacenamiento de documentos
- **Repositorios**: `DocumentRepository`
- **UI**: Vista de documentos

### 13. Módulo de Notificaciones (`notifications/`)
**Responsabilidad**: Sistema de notificaciones y mensajería.
- **Controladores**: `NotificationController`
- **Servicios**: Notificaciones, email, mensajería
- **Repositorios**: `NotificationRepository`
- **UI**: Vista de notificaciones, configuración de mensajería

### 14. Módulo de Automatización (`automation/`)
**Responsabilidad**: Automatización de procesos.
- **Controladores**: `AutomationController`
- **Servicios**: Workflows, reglas de automatización
- **Repositorios**: `AutomationRepository`
- **UI**: Vista de automatización

### 15. Módulo de Tienda Pública (`store/`)
**Responsabilidad**: Tienda pública/e-commerce.
- **Controladores**: `StoreController`
- **Servicios**: Catálogo público, carrito de compras
- **Repositorios**: `StoreRepository`
- **UI**: Vista de tienda, tienda pública

### 16. Módulo de Administración (`admin/`)
**Responsabilidad**: Configuración del sistema.
- **Controladores**: `AdminController`
- **Servicios**: Backups, configuración, permisos
- **Repositorios**: `ConfigRepository`
- **UI**: Panel de administración

---

## Beneficios de la Arquitectura Modular

1. **Separación de Responsabilidades**: Cada módulo tiene una responsabilidad clara y delimitada.
2. **Mantenibilidad**: Los cambios en un módulo no afectan a otros.
3. **Escalabilidad**: Se pueden agregar nuevos módulos sin modificar los existentes.
4. **Testabilidad**: Cada módulo se puede testear de forma independiente.
5. **Reutilización**: Los módulos se pueden reutilizar en otros proyectos.
6. **Colaboración**: Diferentes equipos pueden trabajar en módulos diferentes simultáneamente.

---

## Plan de Migración

### Fase 1: Preparación
- Crear estructura de directorios `modules/`
- Definir interfaces entre módulos
- Establecer convenciones de nomenclatura

### Fase 2: Migración Gradual
- Migrar módulo por módulo comenzando por los más independientes:
  1. `auth/` (dependencia mínima)
  2. `products/`
  3. `inventory/`
  4. `warehouses/`
  5. `sales/`
  6. `reports/`
  7. Resto de módulos

### Fase 3: Actualización de Imports
- Actualizar imports en toda la codebase
- Verificar que no haya dependencias circulares

### Fase 4: Limpieza
- Eliminar archivos antiguos
- Actualizar documentación
- Actualizar tests

---

## Convenciones

### Estructura de Módulo
Cada módulo debe seguir esta estructura:
```
modules/{module_name}/
├── controllers/       # Lógica de negocio
├── services/          # Servicios específicos del módulo
├── repositories/      # Acceso a datos específico
├── ui/               # Vistas específicas del módulo
└── __init__.py       # Exporta la API pública del módulo
```

### Imports
- Los imports deben ser relativos dentro del módulo
- Los imports entre módulos deben hacerse a través de `__init__.py`
- Evitar dependencias circulares

### Testing
- Cada módulo debe tener sus propios tests
- Los tests deben estar en `tests/modules/{module_name}/`
- Usar mocks para dependencias externas

---

## Próximos Pasos

1. Aprobar esta arquitectura modular
2. Crear la estructura de directorios
3. Comenzar la migración con el módulo `auth/`
4. Actualizar la documentación conforme se avanza
5. Realizar pruebas de integración después de cada migración
