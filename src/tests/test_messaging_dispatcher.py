"""Tests for the messaging dispatcher (factory, send_via_channel, create_push_sender_func)."""

"""Tests for the messaging dispatcher."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.messaging.base import MessageSender
from services.messaging.dispatcher import (
    _senders,
    create_push_sender_func,
    get_sender,
    register_sender,
    send_via_channel,
)


class _FakeSender(MessageSender):
    async def send(self, destinatario, asunto, cuerpo, config):
        return {"sent": True, "channel": "fake"}
    def validate_config(self, config):
        return True, ""
    def get_channel_type(self):
        return "fake"


def _mock_response(is_success=True, json_data=None, text=""):
    m = MagicMock()
    m.is_success = is_success
    m.json.return_value = json_data or {}
    m.text = text or ""
    return m


def _async_client_mock(post_return_value=None):
    client = AsyncMock()
    client.__aenter__.return_value = client
    if post_return_value is not None:
        client.post.return_value = post_return_value
    return client


@pytest.mark.asyncio
async def test_get_sender_whatsapp():
    sender = get_sender("whatsapp")
    assert sender.get_channel_type() == "whatsapp"


@pytest.mark.asyncio
async def test_get_sender_telegram():
    sender = get_sender("telegram")
    assert sender.get_channel_type() == "telegram"


@pytest.mark.asyncio
async def test_get_sender_unknown():
    with pytest.raises(ValueError, match="Unknown channel type"):
        get_sender("slack")


@pytest.mark.asyncio
async def test_register_new_sender():
    register_sender("fake", _FakeSender)
    try:
        sender = get_sender("fake")
        assert isinstance(sender, _FakeSender)
    finally:
        _senders.pop("fake", None)


@pytest.mark.asyncio
async def test_send_via_channel_success():
    config = {"wa_api_key": "abc", "wa_phone_id": "123", "wa_enabled": "si",
              "wa_api_url": "https://graph.facebook.com/v18.0"}
    mock_resp = _mock_response(is_success=True, json_data={"messages": [{"id": "wamid.t"}]})
    mock_client = _async_client_mock(post_return_value=mock_resp)
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await send_via_channel("whatsapp", "+52123", "Test", "Hello", config)
    assert result["sent"] is True


@pytest.mark.asyncio
async def test_send_via_channel_invalid_config():
    result = await send_via_channel("whatsapp", "+52123", "Test", "Hello", {})
    assert result["sent"] is False
    assert "Missing config" in result["reason"]


def test_create_push_sender_func_whatsapp():
    def get_config():
        return {"wa_api_key": "abc", "wa_phone_id": "123", "wa_enabled": "si",
                "wa_api_url": "https://graph.facebook.com/v18.0"}
    sender_func = create_push_sender_func("whatsapp", get_config)
    assert callable(sender_func)

    mock_resp = _mock_response(is_success=True, json_data={"messages": [{"id": "wamid.p"}]})
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_resp
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = sender_func({}, "Test", "Hello")
    assert result["sent"] is True


def test_create_push_sender_func_telegram():
    def get_config():
        return {"tg_bot_token": "abc", "tg_chat_id": "-100123", "tg_enabled": "si"}
    sender_func = create_push_sender_func("telegram", get_config)
    assert callable(sender_func)

    mock_resp = _mock_response(is_success=True, json_data={"ok": True, "result": {"message_id": 1}})
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_resp
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = sender_func({}, "Test", "<b>Hello</b>")
    assert result["sent"] is True


def test_create_push_sender_func_invalid_config():
    def get_config():
        return {}
    sender_func = create_push_sender_func("whatsapp", get_config)
    result = sender_func({}, "Test", "Hello")
    assert result["sent"] is False
    assert "Missing config" in result["reason"]
