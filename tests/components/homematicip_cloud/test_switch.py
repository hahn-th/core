"""Tests for HomematicIP Cloud switch."""

from homeassistant.components.homematicip_cloud import DOMAIN as HMIPC_DOMAIN
from homeassistant.components.homematicip_cloud.generic_entity import (
    ATTR_GROUP_MEMBER_UNREACHABLE,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .helper import async_manipulate_test_data, get_and_check_entity_basics


async def test_manually_configured_platform(hass: HomeAssistant) -> None:
    """Test that we do not set up an access point."""
    assert await async_setup_component(
        hass, SWITCH_DOMAIN, {SWITCH_DOMAIN: {"platform": HMIPC_DOMAIN}}
    )
    assert not hass.data.get(HMIPC_DOMAIN)


async def test_hmip_switch(hass: HomeAssistant, default_mock_hap_factory) -> None:
    """Test HomematicipSwitch."""
    entity_id = "switch.schrank"
    entity_name = "Schrank"
    device_model = "HMIP-PS"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000110"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )

    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "device/control/setSwitchState",
        {
            "channelIndex": 1,
            "deviceId": "3014F7110000000000000110",
            "on": False,
        },
    )

    await async_manipulate_test_data(hass, hmip_device, "on", False)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )

    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "device/control/setSwitchState",
        {
            "channelIndex": 1,
            "deviceId": "3014F7110000000000000110",
            "on": True,
        },
    )
    await async_manipulate_test_data(hass, hmip_device, "on", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_switch_input(hass: HomeAssistant, default_mock_hap_factory) -> None:
    """Test HomematicipSwitch."""
    entity_id = "switch.wohnzimmer_beleuchtung"
    entity_name = "Wohnzimmer Beleuchtung"
    device_model = "HmIP-FSI16"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000HmIPFSI16"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "device/control/setSwitchState",
        {
            "channelIndex": 1,
            "deviceId": "3014F7110000000HmIPFSI16",
            "on": False,
        },
    )
    await async_manipulate_test_data(hass, hmip_device, "on", False)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "device/control/setSwitchState",
        {
            "channelIndex": 1,
            "deviceId": "3014F7110000000HmIPFSI16",
            "on": True,
        },
    )
    await async_manipulate_test_data(hass, hmip_device, "on", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_switch_measuring(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipSwitchMeasuring."""
    entity_id = "switch.pc"
    entity_name = "Pc"
    device_model = "HMIP-PSM"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000008"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "device/control/setSwitchState",
        {
            "channelIndex": 1,
            "deviceId": "3014F7110000000000000008",
            "on": False,
        },
    )
    await async_manipulate_test_data(hass, hmip_device, "on", False)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "device/control/setSwitchState",
        {
            "channelIndex": 1,
            "deviceId": "3014F7110000000000000008",
            "on": True,
        },
    )
    await async_manipulate_test_data(hass, hmip_device, "on", True)
    await async_manipulate_test_data(hass, hmip_device, "currentPowerConsumption", 50)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_group_switch(hass: HomeAssistant, default_mock_hap_factory) -> None:
    """Test HomematicipGroupSwitch."""
    entity_id = "switch.strom_group"
    entity_name = "Strom Group"
    device_model = None
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_groups=["00000000-0000-0000-0000-000000000018"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "group/switching/setState",
        {
            "groupId": "00000000-0000-0000-0000-000000000018",
            "on": False,
        },
    )
    await async_manipulate_test_data(hass, hmip_device, "on", False)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "group/switching/setState",
        {
            "groupId": "00000000-0000-0000-0000-000000000018",
            "on": True,
        },
    )
    await async_manipulate_test_data(hass, hmip_device, "on", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON

    assert not ha_state.attributes.get(ATTR_GROUP_MEMBER_UNREACHABLE)
    await async_manipulate_test_data(hass, hmip_device, "unreach", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_GROUP_MEMBER_UNREACHABLE]


async def test_hmip_multi_switch(hass: HomeAssistant, default_mock_hap_factory) -> None:
    """Test HomematicipMultiSwitch."""
    entity_id = "switch.jalousien_1_kizi_2_schlazi_channel1"
    entity_name = "Jalousien - 1 KiZi, 2 SchlaZi Channel1"
    device_model = "HmIP-PCBS2"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=[
            "3014F7110000000000BCBB11",
        ]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "device/control/setSwitchState",
        {
            "channelIndex": 1,
            "deviceId": "3014F7110000000000BCBB11",
            "on": True,
        },
    )
    await async_manipulate_test_data(hass, hmip_device, "on", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "device/control/setSwitchState",
        {
            "channelIndex": 1,
            "deviceId": "3014F7110000000000BCBB11",
            "on": False,
        },
    )
    await async_manipulate_test_data(hass, hmip_device, "on", False)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF


async def test_hmip_wired_multi_switch_channel_1(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipMultiSwitch."""
    entity_id = "switch.fernseher_wohnzimmer"
    entity_name = "Fernseher (Wohnzimmer)"
    device_model = "HmIPW-DRS8"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=[
            "3014F711000WIREDSWITCH8",
        ]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )

    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "device/control/setSwitchState",
        {
            "channelIndex": 1,
            "deviceId": "3014F711000WIREDSWITCH8",
            "on": False,
        },
    )
    await async_manipulate_test_data(hass, hmip_device, "on", False, channel=1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "device/control/setSwitchState",
        {
            "channelIndex": 1,
            "deviceId": "3014F711000WIREDSWITCH8",
            "on": True,
        },
    )
    await async_manipulate_test_data(hass, hmip_device, "on", True, channel=1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_wired_multi_switch_channel_2(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipMultiSwitch."""
    entity_id = "switch.steckdosen_wohnzimmer"
    entity_name = "Steckdosen (Wohnzimmer)"
    device_model = "HmIPW-DRS8"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=[
            "3014F711000WIREDSWITCH8",
        ]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )

    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "device/control/setSwitchState",
        {
            "channelIndex": 2,
            "deviceId": "3014F711000WIREDSWITCH8",
            "on": False,
        },
    )
    await async_manipulate_test_data(hass, hmip_device, "on", False, channel=2)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "device/control/setSwitchState",
        {
            "channelIndex": 2,
            "deviceId": "3014F711000WIREDSWITCH8",
            "on": True,
        },
    )
    await async_manipulate_test_data(hass, hmip_device, "on", True, channel=2)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON
