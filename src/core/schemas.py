"""Data transfer objects (DTOs) for the application.

Use dataclasses for function signatures with 5+ parameters to improve
readability, type safety, and IDE support.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ProductoData:
    """DTO for creating/updating a product."""

    codigo: str
    nombre: str
    descripcion: str = ""
    categoria: str = ""
    stock_min: int = 0
    proveedor_id: int | None = None
    unidad_medida: str = "unidad"
    precio: float = 0.0
    cantidad: int = 0


@dataclass(frozen=True, slots=True)
class ProveedorData:
    """DTO for creating/updating a supplier."""

    nombre: str
    contacto: str = ""
    telefono: str = ""
    email: str = ""
    direccion: str = ""


@dataclass(frozen=True, slots=True)
class ClienteData:
    """DTO for creating/updating a customer."""

    nombre: str
    telefono: str = ""
    email: str = ""
    direccion: str = ""


@dataclass(frozen=True, slots=True)
class VentaData:
    """DTO for creating a sale."""

    cliente_id: int
    items: list[dict] = field(default_factory=list)
    metodo_pago: str = "efectivo"
    referencia: str = ""


@dataclass(frozen=True, slots=True)
class UserData:
    """DTO for creating a user."""

    username: str
    password: str
    nombre: str
    rol_nombre: str = "operador"


@dataclass(frozen=True, slots=True)
class AlmacenData:
    """DTO for creating/updating a warehouse."""

    nombre: str
    ubicacion: str = ""


@dataclass(frozen=True, slots=True)
class TransferenciaData:
    """DTO for creating a warehouse transfer."""

    almacen_origen_id: int
    almacen_destino_id: int
    producto_id: int
    cantidad: int
    nota: str = ""


@dataclass(frozen=True, slots=True)
class DevolucionData:
    """DTO for creating a return."""

    venta_id: int
    items: list[dict] = field(default_factory=list)
    motivo: str = ""


@dataclass(frozen=True, slots=True)
class LoteData:
    """DTO for creating a batch/lot."""

    producto_id: int
    codigo_lote: str
    cantidad_inicial: int = 0
    fecha_fabricacion: str | None = None
    fecha_vencimiento: str | None = None
    serie: str | None = None
    ubicacion: str | None = None
    proveedor_id: int | None = None


@dataclass(frozen=True, slots=True)
class VarianteData:
    """DTO for creating a product variant."""

    producto_id: int
    sku: str
    atributos: str
    cantidad: int = 0
    precio_override: float | None = None


@dataclass(frozen=True, slots=True)
class PlantillaReporteData:
    """DTO for saving a report template."""

    nombre: str
    modulo: str = "productos"
    columnas: list[str] = field(default_factory=list)
    filtros: dict | None = None
    agrupacion: str | None = None
    ordenado_por: str | None = None
