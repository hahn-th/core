"""Support for HomematicIP Cloud binary sensor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypedDict

# assert not ha_state.attributes.get(ATTR_DEVICE_OVERHEATED)
# assert not ha_state.attributes.get(ATTR_DEVICE_OVERLOADED)
# assert not ha_state.attributes.get(ATTR_DEVICE_UNTERVOLTAGE)
# assert not ha_state.attributes.get(ATTR_DUTY_CYCLE_REACHED)
# assert not ha_state.attributes.get(ATTR_CONFIG_PENDING)
# await async_manipulate_test_data(hass, hmip_device, "deviceOverheated", True)
# await async_manipulate_test_data(hass, hmip_device, "deviceOverloaded", True)
# await async_manipulate_test_data(hass, hmip_device, "deviceUndervoltage", True)
# await async_manipulate_test_data(hass, hmip_device, "dutyCycle", True)
# await async_manipulate_test_data(hass, hmip_device, "configPending", True)
# ha_state = hass.states.get(entity_id)
# assert ha_state.attributes[ATTR_DEVICE_OVERHEATED]
# assert ha_state.attributes[ATTR_DEVICE_OVERLOADED]
# assert ha_state.attributes[ATTR_DEVICE_UNTERVOLTAGE]
# assert ha_state.attributes[ATTR_DUTY_CYCLE_REACHED]
# assert ha_state.attributes[ATTR_CONFIG_PENDING]
from homematicip.model.enums import SmokeDetectorAlarmType, WindowState
from homematicip.model.hmip_base import HmipBaseModel
from homematicip.model.model_components import FunctionalChannel

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN as HMIPC_DOMAIN, HomematicipGenericEntity
from .hap import HomematicipHAP

ATTR_ACCELERATION_SENSOR_MODE = "acceleration_sensor_mode"
ATTR_ACCELERATION_SENSOR_NEUTRAL_POSITION = "acceleration_sensor_neutral_position"
ATTR_ACCELERATION_SENSOR_SENSITIVITY = "acceleration_sensor_sensitivity"
ATTR_ACCELERATION_SENSOR_TRIGGER_ANGLE = "acceleration_sensor_trigger_angle"
ATTR_INTRUSION_ALARM = "intrusion_alarm"
ATTR_MOISTURE_DETECTED = "moisture_detected"
ATTR_MOTION_DETECTED = "motion_detected"
ATTR_POWER_MAINS_FAILURE = "power_mains_failure"
ATTR_PRESENCE_DETECTED = "presence_detected"
ATTR_SMOKE_DETECTOR_ALARM = "smoke_detector_alarm"
ATTR_TODAY_SUNSHINE_DURATION = "today_sunshine_duration_in_minutes"
ATTR_WATER_LEVEL_DETECTED = "water_level_detected"
ATTR_WINDOW_STATE = "window_state"
ATTR_EVENT_DELAY = "event_delay"

GROUP_ATTRIBUTES = {
    "moistureDetected": ATTR_MOISTURE_DETECTED,
    "motionDetected": ATTR_MOTION_DETECTED,
    "powerMainsFailure": ATTR_POWER_MAINS_FAILURE,
    "presenceDetected": ATTR_PRESENCE_DETECTED,
    "waterlevelDetected": ATTR_WATER_LEVEL_DETECTED,
}

SAM_DEVICE_ATTRIBUTES = {
    "accelerationSensorNeutralPosition": ATTR_ACCELERATION_SENSOR_NEUTRAL_POSITION,
    "accelerationSensorMode": ATTR_ACCELERATION_SENSOR_MODE,
    "accelerationSensorSensitivity": ATTR_ACCELERATION_SENSOR_SENSITIVITY,
    "accelerationSensorTriggerAngle": ATTR_ACCELERATION_SENSOR_TRIGGER_ANGLE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomematicIP Cloud binary sensor from a config entry."""
    hap = hass.data[HMIPC_DOMAIN][config_entry.unique_id]
    entities: list[HomematicipGenericEntity] = []
    entities.append(HomematicipCloudConnectionSensor(hap))
    for device in hap.model.devices.values():
        if device.functionalChannels:
            channel: FunctionalChannel = None
            for channel in device.functionalChannels.values():
                for entity_description in SENSORS:
                    if entity_description.exists_fn(channel):
                        entity = HmipSensorEntity(
                            hap=hap,
                            device=device,
                            channel_index=channel.index,
                            entity_description=entity_description,
                            is_multi_channel=len(device.functionalChannels) > 2,
                        )
                        entities.append(entity)

    for group in hap.model.groups.values():
        if group.type in MapGroups:
            for target_dict in MapGroups[group.type]:
                target_group_type: type = target_dict["type"]
                entities.append(
                    target_group_type(
                        hap=hap,
                        device=group,
                        post=target_dict["post"],
                    )
                )

    async_add_entities(entities)


