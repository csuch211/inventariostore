"""Tests for WhatsAppSender."""

"""Tests for WhatsAppSender."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.messaging.whatsapp import WhatsAppSender


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
    return WhatsAppSender()


@pytest.mark.asyncio
async def test_validate_config_valid(sender):
    config = {"wa_api_key": "abc", "wa_phone_id": "123456789"}
    valid, msg = sender.validate_config(config)
    assert valid is True
    assert msg == ""


@pytest.mark.asyncio
async def test_validate_config_missing_keys(sender):
    valid, msg = sender.validate_config({"wa_api_key": "abc"})
    assert valid is False
    assert "wa_phone_id" in msg


@pytest.mark.asyncio
async def test_validate_config_empty_values(sender):
    valid, msg = sender.validate_config({"wa_api_key": "", "wa_phone_id": "123"})
    assert valid is False
    assert "wa_api_key is empty" in msg


@pytest.mark.asyncio
async def test_send_disabled_channel(sender):
    config = {"wa_api_key": "abc", "wa_phone_id": "123", "wa_enabled": "no"}
    result = await sender.send("+521234567890", "Test", "Hello", config)
    assert result["sent"] is False
    assert "disabled" in result["reason"].lower()


@pytest.mark.asyncio
async def test_send_success(sender):
    config = {"wa_api_key": "abc", "wa_phone_id": "123", "wa_enabled": "si",
              "wa_api_url": "https://graph.facebook.com/v18.0"}

    mock_resp = _mock_response(is_success=True, json_data={"messages": [{"id": "wamid.test123"}]})

    mock_client = _async_client_mock(post_return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await sender.send("+521234567890", "Test", "Hello", config)

    assert result["sent"] is True
    assert result["message_id"] == "wamid.test123"


@pytest.mark.asyncio
async def test_send_api_error(sender):
    config = {"wa_api_key": "abc", "wa_phone_id": "123", "wa_enabled": "si",
              "wa_api_url": "https://graph.facebook.com/v18.0"}

    mock_resp = _mock_response(is_success=False, json_data={"error": {"message": "Rate limit exceeded"}}, text="Rate limit")

    mock_client = _async_client_mock(post_return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await sender.send("+521234567890", "Test", "Hello", config)

    assert result["sent"] is False
    assert "Rate limit" in result["reason"]


@pytest.mark.asyncio
async def test_send_network_error(sender):
    config = {"wa_api_key": "abc", "wa_phone_id": "123", "wa_enabled": "si",
              "wa_api_url": "https://graph.facebook.com/v18.0"}

    mock_client = _async_client_mock()
    mock_client.post.side_effect = ConnectionError("Network unreachable")

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await sender.send("+521234567890", "Test", "Hello", config)

    assert result["sent"] is False
    assert "Network unreachable" in result["reason"]


@pytest.mark.asyncio
async def test_get_channel_type(sender):
    assert sender.get_channel_type() == "whatsapp"


@pytest.mark.asyncio
async def test_send_invalid_config(sender):
    result = await sender.send("dest", "subj", "body", {})
    assert result["sent"] is False
