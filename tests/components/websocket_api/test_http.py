"""Test Websocket API http module."""
from homeassistant.components.websocket_api import const


async def test_non_json_message(hass, websocket_client, caplog):
    """Test trying to serialze non JSON objects."""
    bad_data = object()
    hass.states.async_set("test_domain.entity", "testing", {"bad": bad_data})
    await websocket_client.send_json({"id": 5, "type": "get_states"})

    msg = await websocket_client.receive_json()
    assert msg["id"] == 5
    assert msg["type"] == const.TYPE_RESULT
    assert not msg["success"]
    assert (
        f"Unable to serialize to JSON. Bad data found at $.result[0](state: test_domain.entity).attributes.bad={bad_data}(<class 'object'>"
        in caplog.text
    )