class HomematicipCloudConnectionSensor(HomematicipGenericEntity, BinarySensorEntity):
    """Representation of the HomematicIP cloud connection sensor."""

    def __init__(self, hap: HomematicipHAP) -> None:
        """Initialize the cloud connection sensor."""
        super().__init__(hap, hap.model.home)

    @property
    def name(self) -> str:
        """Return the name cloud connection entity."""

        name = "Cloud Connection"
        # Add a prefix to the name if the homematic ip home has a name.
        return name if not self._hap.runner.name else f"{self._hap.runner.name} {name}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        # Adds a sensor to the existing HAP device
        return DeviceInfo(
            identifiers={
                # Serial numbers of Homematic IP device
                (HMIPC_DOMAIN, self._hap.model.home.id)
            }
        )

    @property
    def icon(self) -> str:
        """Return the icon of the access point entity."""
        return (
            "mdi:access-point-network"
            if self._hap.model.home.connected
            else "mdi:access-point-network-off"
        )

    @property
    def is_on(self) -> bool:
        """Return true if hap is connected to cloud."""
        return self._hap.model.home.connected

    @property
    def available(self) -> bool:
        """Sensor is always available."""
        return True


class HomematicipBaseActionSensor(HomematicipGenericEntity, BinarySensorEntity):
    """Representation of the HomematicIP base action sensor."""

    _attr_device_class = BinarySensorDeviceClass.MOVING

    @property
    def is_on(self) -> bool:
        """Return true if acceleration is detected."""
        return self.functional_channel.accelerationSensorTriggered

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the acceleration sensor."""
        state_attr = super().extra_state_attributes

        for attr, attr_key in SAM_DEVICE_ATTRIBUTES.items():
            if attr_value := getattr(self.functional_channel, attr, None):
                state_attr[attr_key] = attr_value

        return state_attr


class HomematicipMultiContactInterface(HomematicipGenericEntity, BinarySensorEntity):
    """Representation of the HomematicIP multi room/area contact interface."""

    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(
        self,
        hap: HomematicipHAP,
        device: HmipBaseModel,
        post: str | None = None,
        channel_index: int | None = None,
        is_multi_channel: bool = False,
    ) -> None:
        """Initialize the multi contact interface."""
        super().__init__(
            hap,
            device,
            post,
            channel_index,
            is_multi_channel=len(device.functionalChannels) > 2,
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the contact interface is on/open."""
        if self.functional_channel.windowState is None:
            return None
        return self.functional_channel.windowState != WindowState.CLOSED.value


class HomematicipContactInterface(HomematicipMultiContactInterface, BinarySensorEntity):
    """Representation of the HomematicIP contact interface."""


class HomematicipShutterContact(HomematicipMultiContactInterface, BinarySensorEntity):
    """Representation of the HomematicIP shutter contact."""

    _attr_device_class = BinarySensorDeviceClass.DOOR

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the Shutter Contact."""
        state_attr = super().extra_state_attributes
        state_attr[ATTR_EVENT_DELAY] = self.functional_channel.eventDelay
        return state_attr


class HomematicipShutterContectRotaryHandle(HomematicipShutterContact):
    """Representation of the HomematicIP shutter contact with rotary handle."""

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the Shutter Contact."""
        state_attr = super().extra_state_attributes

        windowState = getattr(self.functional_channel, "windowState", None)
        if windowState and windowState != WindowState.CLOSED.value:
            state_attr[ATTR_WINDOW_STATE] = self.functional_channel.windowState

        return state_attr


