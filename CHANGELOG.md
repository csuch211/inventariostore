# Changelog — MaxStore Inventario

## [2.0.0] - 2026-07-02

Refactoring completo del sistema de inventario MaxStore (Flet/Python 3.14.6).
**735 tests pasando, 0 regressions.**

---

### Arquitectura

- **Eliminados 3 God Objects**: `core/controller.py` (1578→166L), `services/database.py` (1158→331L), `ui/app_view.py` (1117→354L)
- **266 métodos proxy eliminados** del controller principal, sub-controllers expuestos como atributos públicos
- **Schema SQL extraído** a `services/schema.sql` (431L), `_init_database()` reducido de 539→40L
- **3 managers extraídos** de app_view: `auth_manager.py`, `stock_alert_manager.py`, `bulk_manager.py`
- **Módulos renombrados**: `phase1` → `advanced_inventory`, `phase3` → `extended_features`
- **`__getattr__`** en controller y database para backward compatibility

### Seguridad

- **Secrets encriptados**: SMTP password, WhatsApp API key, Telegram bot token se encriptan con Fernet antes de guardar en DB
- **Login rate limiting**: 5 intentos por IP por minuto en endpoint `/auth/login`
- **Auditoría de autenticación**: login exitoso/fallido registrado en tabla `auditoria`

### Validaciones

- **Nuevos validators**: `validate_descripcion()`, `validate_telefono()`, `validate_moneda()`, `validate_positive_int()`
- **Controllers validados**: CRM (nombre, email, teléfono), Sales (email, teléfono), Product (descripción, teléfono), Cart (cantidad > 0, precio > 0), Admin (contraseña)
- **Bug fix**: variable `task` no definida en `actualizar_producto`
- **Bug fix**: validación condicional corregida (`if cantidad and ...` → `if cantidad is not None and ...`)
- **Bug fix**: `sale_repo` lanza `StockInsufficientError` en vez de `ValueError` genérico
- **Bug fix**: `sale_repo.obtener_ventas_estadisticas()` lanza `DatabaseException` en vez de devolver ceros silenciosos

### Performance

- **Índices agregados**: `historial_stock(producto_id, creado_en)`, `ventas_detalle(venta_id)`, `clientes(activo)`

### UX/UI

- **Contraste WCAG AA**: `text_muted` cambiado de `#64748B` a `#475569` (ratio 5.3:1)
- **54 colores hardcodeados migrados** a paleta central en 8 archivos (dashboard, pricing, notifications, store, etc.)
- **6 tokens semánticos nuevos**: `info`, `purple`, `teal` (con versiones light/dark)
- **Animaciones**: fade-out (120ms) + fade-in en transiciones entre vistas
- **Responsive**: `TABLET_BREAKPOINT=1024px`, sidebar 200px tablet / 240px desktop
- **Sidebar**: 13→10 secciones consolidadas, 30+ strings hardcodeados → `t()`, 32 keys i18n agregadas (es + en)
- **Tipografía**: `T.display()` (32px), AppHeader y KpiCard migrados a usar `T.`
- **Accesibilidad**: role pill 9→10px, SidebarItem padding 8→10px, autofocus en login, `SnackBarHelper.warning()`

### Código limpio

- **Imports circulares**: 21 lazy imports innecesarios eliminados
- **`_fmt_money()` duplicado**: 12 archivos UI → import desde `ui/_utils.py`
- **`auth.py` duplicado**: `modules/auth/services/auth_service.py` → re-export desde `services.auth`
- **Error handling**: 6 bare `except Exception` corregidos con logging
- **Magic numbers**: umbrales ABC/aging/stockout → constantes nombradas
- **Variables mutables**: `EXPORT_FORMATS`, `PALETTE`, `MOBILE_TOP_KEYS` → tuple, `REQUIRED_KEYS`/`CONFIG_KEYS` → frozenset
- **Docstrings**: 33 docstrings agregados a métodos de repositorios

### Tests

- **30 tests nuevos**: `test_validators.py` (20 tests), `test_crypto.py` (10 tests)
- **Total**: 735 passed, 1 skipped, 0 regressions

### Archivos nuevos

| Archivo | Propósito |
|---------|-----------|
| `services/schema.sql` | Schema SQL separado de database.py |
| `services/advanced_inventory_db.py` | Renombrado de phase1_db.py |
| `services/extended_features_db.py` | Renombrado de phase3_db.py |
| `core/controllers/advanced_inventory_controller.py` | Renombrado de phase1_controller.py |
| `core/controllers/extended_features_controller.py` | Renombrado de phase3_controller.py |
| `ui/auth_manager.py` | Login/logout/register extraído de app_view |
| `ui/stock_alert_manager.py` | Monitor de stock extraído de app_view |
| `ui/bulk_manager.py` | Operaciones masivas extraído de app_view |
| `tests/test_validators.py` | Tests de validadores nuevos |
| `tests/test_crypto.py` | Tests de encriptación |

### Archivos eliminados

| Archivo | Razón |
|---------|-------|
| `services/phase1_db.py` | Renombrado a advanced_inventory_db.py |
| `services/phase3_db.py` | Renombrado a extended_features_db.py |
| `core/controllers/phase1_controller.py` | Renombrado a advanced_inventory_controller.py |
| `core/controllers/phase3_controller.py` | Renombrado a extended_features_controller.py |
