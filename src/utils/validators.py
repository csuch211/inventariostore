"""
Input validation utilities
"""

import re

# Validation limits
MAX_CODIGO_LENGTH = 50
MAX_NOMBRE_LENGTH = 200
MAX_DESCRIPCION_LENGTH = 2000
MAX_CANTIDAD = 999_999
MAX_PRECIO = 999_999.99
MAX_TELEFONO_LENGTH = 20
MAX_DIRECCION_LENGTH = 500


class Validator:
    """Centralized validation logic"""

    @staticmethod
    def validate_codigo(codigo: str) -> tuple[bool, str | None]:
        """Validate product code"""
        if not codigo:
            return False, "Código es requerido"
        if len(codigo) < 3:
            return False, "Código debe tener al menos 3 caracteres"
        if len(codigo) > MAX_CODIGO_LENGTH:
            return False, f"Código no puede exceder {MAX_CODIGO_LENGTH} caracteres"
        if not re.match(r"^[A-Za-z0-9\-_]+$", codigo):
            return (
                False,
                "Código solo puede contener letras, números, guiones y guiones bajos",
            )
        return True, None

    @staticmethod
    def validate_nombre(nombre: str) -> tuple[bool, str | None]:
        """Validate product name"""
        if not nombre:
            return False, "Nombre es requerido"
        if len(nombre) < 3:
            return False, "Nombre debe tener al menos 3 caracteres"
        if len(nombre) > MAX_NOMBRE_LENGTH:
            return False, f"Nombre no puede exceder {MAX_NOMBRE_LENGTH} caracteres"
        return True, None

    @staticmethod
    def validate_cantidad(cantidad: str) -> tuple[bool, str | None]:
        """Validate quantity"""
        try:
            qty = int(cantidad)
            if qty < 0:
                return False, "Cantidad no puede ser negativa"
            if qty > MAX_CANTIDAD:
                return False, "Cantidad es demasiado grande"
            return True, None
        except ValueError:
            return False, "Cantidad debe ser un número entero"

    @staticmethod
    def validate_precio(precio: str) -> tuple[bool, str | None]:
        """Validate price"""
        try:
            price = float(precio)
            if price < 0:
                return False, "Precio no puede ser negativo"
            if price > MAX_PRECIO:
                return False, "Precio es demasiado grande"
            return True, None
        except ValueError:
            return False, "Precio debe ser un número válido"

    @staticmethod
    def validate_email(email: str) -> tuple[bool, str | None]:
        """Validate email format"""
        if not email:
            return False, "Email es requerido"
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            return False, "Email inválido"
        return True, None

    @staticmethod
    def validate_password(password: str, min_length: int = 8) -> tuple[bool, str | None]:
        """Validate password strength"""
        if not password:
            return False, "Contraseña es requerida"
        if len(password) < min_length:
            return False, f"Contraseña debe tener al menos {min_length} caracteres"
        if not any(c.isupper() for c in password):
            return False, "Contraseña debe contener al menos una mayúscula"
        if not any(c.isdigit() for c in password):
            return False, "Contraseña debe contener al menos un número"
        return True, None

    @staticmethod
    def validate_descripcion(descripcion: str) -> tuple[bool, str | None]:
        """Validate description length"""
        if descripcion and len(descripcion) > MAX_DESCRIPCION_LENGTH:
            return False, f"Descripción no puede exceder {MAX_DESCRIPCION_LENGTH} caracteres"
        return True, None

    @staticmethod
    def validate_telefono(telefono: str) -> tuple[bool, str | None]:
        """Validate phone number format"""
        if not telefono:
            return True, None  # Optional field
        if len(telefono) > MAX_TELEFONO_LENGTH:
            return False, f"Teléfono no puede exceder {MAX_TELEFONO_LENGTH} caracteres"
        if not re.match(r"^[\d\s\+\-\(\)]+$", telefono):
            return False, "Teléfono solo puede contener números, espacios, +, -, (, )"
        return True, None

    @staticmethod
    def validate_moneda(monto: float, nombre: str = "Monto") -> tuple[bool, str | None]:
        """Validate currency amount"""
        if monto < 0:
            return False, f"{nombre} no puede ser negativo"
        if monto > MAX_PRECIO:
            return False, f"{nombre} es demasiado grande"
        # Check for reasonable decimal precision (max 2 decimal places)
        if round(monto, 2) != monto:
            return False, f"{nombre} no puede tener más de 2 decimales"
        return True, None

    @staticmethod
    def validate_positive_int(value: int, nombre: str = "Valor") -> tuple[bool, str | None]:
        """Validate positive integer (for cart quantities, etc.)"""
        if not isinstance(value, int):
            return False, f"{nombre} debe ser un número entero"
        if value <= 0:
            return False, f"{nombre} debe ser mayor a cero"
        if value > MAX_CANTIDAD:
            return False, f"{nombre} es demasiado grande"
        return True, None
