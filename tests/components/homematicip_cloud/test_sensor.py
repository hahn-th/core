"""Tests for HomematicIP Cloud sensor."""

from homematicip.model.enums import ValveState

from homeassistant.components.homematicip_cloud import DOMAIN as HMIPC_DOMAIN
from homeassistant.components.homematicip_cloud.generic_entity import (
    ATTR_RSSI_DEVICE,
    ATTR_RSSI_PEER,
)
from homeassistant.components.homematicip_cloud.sensor import (
    ATTR_LEFT_COUNTER,
    ATTR_RIGHT_COUNTER,
    ATTR_TEMPERATURE_OFFSET,
)
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    DEGREE,
    LIGHT_LUX,
    PERCENTAGE,
    STATE_UNKNOWN,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .helper import async_manipulate_test_data, get_and_check_entity_basics


async def test_manually_configured_platform(hass: HomeAssistant) -> None:
    """Test that we do not set up an access point."""
    assert await async_setup_component(
        hass, SENSOR_DOMAIN, {SENSOR_DOMAIN: {"platform": HMIPC_DOMAIN}}
    )
    assert not hass.data.get(HMIPC_DOMAIN)


async def test_hmip_accesspoint_status(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipSwitch."""
    entity_id = "sensor.home_control_access_point_duty_cycle"
    entity_name = "HOME_CONTROL_ACCESS_POINT Duty Cycle"
    device_model = "HmIP-HAP"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711A000000BAD0C0DED"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )
    assert hmip_device
    assert ha_state.state == "8.0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE


async def test_hmip_heating_thermostat(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipHeatingThermostat."""
    entity_id = "sensor.heizkorperthermostat_heating"
    entity_name = "Heizkörperthermostat Heating"
    device_model = "HMIP-eTRV"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000012"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    await async_manipulate_test_data(hass, hmip_device, "valvePosition", 0.37, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "37"

    await async_manipulate_test_data(hass, hmip_device, "valveState", "nn", 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_UNKNOWN

    await async_manipulate_test_data(
        hass, hmip_device, "valveState", ValveState.ADAPTION_DONE.value
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "37"

    await async_manipulate_test_data(hass, hmip_device, "lowBat", True, 0)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes["icon"] == "mdi:battery-outline"


async def test_hmip_humidity_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipHumiditySensor."""
    entity_id = "sensor.bwth_1_humidity"
    entity_name = "BWTH 1 Humidity"
    device_model = "HmIP-BWTH"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000055"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "40"
    assert ha_state.attributes["unit_of_measurement"] == PERCENTAGE
    await async_manipulate_test_data(hass, hmip_device, "humidity", 45)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "45"
    # test common attributes
    assert ha_state.attributes[ATTR_RSSI_DEVICE] == -76
    assert ha_state.attributes[ATTR_RSSI_PEER] == -77


async def test_hmip_temperature_sensor1(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipTemperatureSensor."""
    entity_id = "sensor.bwth_1_temperature"
    entity_name = "BWTH 1 Temperature"
    device_model = "HmIP-BWTH"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000055"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "21.0"
    assert ha_state.attributes["unit_of_measurement"] == UnitOfTemperature.CELSIUS
    await async_manipulate_test_data(hass, hmip_device, "actualTemperature", 23.5, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"

    assert not ha_state.attributes.get("temperature_offset")
    await async_manipulate_test_data(hass, hmip_device, "temperatureOffset", 10, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_TEMPERATURE_OFFSET] == 10


async def test_hmip_temperature_sensor2(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipTemperatureSensor."""
    entity_id = "sensor.heizkorperthermostat_temperature"
    entity_name = "Heizkörperthermostat Temperature"
    device_model = "HMIP-eTRV"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000012"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "20.0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    await async_manipulate_test_data(
        hass, hmip_device, "valveActualTemperature", 23.5, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"

    assert not ha_state.attributes.get(ATTR_TEMPERATURE_OFFSET)
    await async_manipulate_test_data(hass, hmip_device, "temperatureOffset", 10, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_TEMPERATURE_OFFSET] == 10


async def test_hmip_temperature_sensor3(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipTemperatureSensor."""
    entity_id = "sensor.raumbediengerat_analog_temperature"
    entity_name = "Raumbediengerät Analog Temperature"
    device_model = "ALPHA-IP-RBGa"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711000000BBBB000005"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "23.3"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    await async_manipulate_test_data(hass, hmip_device, "actualTemperature", 23.5, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"

    assert not ha_state.attributes.get(ATTR_TEMPERATURE_OFFSET)
    await async_manipulate_test_data(hass, hmip_device, "temperatureOffset", 10)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_TEMPERATURE_OFFSET] == 10


async def test_hmip_thermostat_evo_heating(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipHeatingThermostat for HmIP-eTRV-E."""
    entity_id = "sensor.thermostat_evo_heating"
    entity_name = "thermostat_evo Heating"
    device_model = "HmIP-eTRV-E"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000E70"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "33"
    await async_manipulate_test_data(hass, hmip_device, "valvePosition", 0.4, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert ha_state.state == "40"


async def test_hmip_thermostat_evo_temperature(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipTemperatureSensor."""
    entity_id = "sensor.thermostat_evo_temperature"
    entity_name = "thermostat_evo Temperature"
    device_model = "HmIP-eTRV-E"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000E70"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "18.7"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    await async_manipulate_test_data(
        hass, hmip_device, "valveActualTemperature", 23.5, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"

    await async_manipulate_test_data(hass, hmip_device, "temperatureOffset", 0.7, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_TEMPERATURE_OFFSET] == 0.7


async def test_hmip_power_sensor(hass: HomeAssistant, default_mock_hap_factory) -> None:
    """Test HomematicipPowerSensor."""
    entity_id = "sensor.flur_oben_power"
    entity_name = "Flur oben Power"
    device_model = "HmIP-BSM"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000108"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "0.0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfPower.WATT
    await async_manipulate_test_data(
        hass, hmip_device, "currentPowerConsumption", 23.5, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"


async def test_hmip_energy_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipPowerSensor."""
    entity_id = "sensor.flur_oben_energy_counter"
    entity_name = "Flur oben Energy Counter"
    device_model = "HmIP-BSM"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000108"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "6.333200000000001"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfEnergy.KILO_WATT_HOUR
    await async_manipulate_test_data(hass, hmip_device, "energyCounter", 23.5, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"


async def test_hmip_illuminance_sensor1(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipIlluminanceSensor."""
    entity_id = "sensor.wettersensor_illuminance"
    entity_name = "Wettersensor Illuminance"
    device_model = "HmIP-SWO-B"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711AAAA000000000003"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "4890.0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == LIGHT_LUX
    await async_manipulate_test_data(hass, hmip_device, "illumination", 231, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "231"


async def test_hmip_current_illumination_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test Homematicip Current Illumination Sensor."""
    entity_id = "sensor.lichtsensor_nord_current_illumination"
    entity_name = "Lichtsensor Nord Current Illumination"
    device_model = "HmIP-SLO"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711SLO0000000000026"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "785.2"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == LIGHT_LUX


async def test_hmip_highest_illumination_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test Homematicip Highest Illumination Sensor."""
    entity_id = "sensor.lichtsensor_nord_highest_illumination"
    entity_name = "Lichtsensor Nord Highest Illumination"
    device_model = "HmIP-SLO"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711SLO0000000000026"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )
    assert ha_state.state == "837.1"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == LIGHT_LUX


async def test_hmip_lowest_illumination_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test Homematicip Lowest Illumination Sensor."""
    entity_id = "sensor.lichtsensor_nord_lowest_illumination"
    entity_name = "Lichtsensor Nord Lowest Illumination"
    device_model = "HmIP-SLO"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711SLO0000000000026"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )
    assert ha_state.state == "785.2"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == LIGHT_LUX


async def test_hmip_average_illumination_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test Homematicip Average Illumination Sensor."""
    entity_id = "sensor.lichtsensor_nord_average_illumination"
    entity_name = "Lichtsensor Nord Average Illumination"
    device_model = "HmIP-SLO"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711SLO0000000000026"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )
    assert ha_state.state == "807.3"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == LIGHT_LUX


async def test_hmip_windspeed_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipWindspeedSensor."""
    entity_id = "sensor.wettersensor_pro_windspeed"
    entity_name = "Wettersensor - pro Windspeed"
    device_model = "HmIP-SWO-PR"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711AAAA000000000001"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "2.6"
    assert (
        ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfSpeed.KILOMETERS_PER_HOUR
    )
    await async_manipulate_test_data(hass, hmip_device, "windSpeed", 9.4, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "9.4"


async def test_hmip_winddirection_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipWindDirectionSensor."""
    entity_id = "sensor.wettersensor_pro_wind_direction"
    entity_name = "Wettersensor - pro Wind Direction"
    device_model = "HmIP-SWO-PR"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711AAAA000000000001"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )
    assert ha_state.state == "295.0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == DEGREE


async def test_hmip_winddirectionvariation_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipWindDirectionVariationSensor."""
    entity_id = "sensor.wettersensor_pro_wind_direction_variation"
    entity_name = "Wettersensor - pro Wind Direction Variation"
    device_model = "HmIP-SWO-PR"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711AAAA000000000001"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )
    assert ha_state.state == "56.25"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == DEGREE


async def test_hmip_today_rain_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipTodayRainSensor."""
    entity_id = "sensor.weather_sensor_plus_today_rain"
    entity_name = "Weather Sensor – plus Today Rain"
    device_model = "HmIP-SWO-PL"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000038"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "3.9"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfLength.MILLIMETERS
    await async_manipulate_test_data(hass, hmip_device, "todayRainCounter", 14.2, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "14.2"


async def test_hmip_temperature_external_sensor_channel_1(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipTemperatureDifferenceSensor Channel 1 HmIP-STE2-PCB."""
    entity_id = "sensor.ste2_external_1_temperature"
    entity_name = "STE2 External 1 Temperature"
    device_model = "HmIP-STE2-PCB"

    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000STE2015"]
    )
    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    hmip_device = mock_hap.hmip_device_by_entity_id.get(entity_id)

    await async_manipulate_test_data(
        hass, hmip_device, "temperatureExternalOne", 25.4, 1
    )

    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "25.4"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    await async_manipulate_test_data(
        hass, hmip_device, "temperatureExternalOne", 23.5, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"


async def test_hmip_temperature_external_sensor_channel_2(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipTemperatureDifferenceSensor Channel 2 HmIP-STE2-PCB."""
    entity_id = "sensor.ste2_external_2_temperature"
    entity_name = "STE2 External 2 Temperature"
    device_model = "HmIP-STE2-PCB"

    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000STE2015"]
    )
    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    hmip_device = mock_hap.hmip_device_by_entity_id.get(entity_id)

    await async_manipulate_test_data(
        hass, hmip_device, "temperatureExternalTwo", 22.4, 1
    )

    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "22.4"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    await async_manipulate_test_data(
        hass, hmip_device, "temperatureExternalTwo", 23.4, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.4"


async def test_hmip_temperature_external_sensor_delta(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipTemperatureDifferenceSensor Delta HmIP-STE2-PCB."""
    entity_id = "sensor.ste2_delta_temperature"
    entity_name = "STE2 Delta Temperature"
    device_model = "HmIP-STE2-PCB"

    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000STE2015"]
    )
    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    hmip_device = mock_hap.hmip_device_by_entity_id.get(entity_id)

    await async_manipulate_test_data(
        hass, hmip_device, "temperatureExternalDelta", 0.4, 1
    )

    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "0.4"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    await async_manipulate_test_data(
        hass, hmip_device, "temperatureExternalDelta", -0.5, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "-0.5"


async def test_hmip_passage_detector_delta_counter(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipPassageDetectorDeltaCounter."""
    entity_id = "sensor.spdr_1"
    entity_name = "SPDR_1"
    device_model = "HmIP-SPDR"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000054"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "164"
    assert ha_state.attributes[ATTR_LEFT_COUNTER] == 966
    assert ha_state.attributes[ATTR_RIGHT_COUNTER] == 802
    await async_manipulate_test_data(hass, hmip_device, "leftRightCounterDelta", 190)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "190"


async def test_hmip_esi_iec_current_power_consumption(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test ESI-IEC currentPowerConsumption Sensor."""
    entity_id = "sensor.esi_iec_currentPowerConsumption"
    entity_name = "esi_iec CurrentPowerConsumption"
    device_model = "HmIP-ESI"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000ESIIEC"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "432"


async def test_hmip_esi_iec_energy_counter_usage_high_tariff(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test ESI-IEC ENERGY_COUNTER_USAGE_HIGH_TARIFF."""
    entity_id = "sensor.esi_iec_energy_counter_usage_high_tariff"
    entity_name = "esi_iec ENERGY_COUNTER_USAGE_HIGH_TARIFF"
    device_model = "HmIP-ESI"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000ESIIEC"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "194.0"


async def test_hmip_esi_iec_energy_counter_usage_low_tariff(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test ESI-IEC ENERGY_COUNTER_USAGE_LOW_TARIFF."""
    entity_id = "sensor.esi_iec_energy_counter_usage_low_tariff"
    entity_name = "esi_iec ENERGY_COUNTER_USAGE_LOW_TARIFF"
    device_model = "HmIP-ESI"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000ESIIEC"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "0.0"


async def test_hmip_esi_iec_energy_counter_input_single_tariff(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test ESI-IEC ENERGY_COUNTER_INPUT_SINGLE_TARIFF."""
    entity_id = "sensor.esi_iec_energy_counter_input_single_tariff"
    entity_name = "esi_iec ENERGY_COUNTER_INPUT_SINGLE_TARIFF"
    device_model = "HmIP-ESI"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000ESIIEC"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "3.0"


async def test_hmip_esi_iec_unknown_channel(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test devices are loaded partially."""
    not_existing_entity_id = "sensor.esi_iec2_energy_counter_input_single_tariff"
    existing_entity_id = "sensor.esi_iec2_energy_counter_usage_high_tariff"
    await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711000000000ESIIEC2"]
    )

    not_existing_ha_state = hass.states.get(not_existing_entity_id)
    existing_ha_state = hass.states.get(existing_entity_id)

    assert not_existing_ha_state is None
    assert existing_ha_state.state == "194.0"


async def test_hmip_esi_gas_current_gas_flow(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test ESI-IEC CurrentGasFlow."""
    entity_id = "sensor.esi_gas_currentgasflow"
    entity_name = "esi_gas CurrentGasFlow"
    device_model = "HmIP-ESI"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000ESIGAS"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "1.03"


async def test_hmip_esi_gas_gas_volume(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test ESI-IEC GasVolume."""
    entity_id = "sensor.esi_gas_gasvolume"
    entity_name = "esi_gas GasVolume"
    device_model = "HmIP-ESI"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000ESIGAS"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "1019.26"
