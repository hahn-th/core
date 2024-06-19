"""Support for HomematicIP Cloud sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypedDict

from homematicip.model.enums import ValveState
from homematicip.model.model_components import FunctionalChannel

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPrecipitationDepth,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import DOMAIN as HMIPC_DOMAIN, HomematicipGenericEntity
from .hap import HomematicipHAP

ATTR_CURRENT_ILLUMINATION = "current_illumination"
ATTR_LOWEST_ILLUMINATION = "lowest_illumination"
ATTR_HIGHEST_ILLUMINATION = "highest_illumination"
ATTR_LEFT_COUNTER = "left_counter"
ATTR_RIGHT_COUNTER = "right_counter"
ATTR_TEMPERATURE_OFFSET = "temperature_offset"

ESI_CONNECTED_SENSOR_TYPE_IEC = "ES_IEC"
ESI_CONNECTED_SENSOR_TYPE_GAS = "ES_GAS"
ESI_CONNECTED_SENSOR_TYPE_LED = "ES_LED"

ESI_TYPE_UNKNOWN = "UNKNOWN"
ESI_TYPE_CURRENT_POWER_CONSUMPTION = "CurrentPowerConsumption"
ESI_TYPE_CURRENT_POWER_CONSUMPTION_KEY = "current_power_consumption"
ESI_TYPE_ENERGY_COUNTER_USAGE_HIGH_TARIFF = "ENERGY_COUNTER_USAGE_HIGH_TARIFF"
ESI_TYPE_ENERGY_COUNTER_USAGE_HIGH_TARIFF_KEY = "energy_counter_usage_high_tariff"
ESI_TYPE_ENERGY_COUNTER_USAGE_LOW_TARIFF = "ENERGY_COUNTER_USAGE_LOW_TARIFF"
ESI_TYPE_ENERGY_COUNTER_USAGE_LOW_TARIFF_KEY = "energy_counter_usage_low_tariff"
ESI_TYPE_ENERGY_COUNTER_INPUT_SINGLE_TARIFF = "ENERGY_COUNTER_INPUT_SINGLE_TARIFF"
ESI_TYPE_ENERGY_COUNTER_INPUT_SINGLE_TARIFF_KEY = "energy_counter_input_single_tariff"
ESI_TYPE_CURRENT_GAS_FLOW = "CurrentGasFlow"
ESI_TYPE_CURRENT_GAS_FLOW_KEY = "current_gas_flow"
ESI_TYPE_CURRENT_GAS_VOLUME = "GasVolume"
ESI_TYPE_CURRENT_GAS_VOLUME_KEY = "gas_volume"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomematicIP Cloud sensors from a config entry."""
    hap = hass.data[HMIPC_DOMAIN][config_entry.unique_id]
    entities: list[HomematicipGenericEntity] = []

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
                        )
                        entities.append(entity)

                # Search for devices for channel in MapFunctionalChannelDevice
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

    async_add_entities(entities)


class HomematicipHeatingThermostat(HomematicipGenericEntity, SensorEntity):
    """Representation of the HomematicIP heating thermostat."""

    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def icon(self) -> str | None:
        """Return the icon."""
        if super().icon:
            return super().icon
        if self.functional_channel.valveState != ValveState.ADAPTION_DONE.value:
            return "mdi:alert"
        return "mdi:radiator"

    @property
    def native_value(self) -> int | None:
        """Return the state of the radiator valve."""
        if self.functional_channel.valveState != ValveState.ADAPTION_DONE.value:
            return None
        return round(self.functional_channel.valvePosition * 100)


@dataclass(kw_only=True, frozen=True)
class HmipSensorEntityDescription(SensorEntityDescription):
    """SensorEntityDescription for HmIP Sensors."""

    name: str | None = None
    value_fn: Callable[[FunctionalChannel], StateType]
    extra_state_attributes: dict | None = None
    exists_fn: Callable[[FunctionalChannel], bool] = lambda channel: False


class HmipSensorEntity(HomematicipGenericEntity, SensorEntity):
    """EntityDescription for HmIP-ESI Sensors."""

    entity_description: HmipSensorEntityDescription

    def __init__(
        self,
        hap: HomematicipHAP,
        device: HomematicipGenericEntity,
        channel_index: int,
        entity_description: HmipSensorEntityDescription,
    ) -> None:
        """Initialize Sensor Entity."""
        super().__init__(
            hap=hap,
            device=device,
            channel_index=channel_index,
            post=entity_description.name,
            is_multi_channel=False,
        )
        self.entity_description = entity_description

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        ret_val = self.entity_description.value_fn(self.functional_channel)
        if ret_val is not None:
            return str(ret_val)

        return None

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


