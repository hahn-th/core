"""Support for HomematicIP Cloud binary sensor."""

from __future__ import annotations

from typing import Any, TypedDict

# from homematicip.aio.device import (
#     AsyncAccelerationSensor,
#     AsyncContactInterface,
#     AsyncDevice,
#     AsyncFullFlushContactInterface,
#     AsyncFullFlushContactInterface6,
#     AsyncMotionDetectorIndoor,
#     AsyncMotionDetectorOutdoor,
#     AsyncMotionDetectorPushButton,
#     AsyncPluggableMainsFailureSurveillance,
#     AsyncPresenceDetectorIndoor,
#     AsyncRainSensor,
#     AsyncRotaryHandleSensor,
#     AsyncShutterContact,
#     AsyncShutterContactMagnetic,
#     AsyncSmokeDetector,
#     AsyncTiltVibrationSensor,
#     AsyncWaterSensor,
#     AsyncWeatherSensor,
#     AsyncWeatherSensorPlus,
#     AsyncWeatherSensorPro,
#     AsyncWiredInput32,
# )
# from homematicip.aio.group import AsyncSecurityGroup, AsyncSecurityZoneGroup
from homematicip.model.enums import SmokeDetectorAlarmType, WindowState
from homematicip.model.hmip_base import HmipBaseModel
from homematicip.model.model_components import FunctionalChannel

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
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


# ACCELERATION_SENSOR_CHANNEL => HomematicipAccelerationSensor
# TILT_VIBRATION_SENSOR_CHANNEL => HomematicipTiltVibrationSensor
# MULTI_MODE_INPUT_CHANNEL => HomematicipMultiContactInterface
# MULTI_MODE_INPUT_CHANNEL => HomematicipMultiContactInterface
# SHUTTER_CONTACT_CHANNEL => HomematicipShutterContac
# ROTARY_HANDLE_CHANNEL => HomematicipShutterContectRotaryHandle
# MOTION_DETECTION_CHANNEL => HomematicipMotionDetector
# MAINS_FAILURE_CHANNEL => HomematicipPluggableMainsFailureSurveillanceSensor
# PRESENCE_DETECTION_CHANNEL => HomematicipPresenceDetector
# SMOKE_DETECTOR_CHANNEL => HomematicipSmokeDetector
# WATER_SENSOR_CHANNEL => HomematicipWaterDetector
# WEATHER_SENSOR_CHANNEL => HomematicipStormSensor
# WEATHER_SENSOR_CHANNEL => HomematicipSunshineSensor
# WEATHER_SENSOR_CHANNEL => HomematicipRainSensor
# WEATHER_SENSOR_PLUS_CHANNEL => HomematicipStormSensor
# WEATHER_SENSOR_PLUS_CHANNEL => HomematicipSunshineSensor
# WEATHER_SENSOR_PLUS_CHANNEL => HomematicipRainSensor
# WEATHER_SENSOR_PRO_CHANNEL => HomematicipStormSensor
# WEATHER_SENSOR_PRO_CHANNEL => HomematicipSunshineSensor
# WEATHER_SENSOR_PRO_CHANNEL => HomematicipRainSensor
# AsyncDevice and device.lowBat is not None => HomematicipBatterySensor


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
                if channel.functionalChannelType in MapFunctionalChannelDevice:
                    for target_dict in MapFunctionalChannelDevice[
                        channel.functionalChannelType
                    ]:
                        target_type: type = target_dict["type"]
                        entities.append(
                            target_type(
                                hap=hap,
                                device=device,
                                channel_index=channel.index,
                                is_multi_channel=target_dict["is_multi_channel"],
                                post=target_dict["post"],
                            )
                        )

    entities = entities + [
        HomematicipBatterySensor(hap, device)
        for device in hap.model.devices.values()
        if device.functionalChannels[str(0)].lowBat is not None
    ]

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
    # for group in hap.home.groups:
    #     if isinstance(group, AsyncSecurityGroup):
    #         entities.append(HomematicipSecuritySensorGroup(hap, device=group))
    #     elif isinstance(group, AsyncSecurityZoneGroup):
    #         entities.append(HomematicipSecurityZoneSensorGroup(hap, device=group))

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


class HomematicipAccelerationSensor(HomematicipBaseActionSensor):
    """Representation of the HomematicIP acceleration sensor."""


class HomematicipTiltVibrationSensor(HomematicipBaseActionSensor):
    """Representation of the HomematicIP tilt vibration sensor."""


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


class HomematicipMotionDetector(HomematicipGenericEntity, BinarySensorEntity):
    """Representation of the HomematicIP motion detector."""

    _attr_device_class = BinarySensorDeviceClass.MOTION

    @property
    def is_on(self) -> bool:
        """Return true if motion is detected."""
        return self.functional_channel.motionDetected


class HomematicipPresenceDetector(HomematicipGenericEntity, BinarySensorEntity):
    """Representation of the HomematicIP presence detector."""

    _attr_device_class = BinarySensorDeviceClass.PRESENCE

    @property
    def is_on(self) -> bool:
        """Return true if presence is detected."""
        return self.functional_channel.presenceDetected


class HomematicipSmokeDetector(HomematicipGenericEntity, BinarySensorEntity):
    """Representation of the HomematicIP smoke detector."""

    _attr_device_class = BinarySensorDeviceClass.SMOKE

    @property
    def is_on(self) -> bool:
        """Return true if smoke is detected."""
        if self.functional_channel.smokeDetectorAlarmType:
            return (
                self.functional_channel.smokeDetectorAlarmType
                == SmokeDetectorAlarmType.PRIMARY_ALARM.value
            )
        return False


