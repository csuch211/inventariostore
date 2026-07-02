"""Data transfer objects (DTOs) for the application.

Use dataclasses for function signatures with 5+ parameters to improve
readability, type safety, and IDE support.
"""

import re
from dataclasses import dataclass, field


def _strip_strings(obj):
    for field_name in obj.__dataclass_fields__:
        value = getattr(obj, field_name)
        if isinstance(value, str):
            object.__setattr__(obj, field_name, value.strip())


_EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


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

    def __post_init__(self):
        _strip_strings(self)

    def validate(self):
        if self.precio < 0:
            raise ValueError("El precio no puede ser negativo")
        if self.cantidad < 0:
            raise ValueError("La cantidad no puede ser negativa")
        return True


@dataclass(frozen=True, slots=True)
class ProveedorData:
    """DTO for creating/updating a supplier."""

    nombre: str
    contacto: str = ""
    telefono: str = ""
    email: str = ""
    direccion: str = ""

    def __post_init__(self):
        _strip_strings(self)

    def validate(self):
        if self.email and not _EMAIL_PATTERN.match(self.email):
            raise ValueError("El formato del email no es válido")
        return True


@dataclass(frozen=True, slots=True)
class ClienteData:
    """DTO for creating/updating a customer."""

    nombre: str
    telefono: str = ""
    email: str = ""
    direccion: str = ""

    def __post_init__(self):
        _strip_strings(self)

    def validate(self):
        if self.email and not _EMAIL_PATTERN.match(self.email):
            raise ValueError("El formato del email no es válido")
        return True


@dataclass(frozen=True, slots=True)
class VentaData:
    """DTO for creating a sale."""

    cliente_id: int
    items: list[dict] = field(default_factory=list)
    metodo_pago: str = "efectivo"
    referencia: str = ""

    def __post_init__(self):
        object.__setattr__(self, "metodo_pago", self.metodo_pago.strip())
        object.__setattr__(self, "referencia", self.referencia.strip())

    def validate(self):
        return True


@dataclass(frozen=True, slots=True)
class UserData:
    """DTO for creating a user."""

    username: str
    password: str
    nombre: str
    rol_nombre: str = "operador"

    def __post_init__(self):
        _strip_strings(self)

    def validate(self):
        if len(self.password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not re.search(r'[A-Z]', self.password):
            raise ValueError("La contraseña debe contener al menos una mayúscula")
        if not re.search(r'[0-9]', self.password):
            raise ValueError("La contraseña debe contener al menos un número")
        return True


@dataclass(frozen=True, slots=True)
class AlmacenData:
    """DTO for creating/updating a warehouse."""

    nombre: str
    ubicacion: str = ""

    def __post_init__(self):
        _strip_strings(self)

    def validate(self):
        return True


@dataclass(frozen=True, slots=True)
class TransferenciaData:
    """DTO for creating a warehouse transfer."""

    almacen_origen_id: int
    almacen_destino_id: int
    producto_id: int
    cantidad: int
    nota: str = ""

    def __post_init__(self):
        object.__setattr__(self, "nota", self.nota.strip())

    def validate(self):
        return True


@dataclass(frozen=True, slots=True)
class DevolucionData:
    """DTO for creating a return."""

    venta_id: int
    items: list[dict] = field(default_factory=list)
    motivo: str = ""

    def __post_init__(self):
        object.__setattr__(self, "motivo", self.motivo.strip())

    def validate(self):
        return True


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

    def __post_init__(self):
        object.__setattr__(self, "codigo_lote", self.codigo_lote.strip())
        for f in ("fecha_fabricacion", "fecha_vencimiento", "serie", "ubicacion"):
            v = getattr(self, f)
            if isinstance(v, str):
                object.__setattr__(self, f, v.strip())

    def validate(self):
        if self.cantidad_inicial <= 0:
            raise ValueError("La cantidad inicial debe ser mayor a 0")
        return True


@dataclass(frozen=True, slots=True)
class VarianteData:
    """DTO for creating a product variant."""

    producto_id: int
    sku: str
    atributos: str
    cantidad: int = 0
    precio_override: float | None = None

    def __post_init__(self):
        _strip_strings(self)

    def validate(self):
        return True


@dataclass(frozen=True, slots=True)
class PlantillaReporteData:
    """DTO for saving a report template."""

    nombre: str
    modulo: str = "productos"
    columnas: list[str] = field(default_factory=list)
    filtros: dict | None = None
    agrupacion: str | None = None
    ordenado_por: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "nombre", self.nombre.strip())
        object.__setattr__(self, "modulo", self.modulo.strip())

    def validate(self):
        return True
