"""Tests for utils/validators.py — new validators."""

from utils.validators import Validator


class TestValidateDescripcion:
    def test_empty_descripcion_is_valid(self):
        ok, _ = Validator.validate_descripcion("")
        assert ok is True

    def test_valid_descripcion(self):
        ok, _ = Validator.validate_descripcion("A" * 500)
        assert ok is True

    def test_max_length_descripcion(self):
        ok, _ = Validator.validate_descripcion("A" * 2000)
        assert ok is True

    def test_too_long_descripcion(self):
        ok, err = Validator.validate_descripcion("A" * 2001)
        assert ok is False
        assert "2000" in err


class TestValidateTelefono:
    def test_empty_telefono_is_valid(self):
        ok, _ = Validator.validate_telefono("")
        assert ok is True

    def test_valid_telefono_digits(self):
        ok, _ = Validator.validate_telefono("1234567890")
        assert ok is True

    def test_valid_telefono_with_plus(self):
        ok, _ = Validator.validate_telefono("+52 123 456 7890")
        assert ok is True

    def test_valid_telefono_with_parens(self):
        ok, _ = Validator.validate_telefono("(555) 123-4567")
        assert ok is True

    def test_invalid_telefono_letters(self):
        ok, _ = Validator.validate_telefono("abc123")
        assert ok is False

    def test_too_long_telefono(self):
        ok, _ = Validator.validate_telefono("1" * 21)
        assert ok is False


class TestValidateMoneda:
    def test_valid_monto(self):
        ok, _ = Validator.validate_moneda(100.50)
        assert ok is True

    def test_zero_monto(self):
        ok, _ = Validator.validate_moneda(0)
        assert ok is True

    def test_negative_monto(self):
        ok, _ = Validator.validate_moneda(-10)
        assert ok is False

    def test_too_large_monto(self):
        ok, _ = Validator.validate_moneda(1_000_000)
        assert ok is False

    def test_too_many_decimals(self):
        ok, _ = Validator.validate_moneda(10.123)
        assert ok is False

    def test_two_decimals_ok(self):
        ok, _ = Validator.validate_moneda(10.99)
        assert ok is True


class TestValidatePositiveInt:
    def test_valid_positive_int(self):
        ok, _ = Validator.validate_positive_int(5)
        assert ok is True

    def test_zero_is_not_positive(self):
        ok, _ = Validator.validate_positive_int(0)
        assert ok is False

    def test_negative_is_not_positive(self):
        ok, _ = Validator.validate_positive_int(-1)
        assert ok is False

    def test_too_large(self):
        ok, _ = Validator.validate_positive_int(1_000_000)
        assert ok is False

    def test_float_is_not_int(self):
        ok, _ = Validator.validate_positive_int(5.5)
        assert ok is False
