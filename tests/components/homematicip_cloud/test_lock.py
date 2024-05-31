"""Tests for HomematicIP Cloud locks."""

from unittest.mock import AsyncMock, patch

from homematicip.model.enums import LockState, MotorState
import pytest

from homeassistant.components.homematicip_cloud import DOMAIN as HMIPC_DOMAIN
from homeassistant.components.lock import DOMAIN, STATE_LOCKING, STATE_UNLOCKING
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component

from .helper import async_manipulate_test_data, get_and_check_entity_basics


async def test_manually_configured_platform(hass: HomeAssistant) -> None:
    """Test that we do not set up an access point."""
    assert await async_setup_component(
        hass, DOMAIN, {DOMAIN: {"platform": HMIPC_DOMAIN}}
    )
    assert not hass.data.get(HMIPC_DOMAIN)


async def test_hmip_doorlockdrive(
    hass: HomeAssistant, default_mock_hap_factory, mocker
) -> None:
    """Test HomematicipDoorLockDrive."""
    entity_id = "lock.haustuer"
    entity_name = "Haustuer"
    device_model = "HmIP-DLD"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000DLD"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    await hass.services.async_call(
        "lock",
        "open",
        {"entity_id": entity_id},
        blocking=True,
    )

    assert (
        mock_hap.runner.rest_connection.async_post.mock_calls[-1][1][1]["deviceId"]
        == hmip_device.id
    )
    assert (
        mock_hap.runner.rest_connection.async_post.mock_calls[-1][1][1]["channelIndex"]
        == 1
    )
    assert (
        mock_hap.runner.rest_connection.async_post.mock_calls[-1][1][1][
            "targetLockState"
        ]
        == LockState.OPEN.value
    )

    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": entity_id},
        blocking=True,
    )

    assert (
        mock_hap.runner.rest_connection.async_post.mock_calls[-1][1][1]["deviceId"]
        == hmip_device.id
    )
    assert (
        mock_hap.runner.rest_connection.async_post.mock_calls[-1][1][1]["channelIndex"]
        == 1
    )
    assert (
        mock_hap.runner.rest_connection.async_post.mock_calls[-1][1][1][
            "targetLockState"
        ]
        == LockState.LOCKED.value
    )

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": entity_id},
        blocking=True,
    )

    assert (
        mock_hap.runner.rest_connection.async_post.mock_calls[-1][1][1]["deviceId"]
        == hmip_device.id
    )
    assert (
        mock_hap.runner.rest_connection.async_post.mock_calls[-1][1][1]["channelIndex"]
        == 1
    )
    assert (
        mock_hap.runner.rest_connection.async_post.mock_calls[-1][1][1][
            "targetLockState"
        ]
        == LockState.UNLOCKED.value
    )

    await async_manipulate_test_data(
        hass, hmip_device, "motorState", MotorState.CLOSING
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_LOCKING

    await async_manipulate_test_data(
        hass, hmip_device, "motorState", MotorState.OPENING
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_UNLOCKING


async def test_hmip_doorlockdrive_handle_errors(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipDoorLockDrive."""
    entity_id = "lock.haustuer"
    entity_name = "Haustuer"
    device_model = "HmIP-DLD"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000DLD"]
    )
    with patch(
        "homeassistant.components.homematicip_cloud.lock.action_set_door_state",
        new=AsyncMock(),
    ) as mocked_action:
        mocked_action.return_value = {
            "errorCode": "INVALID_NUMBER_PARAMETER_VALUE",
            "minValue": 0.0,
            "maxValue": 1.01,
        }
        get_and_check_entity_basics(
            hass, mock_hap, entity_id, entity_name, device_model
        )

        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                "lock",
                "open",
                {"entity_id": entity_id},
                blocking=True,
            )

        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                "lock",
                "lock",
                {"entity_id": entity_id},
                blocking=True,
            )

        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                "lock",
                "unlock",
                {"entity_id": entity_id},
                blocking=True,
            )
