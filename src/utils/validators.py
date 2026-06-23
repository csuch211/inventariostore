"""
Input validation utilities
"""

import re


class Validator:
    """Centralized validation logic"""

    @staticmethod
    def validate_codigo(codigo: str) -> tuple[bool, str | None]:
        """Validate product code"""
        if not codigo:
            return False, "Código es requerido"
        if len(codigo) < 3:
            return False, "Código debe tener al menos 3 caracteres"
        if len(codigo) > 50:
            return False, "Código no puede exceder 50 caracteres"
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
        if len(nombre) > 200:
            return False, "Nombre no puede exceder 200 caracteres"
        return True, None

    @staticmethod
    def validate_cantidad(cantidad: str) -> tuple[bool, str | None]:
        """Validate quantity"""
        try:
            qty = int(cantidad)
            if qty < 0:
                return False, "Cantidad no puede ser negativa"
            if qty > 999999:
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
            if price > 999999.99:
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