class HomematicipWaterDetector(HomematicipGenericEntity, BinarySensorEntity):
    """Representation of the HomematicIP water detector."""

    _attr_device_class = BinarySensorDeviceClass.MOISTURE

    @property
    def is_on(self) -> bool:
        """Return true, if moisture or waterlevel is detected."""
        return (
            self.functional_channel.moistureDetected
            or self.functional_channel.waterlevelDetected
        )


class HomematicipStormSensor(HomematicipGenericEntity, BinarySensorEntity):
    """Representation of the HomematicIP storm sensor."""

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:weather-windy" if self.is_on else "mdi:pinwheel-outline"

    @property
    def is_on(self) -> bool:
        """Return true, if storm is detected."""
        return self.functional_channel.storm


class HomematicipRainSensor(HomematicipGenericEntity, BinarySensorEntity):
    """Representation of the HomematicIP rain sensor."""

    _attr_device_class = BinarySensorDeviceClass.MOISTURE

    @property
    def is_on(self) -> bool:
        """Return true, if it is raining."""
        return self.functional_channel.raining


class HomematicipSunshineSensor(HomematicipGenericEntity, BinarySensorEntity):
    """Representation of the HomematicIP sunshine sensor."""

    _attr_device_class = BinarySensorDeviceClass.LIGHT

    @property
    def is_on(self) -> bool:
        """Return true if sun is shining."""
        return self.functional_channel.sunshine

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the illuminance sensor."""
        state_attr = super().extra_state_attributes

        today_sunshine_duration = getattr(
            self.functional_channel, "todaySunshineDuration", None
        )
        if today_sunshine_duration:
            state_attr[ATTR_TODAY_SUNSHINE_DURATION] = today_sunshine_duration

        return state_attr


class HomematicipBatterySensor(HomematicipGenericEntity, BinarySensorEntity):
    """Representation of the HomematicIP low battery sensor."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(self, hap: HomematicipHAP, device) -> None:
        """Initialize battery sensor."""
        super().__init__(
            hap, device, channel_index=0, is_multi_channel=False, post="Battery"
        )

    @property
    def is_on(self) -> bool:
        """Return true if battery is low."""
        return self.base_channel.lowBat


class HomematicipPluggableMainsFailureSurveillanceSensor(
    HomematicipGenericEntity, BinarySensorEntity
):
    """Representation of the HomematicIP pluggable mains failure surveillance sensor."""

    _attr_device_class = BinarySensorDeviceClass.POWER

    @property
    def is_on(self) -> bool:
        """Return true if power mains fails."""
        return not self.functional_channel.powerMainsFailure


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


MapFunctionalChannelDevice: dict[str, list[TypedMappingDict]] = {
    "ACCELERATION_SENSOR_CHANNEL": [
        {
            "type": HomematicipAccelerationSensor,
            "is_multi_channel": False,
            "post": None,
        }
    ],
    "TILT_VIBRATION_SENSOR_CHANNEL": [
        {
            "type": HomematicipTiltVibrationSensor,
            "is_multi_channel": False,
            "post": None,
        }
    ],
    "MULTI_MODE_INPUT_CHANNEL": [
        {
            "type": HomematicipMultiContactInterface,
            "is_multi_channel": True,
            "post": None,
        }
    ],
    "SHUTTER_CONTACT_CHANNEL": [
        {
            "type": HomematicipShutterContact,
            "is_multi_channel": False,
            "post": None,
        }
    ],
    "ROTARY_HANDLE_CHANNEL": [
        {
            "type": HomematicipShutterContectRotaryHandle,
            "is_multi_channel": False,
            "post": None,
        }
    ],
    "MOTION_DETECTION_CHANNEL": [
        {
            "type": HomematicipMotionDetector,
            "is_multi_channel": False,
            "post": None,
        }
    ],
    "MAINS_FAILURE_CHANNEL": [
        {
            "type": HomematicipPluggableMainsFailureSurveillanceSensor,
            "is_multi_channel": False,
            "post": None,
        }
    ],
    "PRESENCE_DETECTION_CHANNEL": [
        {
            "type": HomematicipPresenceDetector,
            "is_multi_channel": False,
            "post": None,
        }
    ],
    "SMOKE_DETECTOR_CHANNEL": [
        {
            "type": HomematicipSmokeDetector,
            "is_multi_channel": False,
            "post": None,
        }
    ],
    "WATER_SENSOR_CHANNEL": [
        {
            "type": HomematicipWaterDetector,
            "is_multi_channel": False,
            "post": None,
        }
    ],
    "WEATHER_SENSOR_CHANNEL": [
        {
            "type": HomematicipStormSensor,
            "is_multi_channel": False,
            "post": "Storm",
        },
        {
            "type": HomematicipSunshineSensor,
            "is_multi_channel": False,
            "post": "Sunshine",
        },
        {
            "type": HomematicipRainSensor,
            "is_multi_channel": False,
            "post": "Raining",
        },
    ],
    "WEATHER_SENSOR_PLUS_CHANNEL": [
        {
            "type": HomematicipStormSensor,
            "is_multi_channel": False,
            "post": "Storm",
        },
        {
            "type": HomematicipSunshineSensor,
            "is_multi_channel": False,
            "post": "Sunshine",
        },
        {
            "type": HomematicipRainSensor,
            "is_multi_channel": False,
            "post": "Raining",
        },
    ],
    "WEATHER_SENSOR_PRO_CHANNEL": [
        {
            "type": HomematicipStormSensor,
            "is_multi_channel": False,
            "post": "Storm",
        },
        {
            "type": HomematicipSunshineSensor,
            "is_multi_channel": False,
            "post": "Sunshine",
        },
        {
            "type": HomematicipRainSensor,
            "is_multi_channel": False,
            "post": "Raining",
        },
    ],
}
