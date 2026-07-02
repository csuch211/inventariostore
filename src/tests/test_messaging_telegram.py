"""Tests for TelegramSender."""

"""Tests for TelegramSender."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.messaging.telegram import TelegramSender


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


@pytest.fixture
def sender():
    return TelegramSender()


@pytest.mark.asyncio
async def test_validate_config_valid(sender):
    config = {"tg_bot_token": "bot123:abc", "tg_chat_id": "-100123456789"}
    valid, msg = sender.validate_config(config)
    assert valid is True
    assert msg == ""


@pytest.mark.asyncio
async def test_validate_config_missing_keys(sender):
    valid, msg = sender.validate_config({"tg_bot_token": "abc"})
    assert valid is False
    assert "tg_chat_id" in msg


@pytest.mark.asyncio
async def test_validate_config_empty_values(sender):
    valid, msg = sender.validate_config({"tg_bot_token": "", "tg_chat_id": "123"})
    assert valid is False
    assert "tg_bot_token is empty" in msg


@pytest.mark.asyncio
async def test_send_disabled_channel(sender):
    config = {"tg_bot_token": "abc", "tg_chat_id": "123", "tg_enabled": "no"}
    result = await sender.send("-100123", "Test", "Hello", config)
    assert result["sent"] is False
    assert "disabled" in result["reason"].lower()


@pytest.mark.asyncio
async def test_send_success(sender):
    config = {"tg_bot_token": "bot123:abc", "tg_chat_id": "-100123456789", "tg_enabled": "si"}

    mock_resp = _mock_response(is_success=True, json_data={"ok": True, "result": {"message_id": 42}})
    mock_client = _async_client_mock(post_return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await sender.send("-100123456789", "Test", "<b>Hello</b>", config)

    assert result["sent"] is True
    assert result["message_id"] == "42"


@pytest.mark.asyncio
async def test_send_api_error(sender):
    config = {"tg_bot_token": "bot123:abc", "tg_chat_id": "-100123456789", "tg_enabled": "si"}

    mock_resp = _mock_response(is_success=False, json_data={"ok": False, "description": "Forbidden: bot was blocked"}, text="Forbidden")
    mock_client = _async_client_mock(post_return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await sender.send("-100123456789", "Test", "Hello", config)

    assert result["sent"] is False
    assert "Forbidden" in result["reason"]


@pytest.mark.asyncio
async def test_send_network_error(sender):
    config = {"tg_bot_token": "bot123:abc", "tg_chat_id": "-100123456789", "tg_enabled": "si"}

    mock_client = _async_client_mock()
    mock_client.post.side_effect = TimeoutError("Connection timed out")

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await sender.send("-100123456789", "Test", "Hello", config)

    assert result["sent"] is False
    assert "timed out" in result["reason"].lower()


@pytest.mark.asyncio
async def test_get_channel_type(sender):
    assert sender.get_channel_type() == "telegram"


@pytest.mark.asyncio
async def test_send_invalid_config(sender):
    result = await sender.send("dest", "subj", "body", {})
    assert result["sent"] is False