SENSORS: tuple[HmipSensorEntityDescription, ...] = (
    HmipSensorEntityDescription(
        key="humidity",
        name="Humidity",
        value_fn=lambda channel: channel.humidity,
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda channel: hasattr(channel, "humidity"),
    ),
    HmipSensorEntityDescription(
        key="temperature",
        name="Temperature",
        value_fn=lambda channel: channel.actualTemperature,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda channel: hasattr(channel, "temperature"),
    ),
    HmipSensorEntityDescription(
        key="temperature",
        name="Temperature",
        value_fn=lambda channel: channel.actualTemperature,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        extra_state_attributes={"temperatureOffset": ATTR_TEMPERATURE_OFFSET},
        exists_fn=lambda channel: hasattr(channel, "actualTemperature"),
    ),
    HmipSensorEntityDescription(
        key="temperature",
        name="Temperature",
        value_fn=lambda channel: channel.valveActualTemperature,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        extra_state_attributes={"temperatureOffset": ATTR_TEMPERATURE_OFFSET},
        exists_fn=lambda channel: hasattr(channel, "valveActualTemperature"),
    ),
    HmipSensorEntityDescription(
        key="windspeed",
        name="Windspeed",
        value_fn=lambda channel: channel.windSpeed,
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        exists_fn=lambda channel: hasattr(channel, "windSpeed"),
    ),
    HmipSensorEntityDescription(
        key="wind_direction",
        name="Wind Direction",
        value_fn=lambda channel: channel.windDirection,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=DEGREE,
        exists_fn=lambda channel: hasattr(channel, "windDirection"),
    ),
    HmipSensorEntityDescription(
        key="wind_direction_variation",
        name="Wind Direction Variation",
        value_fn=lambda channel: channel.windDirectionVariation,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=DEGREE,
        exists_fn=lambda channel: hasattr(channel, "windDirectionVariation"),
    ),
    HmipSensorEntityDescription(
        key="illuminance",
        name="Illuminance",
        value_fn=lambda channel: channel.illumination,
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda channel: hasattr(channel, "illumination"),
    ),
    HmipSensorEntityDescription(
        key="today_rain",
        name="Today Rain",
        value_fn=lambda channel: round(channel.todayRainCounter, 2),
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        exists_fn=lambda channel: hasattr(channel, "todayRainCounter"),
    ),
    HmipSensorEntityDescription(
        key="average_illumination",
        name="Average Illumination",
        value_fn=lambda channel: channel.averageIllumination,
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda channel: hasattr(channel, "averageIllumination"),
    ),
    HmipSensorEntityDescription(
        key="current_illumination",
        name="Current Illumination",
        value_fn=lambda channel: channel.currentIllumination,
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda channel: hasattr(channel, "currentIllumination"),
    ),
    HmipSensorEntityDescription(
        key="highest_illumination",
        name="Highest Illumination",
        value_fn=lambda channel: channel.highestIllumination,
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda channel: hasattr(channel, "highestIllumination"),
    ),
    HmipSensorEntityDescription(
        key="lowest_illumination",
        name="Lowest Illumination",
        value_fn=lambda channel: channel.lowestIllumination,
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda channel: hasattr(channel, "lowestIllumination"),
    ),
    HmipSensorEntityDescription(
        key="duty_cycle",
        name="Duty Cycle",
        value_fn=lambda channel: channel.dutyCycleLevel,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda channel: hasattr(channel, "dutyCycleLevel"),
    ),
    HmipSensorEntityDescription(
        key="left_right_counter_delta",
        name="",
        value_fn=lambda channel: channel.leftRightCounterDelta,
        extra_state_attributes={
            "leftCounter": ATTR_LEFT_COUNTER,
            "rightCounter": ATTR_RIGHT_COUNTER,
        },
        exists_fn=lambda channel: hasattr(channel, "leftRightCounterDelta"),
    ),
    HmipSensorEntityDescription(
        key="ext_1_temperature",
        name="External 1 Temperature",
        value_fn=lambda channel: channel.temperatureExternalOne,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda channel: hasattr(channel, "temperatureExternalOne"),
    ),
    HmipSensorEntityDescription(
        key="ext_2_temperature",
        name="External 2 Temperature",
        value_fn=lambda channel: channel.temperatureExternalTwo,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda channel: hasattr(channel, "temperatureExternalTwo"),
    ),
    HmipSensorEntityDescription(
        key="ext_delta_temperature",
        name="Delta Temperature",
        value_fn=lambda channel: channel.temperatureExternalDelta,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda channel: hasattr(channel, "temperatureExternalDelta"),
    ),
    HmipSensorEntityDescription(
        key="power",
        name="Power",
        value_fn=lambda channel: channel.currentPowerConsumption,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        exists_fn=lambda channel: hasattr(channel, "currentPowerConsumption"),
    ),
    HmipSensorEntityDescription(
        key="energy_counter",
        name="Energy Counter",
        value_fn=lambda channel: channel.energyCounter,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        exists_fn=lambda channel: hasattr(channel, "energyCounter"),
    ),
    # ESI_CONNECTED_SENSOR_TYPE_IEC
    HmipSensorEntityDescription(
        key=ESI_TYPE_CURRENT_POWER_CONSUMPTION_KEY,
        name=ESI_TYPE_CURRENT_POWER_CONSUMPTION,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda channel: channel.currentPowerConsumption,
        exists_fn=lambda channel: getattr(channel, "currentPowerConsumption", None)
        is not None
        and getattr(channel, "connectedEnergySensorType", None)
        == ESI_CONNECTED_SENSOR_TYPE_IEC,
    ),
    HmipSensorEntityDescription(
        key=ESI_TYPE_ENERGY_COUNTER_USAGE_HIGH_TARIFF_KEY,
        name=ESI_TYPE_ENERGY_COUNTER_USAGE_HIGH_TARIFF,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda channel: channel.energyCounterOne,
        exists_fn=lambda channel: getattr(channel, "energyCounterOneType", None)
        != ESI_TYPE_UNKNOWN
        and getattr(channel, "connectedEnergySensorType", None)
        == ESI_CONNECTED_SENSOR_TYPE_IEC,
    ),
    HmipSensorEntityDescription(
        key=ESI_TYPE_ENERGY_COUNTER_USAGE_LOW_TARIFF_KEY,
        name=ESI_TYPE_ENERGY_COUNTER_USAGE_LOW_TARIFF,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda channel: channel.energyCounterTwo,
        exists_fn=lambda channel: getattr(channel, "energyCounterTwoType", None)
        != ESI_TYPE_UNKNOWN
        and getattr(channel, "connectedEnergySensorType", None)
        == ESI_CONNECTED_SENSOR_TYPE_IEC,
    ),
    HmipSensorEntityDescription(
        key=ESI_TYPE_ENERGY_COUNTER_INPUT_SINGLE_TARIFF_KEY,
        name=ESI_TYPE_ENERGY_COUNTER_INPUT_SINGLE_TARIFF,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda channel: channel.energyCounterThree,
        exists_fn=lambda channel: getattr(channel, "energyCounterThreeType", None)
        != ESI_TYPE_UNKNOWN
        and getattr(channel, "connectedEnergySensorType", None)
        == ESI_CONNECTED_SENSOR_TYPE_IEC,
    ),
    # ESI_CONNECTED_SENSOR_TYPE_LED
    HmipSensorEntityDescription(
        key=ESI_TYPE_CURRENT_POWER_CONSUMPTION_KEY,
        name=ESI_TYPE_CURRENT_POWER_CONSUMPTION,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda channel: channel.currentPowerConsumption,
        exists_fn=lambda channel: getattr(channel, "currentPowerConsumption", None)
        is not None
        and getattr(channel, "connectedEnergySensorType", None)
        == ESI_CONNECTED_SENSOR_TYPE_LED,
    ),
    HmipSensorEntityDescription(
        key=ESI_TYPE_ENERGY_COUNTER_USAGE_HIGH_TARIFF_KEY,
        name=ESI_TYPE_ENERGY_COUNTER_USAGE_HIGH_TARIFF,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda channel: channel.energyCounterOne,
        exists_fn=lambda channel: getattr(channel, "energyCounterOne", None) is not None
        and getattr(channel, "connectedEnergySensorType", None)
        == ESI_CONNECTED_SENSOR_TYPE_LED,
    ),
    # ESI_CONNECTED_SENSOR_TYPE_GAS:
    HmipSensorEntityDescription(
        key=ESI_TYPE_CURRENT_GAS_FLOW_KEY,
        name=ESI_TYPE_CURRENT_GAS_FLOW,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda channel: channel.currentGasFlow,
        exists_fn=lambda channel: getattr(channel, "currentGasFlow", None) is not None
        and getattr(channel, "connectedEnergySensorType", None)
        == ESI_CONNECTED_SENSOR_TYPE_GAS,
    ),
    HmipSensorEntityDescription(
        key=ESI_TYPE_CURRENT_GAS_VOLUME_KEY,
        name=ESI_TYPE_CURRENT_GAS_VOLUME,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda channel: channel.gasVolume,
        exists_fn=lambda channel: getattr(channel, "gasVolume", None) is not None
        and getattr(channel, "connectedEnergySensorType", None)
        == ESI_CONNECTED_SENSOR_TYPE_GAS,
    ),
    HmipSensorEntityDescription(
        key="today_sunshine_duration",
        name="Today Sunshine Duration",
        value_fn=lambda channel: channel.todaySunshineDuration,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        exists_fn=lambda channel: hasattr(channel, "todaySunshineDuration"),
    ),
    HmipSensorEntityDescription(
        key="total_sunshine_duration",
        name="Total Sunshine Duration",
        value_fn=lambda channel: channel.totalSunshineDuration,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        exists_fn=lambda channel: hasattr(channel, "totalSunshineDuration"),
    ),
)


class TypedMappingDict(TypedDict):
    """TypedDict for mapping functional channel types to their classes."""

    type: type
    is_multi_channel: bool
    post: str | None


MapFunctionalChannelDevice: dict[str, list[TypedMappingDict]] = {
    "HEATING_THERMOSTAT_CHANNEL": [
        {
            "type": HomematicipHeatingThermostat,
            "is_multi_channel": False,
            "post": "Heating",
        },
    ],
}
