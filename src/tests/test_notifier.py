"""Tests for the email notification service (notifier.py).

Uses mocking to avoid actual SMTP connections.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from services.notifier import (
    _send_email_raw,
    get_smtp_config,
    is_configured,
    send_custom_alert,
    send_low_stock_alert,
)


class TestNotifierConfig:
    def test_get_smtp_config(self, ctrl):
        cfg = get_smtp_config(ctrl.db)
        assert isinstance(cfg, dict)
        assert "host" in cfg
        assert "port" in cfg
        assert "enabled" in cfg

    def test_is_configured_full(self):
        cfg = {"host": "smtp.example.com", "user": "u", "password": "p", "to_email": "a@b.com"}
        assert is_configured(cfg) is True

    def test_is_configured_missing_fields(self):
        assert is_configured({"host": "", "user": "u", "password": "p", "to_email": "a@b.com"}) is False
        assert is_configured({"host": "h", "user": "", "password": "p", "to_email": "a@b.com"}) is False
        assert is_configured({"host": "h", "user": "u", "password": "", "to_email": "a@b.com"}) is False
        assert is_configured({"host": "h", "user": "u", "password": "p", "to_email": ""}) is False


class TestNotifierSendLowStock:
    @patch("services.notifier.get_smtp_config")
    @patch("services.notifier._send_email_raw")
    def test_low_stock_alert_disabled(
        self, mock_send: MagicMock, mock_config: MagicMock, ctrl
    ):
        mock_config.return_value = {
            "host": "smtp.example.com", "port": "587", "user": "u",
            "password": "p", "from_email": "f@e.com", "to_email": "t@e.com",
            "enabled": "no",
        }
        result = send_low_stock_alert(ctrl.db)
        assert result["sent"] is False
        assert "disabled" in result.get("reason", "").lower()
        mock_send.assert_not_called()

    @patch("services.notifier.get_smtp_config")
    @patch("services.notifier._send_email_raw")
    def test_low_stock_alert_not_configured(
        self, mock_send: MagicMock, mock_config: MagicMock, ctrl
    ):
        mock_config.return_value = {
            "host": "", "port": "587", "user": "", "password": "",
            "from_email": "", "to_email": "", "enabled": "si",
        }
        result = send_low_stock_alert(ctrl.db)
        assert result["sent"] is False
        assert "not configured" in result.get("reason", "").lower()
        mock_send.assert_not_called()

    @patch("services.notifier.get_smtp_config")
    @patch("services.notifier._send_email_raw")
    def test_low_stock_alert_no_products(
        self, mock_send: MagicMock, mock_config: MagicMock, ctrl
    ):
        mock_config.return_value = {
            "host": "smtp.example.com", "port": "587", "user": "u",
            "password": "p", "from_email": "f@e.com", "to_email": "t@e.com",
            "enabled": "si",
        }
        with patch.object(ctrl.db, "obtener_productos_stock_bajo", return_value=[]):
            result = send_low_stock_alert(ctrl.db)
        assert result["sent"] is False
        assert "no low stock" in result.get("reason", "").lower()
        mock_send.assert_not_called()

    @patch("services.notifier.get_smtp_config")
    @patch("services.notifier._send_email_raw")
    def test_low_stock_alert_success(
        self, mock_send: MagicMock, mock_config: MagicMock, ctrl
    ):
        mock_config.return_value = {
            "host": "smtp.example.com", "port": "587", "user": "u",
            "password": "p", "from_email": "f@e.com", "to_email": "t@e.com",
            "enabled": "si",
        }
        mock_send.return_value = {"sent": True, "subject": "Test", "to": "t@e.com"}
        products = [
            {"nombre": "Prod A", "codigo": "P001", "cantidad": 2, "stock_min": 10}
        ]
        with patch.object(ctrl.db, "obtener_productos_stock_bajo", return_value=products):
            result = send_low_stock_alert(ctrl.db)
        assert result["sent"] is True
        mock_send.assert_called_once()


class TestNotifierCustomAlert:
    @patch("services.notifier.get_smtp_config")
    @patch("services.notifier._send_email_raw")
    def test_custom_alert_not_configured(
        self, mock_send: MagicMock, mock_config: MagicMock, ctrl
    ):
        mock_config.return_value = {
            "host": "", "user": "", "password": "", "to_email": ""
        }
        result = send_custom_alert(ctrl.db, "Subject", "Body")
        assert result["sent"] is False
        mock_send.assert_not_called()

    @patch("services.notifier._send_email_raw")
    def test_custom_alert_success(self, mock_send: MagicMock, ctrl):
        with patch("services.notifier.get_smtp_config") as mock_config:
            mock_config.return_value = {
                "host": "smtp.example.com", "port": "587", "user": "u",
                "password": "p", "from_email": "f@e.com", "to_email": "t@e.com",
                "enabled": "si",
            }
            mock_send.return_value = {"sent": True}
            result = send_custom_alert(ctrl.db, "Hola", "Mundo")
        assert result["sent"] is True
        mock_send.assert_called_once()


class TestNotifierSendEmailRaw:
    @patch("services.notifier.smtplib.SMTP")
    @patch("services.notifier.ssl.create_default_context")
    def test_send_email_raw_success(
        self, mock_ssl: MagicMock, mock_smtp: MagicMock
    ):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        cfg = {
            "host": "smtp.example.com", "port": "587", "user": "user",
            "password": "pass", "from_email": "from@e.com", "to_email": "to@e.com",
        }
        result = _send_email_raw(cfg, "Subject", "Body")
        assert result["sent"] is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.send_message.assert_called_once()

    @patch("services.notifier.smtplib.SMTP")
    def test_send_email_raw_failure(self, mock_smtp: MagicMock):
        mock_smtp.side_effect = Exception("Connection refused")
        cfg = {
            "host": "smtp.example.com", "port": "587", "user": "u",
            "password": "p", "from_email": "f", "to_email": "t",
        }
        result = _send_email_raw(cfg, "Sub", "Body")
        assert result["sent"] is False
        assert "refused" in result.get("reason", "")
