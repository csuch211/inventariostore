"""
Barcode and QR code generation and reading service
"""

import base64
import io
import logging
from pathlib import Path

from config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

BARCODE_DIR = PROJECT_ROOT / "barcodes"
QRCODE_DIR = PROJECT_ROOT / "qrcodes"
BARCODE_DIR.mkdir(exist_ok=True)
QRCODE_DIR.mkdir(exist_ok=True)

try:
    import barcode
    from barcode.writer import ImageWriter

    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False

try:
    import qrcode

    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

try:
    from pyzbar.pyzbar import decode as pyzbar_decode

    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class CodeHandler:
    @staticmethod
    def generar_codigo_barras(codigo: str) -> Path | None:
        if not BARCODE_AVAILABLE:
            return None
        try:
            code128 = barcode.get_barcode_class("code128")
            b_img = code128(codigo, writer=ImageWriter())
            stem = str(BARCODE_DIR / codigo)
            b_img.save(stem)
            path = BARCODE_DIR / f"{codigo}.png"
            return path if path.exists() else None
        except Exception as e:
            logger.error(f"Barcode generation error for {codigo}: {e}")
            return None

    @staticmethod
    def generar_qr(codigo: str) -> Path | None:
        if not QR_AVAILABLE:
            return None
        try:
            img = qrcode.make(codigo)
            path = QRCODE_DIR / f"{codigo}.png"
            img.save(str(path))
            return path
        except Exception as e:
            logger.error(f"QR generation error for {codigo}: {e}")
            return None

    @staticmethod
    def obtener_codigo_barras(codigo: str) -> Path | None:
        path = BARCODE_DIR / f"{codigo}.png"
        if path.exists():
            return path
        return CodeHandler.generar_codigo_barras(codigo)

    @staticmethod
    def obtener_qr(codigo: str) -> Path | None:
        path = QRCODE_DIR / f"{codigo}.png"
        if path.exists():
            return path
        return CodeHandler.generar_qr(codigo)

    @staticmethod
    def imagen_a_base64(ruta: Path) -> str | None:
        if not ruta or not ruta.exists() or not PIL_AVAILABLE:
            return None
        try:
            img = Image.open(ruta)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            logger.error(f"Image to base64 error: {e}")
            return None

    @staticmethod
    def leer_codigo_desde_imagen(ruta_imagen: str) -> str | None:
        if not PYZBAR_AVAILABLE or not PIL_AVAILABLE:
            return None
        try:
            results = pyzbar_decode(Image.open(ruta_imagen))
            if results:
                return results[0].data.decode("utf-8")
            return None
        except Exception as e:
            logger.error(f"Code reading error from image: {e}")
            return None

    @staticmethod
    def disponibilidad() -> dict:
        return {
            "barcode": BARCODE_AVAILABLE,
            "qrcode": QR_AVAILABLE,
            "pyzbar": PYZBAR_AVAILABLE,
            "pillow": PIL_AVAILABLE,
        }
