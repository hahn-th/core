"""Tests for HomematicIP Cloud alarm control panel."""

from homematicip.model.model import Model

from homeassistant.components.alarm_control_panel import (
    DOMAIN as ALARM_CONTROL_PANEL_DOMAIN,
)
from homeassistant.components.homematicip_cloud import DOMAIN as HMIPC_DOMAIN
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .helper import get_and_check_entity_basics


async def _async_manipulate_security_zones(
    hass: HomeAssistant,
    model: Model,
    internal_active=False,
    external_active=False,
    alarm_triggered=False,
):
    """Set new values on hmip security zones."""
    model.home.functionalHomes["SECURITY_AND_ALARM"].alarmActive = alarm_triggered
    external_zone_id = model.home.functionalHomes["SECURITY_AND_ALARM"].securityZones[
        "EXTERNAL"
    ]
    internal_zone_id = model.home.functionalHomes["SECURITY_AND_ALARM"].securityZones[
        "INTERNAL"
    ]

    external_zone = model.groups[external_zone_id]
    external_zone.active = external_active
    internal_zone = model.groups[internal_zone_id]
    internal_zone.active = internal_active

    model.home.fire_on_update()
    await hass.async_block_till_done()


async def test_manually_configured_platform(hass: HomeAssistant) -> None:
    """Test that we do not set up an access point."""
    assert await async_setup_component(
        hass,
        ALARM_CONTROL_PANEL_DOMAIN,
        {ALARM_CONTROL_PANEL_DOMAIN: {"platform": HMIPC_DOMAIN}},
    )

    assert not hass.data.get(HMIPC_DOMAIN)


async def test_hmip_alarm_control_panel(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipAlarmControlPanel."""
    entity_id = "alarm_control_panel.hmip_alarm_control_panel"
    entity_name = "HmIP Alarm Control Panel"
    device_model = None
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_groups=[
            "00000000-0000-0000-0000-000000000005",
            "00000000-0000-0000-0000-000000000016",
        ]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "disarmed"
    assert not hmip_device

    await hass.services.async_call(
        "alarm_control_panel", "alarm_arm_away", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "home/security/setZonesActivation",
        {
            "zonesActivation": {
                "INTERNAL": True,
                "EXTERNAL": True,
            }
        },
    )

    await _async_manipulate_security_zones(
        hass, mock_hap.model, internal_active=True, external_active=True
    )
    assert hass.states.get(entity_id).state is STATE_ALARM_ARMED_AWAY

    await hass.services.async_call(
        "alarm_control_panel", "alarm_arm_home", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "home/security/setZonesActivation",
        {
            "zonesActivation": {
                "INTERNAL": False,
                "EXTERNAL": True,
            }
        },
    )

    await _async_manipulate_security_zones(hass, mock_hap.model, external_active=True)
    assert hass.states.get(entity_id).state is STATE_ALARM_ARMED_HOME

    await hass.services.async_call(
        "alarm_control_panel", "alarm_disarm", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "home/security/setZonesActivation",
        {
            "zonesActivation": {
                "INTERNAL": False,
                "EXTERNAL": False,
            }
        },
    )

    await _async_manipulate_security_zones(hass, mock_hap.model)
    assert hass.states.get(entity_id).state is STATE_ALARM_DISARMED

    await hass.services.async_call(
        "alarm_control_panel", "alarm_arm_away", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "home/security/setZonesActivation",
        {
            "zonesActivation": {
                "INTERNAL": True,
                "EXTERNAL": True,
            }
        },
    )
    await _async_manipulate_security_zones(
        hass,
        mock_hap.model,
        internal_active=True,
        external_active=True,
        alarm_triggered=True,
    )
    assert hass.states.get(entity_id).state is STATE_ALARM_TRIGGERED

    await hass.services.async_call(
        "alarm_control_panel", "alarm_arm_home", {"entity_id": entity_id}, blocking=True
    )
    mock_hap.runner.rest_connection.async_post.assert_called_with(
        "home/security/setZonesActivation",
        {
            "zonesActivation": {
                "INTERNAL": False,
                "EXTERNAL": True,
            }
        },
    )

    await _async_manipulate_security_zones(
        hass, mock_hap.model, external_active=True, alarm_triggered=True
    )
    assert hass.states.get(entity_id).state is STATE_ALARM_TRIGGERED