class HomematicipSecurityZoneSensorGroup(HomematicipGenericEntity, BinarySensorEntity):
    """Representation of the HomematicIP security zone sensor group."""

    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, hap: HomematicipHAP, device, post: str) -> None:
        """Initialize security zone group."""
        device.modelType = f"HmIP-{post}"
        super().__init__(hap, device, post=post)

    @property
    def available(self) -> bool:
        """Security-Group available."""
        # A security-group must be available, and should not be affected by
        # the individual availability of group members.
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the security zone group."""
        state_attr = super().extra_state_attributes

        for attr, attr_key in GROUP_ATTRIBUTES.items():
            if attr_value := getattr(self._device, attr, None):
                state_attr[attr_key] = attr_value

        window_state = getattr(self._device, "windowState", None)
        if window_state and window_state != WindowState.CLOSED.value:
            state_attr[ATTR_WINDOW_STATE] = str(window_state)

        return state_attr

    @property
    def is_on(self) -> bool:
        """Return true if security issue detected."""
        if (
            self._device.motionDetected
            or self._device.presenceDetected
            or self._device.unreach
            or self._device.sabotage
        ):
            return True

        if (
            self._device.windowState is not None
            and self._device.windowState != WindowState.CLOSED.value
        ):
            return True
        return False


class HomematicipSecuritySensorGroup(
    HomematicipSecurityZoneSensorGroup, BinarySensorEntity
):
    """Representation of the HomematicIP security group."""

    def __init__(self, hap: HomematicipHAP, device, post) -> None:
        """Initialize security group."""
        super().__init__(hap, device, post=post)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the security group."""
        state_attr = super().extra_state_attributes

        smoke_detector_at = getattr(self._device, "smokeDetectorAlarmType", None)
        if smoke_detector_at:
            if smoke_detector_at == SmokeDetectorAlarmType.PRIMARY_ALARM.value:
                state_attr[ATTR_SMOKE_DETECTOR_ALARM] = str(smoke_detector_at)
            if smoke_detector_at == SmokeDetectorAlarmType.INTRUSION_ALARM.value:
                state_attr[ATTR_INTRUSION_ALARM] = str(smoke_detector_at)
        return state_attr

    @property
    def is_on(self) -> bool:
        """Return true if safety issue detected."""
        if super().is_on:
            # parent is on
            return True

        if (
            self._device.powerMainsFailure
            or self._device.moistureDetected
            or self._device.waterlevelDetected
            or self._device.lowBat
            or self._device.dutyCycle
        ):
            return True

        if (
            self._device.smokeDetectorAlarmType is not None
            and self._device.smokeDetectorAlarmType
            != SmokeDetectorAlarmType.IDLE_OFF.value
        ):
            return True

        return False


@dataclass(kw_only=True, frozen=True)
class HmipEntityDescription(BinarySensorEntityDescription):
    """SensorEntityDescription for HmIP Sensors.

    extra_state_attributes is the mapping between the hmip device attribute (key) and the home assistant extra-state (value).
    """

    name: str | None = None
    value_fn: Callable[[FunctionalChannel], bool | None]
    extra_state_attributes: dict | None = None
    exists_fn: Callable[[FunctionalChannel], bool] = lambda channel: False


class HmipSensorEntity(HomematicipGenericEntity, BinarySensorEntity):
    """EntityDescription for HmIP-ESI Sensors."""

    entity_description: HmipEntityDescription

    def __init__(
        self,
        hap: HomematicipHAP,
        device: HomematicipGenericEntity,
        channel_index: int,
        entity_description: HmipEntityDescription,
        is_multi_channel: bool = False,
    ) -> None:
        """Initialize Sensor Entity."""
        super().__init__(
            hap=hap,
            device=device,
            channel_index=channel_index,
            post=entity_description.name,
            is_multi_channel=is_multi_channel,
        )
        self.entity_description = entity_description

    @property
    def is_on(self) -> bool | None:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.functional_channel)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        state_attr = super().extra_state_attributes
        extra_state_attr_fn = self.entity_description.extra_state_attributes

        if extra_state_attr_fn:
            for key, value in extra_state_attr_fn.items():
                if hasattr(self.functional_channel, key):
                    state_attr[value] = getattr(self.functional_channel, key)

        return state_attr


