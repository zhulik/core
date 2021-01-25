"""Test cloud system health."""
import asyncio
from unittest.mock import Mock

from aiohttp import ClientError

from homeassistant.setup import async_setup_component
from homeassistant.util.dt import utcnow

from tests.common import get_system_health_info


async def test_cloud_system_health(hass, aioclient_mock):
    """Test cloud system health."""
    aioclient_mock.get("https://cloud.bla.com/status", text="")
    aioclient_mock.get("https://cert-server", text="")
    aioclient_mock.get(
        "https://cognito-idp.us-east-1.amazonaws.com/AAAA/.well-known/jwks.json",
        exc=ClientError,
    )
    hass.config.components.add("cloud")
    assert await async_setup_component(hass, "system_health", {})
    now = utcnow()

    hass.data["cloud"] = Mock(
        region="us-east-1",
        user_pool_id="AAAA",
        relayer="wss://cloud.bla.com/websocket_api",
        acme_directory_server="https://cert-server",
        is_logged_in=True,
        remote=Mock(is_connected=False),
        expiration_date=now,
        is_connected=True,
        client=Mock(
            prefs=Mock(
                remote_enabled=True,
                alexa_enabled=True,
                google_enabled=False,
            )
        ),
    )

    info = await get_system_health_info(hass, "cloud")

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info == {
        "logged_in": True,
        "subscription_expiration": now,
        "relayer_connected": True,
        "remote_enabled": True,
        "remote_connected": False,
        "alexa_enabled": True,
        "google_enabled": False,
        "can_reach_cert_server": "ok",
        "can_reach_cloud_auth": {"type": "failed", "error": "unreachable"},
        "can_reach_cloud": "ok",
    }
