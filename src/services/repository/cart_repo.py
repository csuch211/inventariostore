"""Cart repository for persistent shopping carts."""

import sqlite3
from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CartRepository(BaseRepository):
    def obtener_carrito_activo(self, usuario: str) -> dict | None:
        """Get the active cart for a user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM carritos WHERE usuario = ? AND estado = 'activo' ORDER BY creado_en DESC LIMIT 1",
                    (usuario,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch active cart: {e}")

    def crear_carrito(self, usuario: str, cliente_id: int | None = None, notas: str = "") -> int:
        """Create a new shopping cart."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO carritos (usuario, cliente_id, estado, notas, creado_en, actualizado_en) VALUES (?, ?, 'activo', ?, ?, ?)",
                    (usuario, cliente_id, notas, now, now),
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create cart: {e}")

    def obtener_o_crear_carrito(self, usuario: str, cliente_id: int | None = None) -> dict:
        """Get the active cart or create one if none exists."""
        cart = self.obtener_carrito_activo(usuario)
        if cart:
            return cart
        cart_id = self.crear_carrito(usuario, cliente_id)
        return {"id": cart_id, "usuario": usuario, "cliente_id": cliente_id, "estado": "activo"}

    def agregar_item(self, carrito_id: int, producto_id: int, cantidad: int, precio_unitario: float) -> int | None:
        """Add a product to the cart or increment its quantity."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                existing = conn.execute(
                    "SELECT id, cantidad FROM carritos_items WHERE carrito_id = ? AND producto_id = ?",
                    (carrito_id, producto_id),
                ).fetchone()
                if existing:
                    new_qty = existing["cantidad"] + cantidad
                    conn.execute(
                        "UPDATE carritos_items SET cantidad = ? WHERE id = ?",
                        (new_qty, existing["id"]),
                    )
                    conn.execute(
                        "UPDATE carritos SET actualizado_en = ? WHERE id = ?",
                        (now, carrito_id),
                    )
                    conn.commit()
                    return existing["id"]
                cursor = conn.execute(
                    "INSERT INTO carritos_items (carrito_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)",
                    (carrito_id, producto_id, cantidad, precio_unitario),
                )
                conn.execute(
                    "UPDATE carritos SET actualizado_en = ? WHERE id = ?",
                    (now, carrito_id),
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to add cart item: {e}")

    def actualizar_cantidad(self, item_id: int, cantidad: int) -> None:
        """Update the quantity of a cart item."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE carritos_items SET cantidad = ? WHERE id = ?", (cantidad, item_id))
                conn.execute(
                    "UPDATE carritos SET actualizado_en = ? WHERE id IN (SELECT carrito_id FROM carritos_items WHERE id = ?)",
                    (now, item_id),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to update cart item: {e}")

    def eliminar_item(self, item_id: int) -> None:
        """Remove an item from the cart."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE carritos SET actualizado_en = ? WHERE id IN (SELECT carrito_id FROM carritos_items WHERE id = ?)", (now, item_id))
                conn.execute("DELETE FROM carritos_items WHERE id = ?", (item_id,))
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete cart item: {e}")

    def obtener_items(self, carrito_id: int) -> list[dict]:
        """List all items in a cart with product details."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT ci.*, p.codigo, p.nombre, p.cantidad as stock_disponible
                    FROM carritos_items ci
                    LEFT JOIN productos p ON ci.producto_id = p.id
                    WHERE ci.carrito_id = ?
                """, (carrito_id,))
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch cart items: {e}")

    def vaciar_carrito(self, carrito_id: int) -> None:
        """Remove all items from a cart."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM carritos_items WHERE carrito_id = ?", (carrito_id,))
                conn.execute("UPDATE carritos SET actualizado_en = ? WHERE id = ?", (now, carrito_id))
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to empty cart: {e}")

    def marcar_convertido(self, carrito_id: int) -> None:
        """Mark a cart as converted to sale."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE carritos SET estado = 'convertido', actualizado_en = ? WHERE id = ?", (now, carrito_id))
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to mark cart as converted: {e}")

    def marcar_abandonado(self, carrito_id: int) -> None:
        """Mark a cart as abandoned."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE carritos SET estado = 'abandonado', actualizado_en = ? WHERE id = ?", (now, carrito_id))
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to mark cart as abandoned: {e}")

    def obtener_carritos_por_usuario(self, usuario: str) -> list[dict]:
        """List all carts for a user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM carritos WHERE usuario = ? ORDER BY creado_en DESC",
                    (usuario,),
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch user carts: {e}")

    def obtener_carrito_por_id(self, carrito_id: int) -> dict | None:
        """Get cart by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM carritos WHERE id = ?", (carrito_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch cart: {e}")

    def obtener_config_ventas(self) -> dict[str, str]:
        """Get all sales configuration key-value pairs."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT clave, valor FROM configuracion_ventas")
                return {r["clave"]: r["valor"] for r in cursor.fetchall()}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch sales config: {e}")

    def guardar_config_ventas(self, clave: str, valor: str) -> None:
        """Upsert a sales configuration key-value pair."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO configuracion_ventas (clave, valor, actualizado_en) VALUES (?, ?, ?) ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor, actualizado_en = excluded.actualizado_en",
                    (clave, valor, now),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to save sales config: {e}")