SENSORS: tuple[HmipEntityDescription, ...] = (
    HmipEntityDescription(
        key="acceleration",
        name="Acceleration",
        value_fn=lambda channel: channel.accelerationSensorTriggered,
        exists_fn=lambda channel: hasattr(channel, "accelerationSensorTriggered"),
        device_class=BinarySensorDeviceClass.MOVING,
        extra_state_attributes=SAM_DEVICE_ATTRIBUTES,
    ),
    HmipEntityDescription(
        key="motion_sensor",
        name="Motion",
        value_fn=lambda channel: channel.motionDetected,
        exists_fn=lambda channel: hasattr(channel, "motionDetected"),
        device_class=BinarySensorDeviceClass.MOTION,
    ),
    HmipEntityDescription(
        key="presence_sensor",
        name="Presence",
        value_fn=lambda channel: channel.presenceDetected,
        exists_fn=lambda channel: hasattr(channel, "presenceDetected"),
        device_class=BinarySensorDeviceClass.PRESENCE,
    ),
    HmipEntityDescription(
        key="smoke_detector",
        name="Smoke",
        value_fn=lambda channel: getattr(channel, "smokeDetectorAlarmType", None)
        == SmokeDetectorAlarmType.PRIMARY_ALARM.value,
        exists_fn=lambda channel: hasattr(channel, "smokeDetectorAlarmType"),
        device_class=BinarySensorDeviceClass.SMOKE,
    ),
    HmipEntityDescription(
        key="moisture",
        name="Moisture",
        value_fn=lambda channel: channel.moistureDetected,
        exists_fn=lambda channel: hasattr(channel, "moistureDetected"),
        device_class=BinarySensorDeviceClass.MOISTURE,
    ),
    HmipEntityDescription(
        key="water",
        name="Water",
        value_fn=lambda channel: channel.waterlevelDetected,
        exists_fn=lambda channel: hasattr(channel, "waterlevelDetected"),
        device_class=BinarySensorDeviceClass.MOISTURE,
    ),
    HmipEntityDescription(
        key="storm",
        name="Storm",
        value_fn=lambda channel: channel.storm,
        exists_fn=lambda channel: hasattr(channel, "storm"),
    ),
    HmipEntityDescription(
        key="raining",
        name="Raining",
        value_fn=lambda channel: channel.raining,
        exists_fn=lambda channel: hasattr(channel, "raining"),
    ),
    HmipEntityDescription(
        key="sunshine",
        name="Sunshine",
        value_fn=lambda channel: channel.sunshine,
        exists_fn=lambda channel: hasattr(channel, "sunshine"),
        device_class=BinarySensorDeviceClass.LIGHT,
    ),
    HmipEntityDescription(
        key="battery",
        name="Battery",
        value_fn=lambda channel: channel.lowBat,
        exists_fn=lambda channel: hasattr(channel, "lowBat"),
        device_class=BinarySensorDeviceClass.BATTERY,
    ),
    HmipEntityDescription(
        key="mains_failure",
        value_fn=lambda channel: not channel.powerMainsFailure,
        exists_fn=lambda channel: hasattr(channel, "powerMainsFailure"),
        device_class=BinarySensorDeviceClass.POWER,
    ),
    HmipEntityDescription(
        key="window",
        value_fn=lambda channel: None
        if channel.windowState is None
        else channel.windowState != WindowState.CLOSED.value,
        exists_fn=lambda channel: hasattr(channel, "windowState"),
        device_class=BinarySensorDeviceClass.OPENING,
    ),
)


class TypedMappingDict(TypedDict):
    """TypedDict for mapping functional channel types to their classes."""

    type: type
    is_multi_channel: bool
    post: str | None


MapGroups: dict[str, list[TypedMappingDict]] = {
    "SECURITY": [
        {
            "type": HomematicipSecuritySensorGroup,
            "is_multi_channel": False,
            "post": "Sensors",
        }
    ],
    "SECURITY_ZONE": [
        {
            "type": HomematicipSecurityZoneSensorGroup,
            "is_multi_channel": False,
            "post": "SecurityZone",
        }
    ],
}
