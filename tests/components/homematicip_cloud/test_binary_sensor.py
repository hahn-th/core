"""Tests for HomematicIP Cloud binary sensor."""

from homematicip.model.enums import SmokeDetectorAlarmType, WindowState

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.homematicip_cloud import DOMAIN as HMIPC_DOMAIN
from homeassistant.components.homematicip_cloud.binary_sensor import (
    ATTR_ACCELERATION_SENSOR_MODE,
    ATTR_ACCELERATION_SENSOR_NEUTRAL_POSITION,
    ATTR_ACCELERATION_SENSOR_SENSITIVITY,
    ATTR_ACCELERATION_SENSOR_TRIGGER_ANGLE,
    ATTR_MOISTURE_DETECTED,
    ATTR_MOTION_DETECTED,
    ATTR_POWER_MAINS_FAILURE,
    ATTR_PRESENCE_DETECTED,
    ATTR_WATER_LEVEL_DETECTED,
    ATTR_WINDOW_STATE,
)
from homeassistant.components.homematicip_cloud.generic_entity import (
    ATTR_GROUP_MEMBER_UNREACHABLE,
    ATTR_LOW_BATTERY,
    ATTR_RSSI_DEVICE,
    ATTR_SABOTAGE,
)
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .helper import async_manipulate_test_data, get_and_check_entity_basics


async def test_manually_configured_platform(hass: HomeAssistant) -> None:
    """Test that we do not set up an access point."""
    assert await async_setup_component(
        hass,
        BINARY_SENSOR_DOMAIN,
        {BINARY_SENSOR_DOMAIN: {"platform": HMIPC_DOMAIN}},
    )
    assert not hass.data.get(HMIPC_DOMAIN)


async def test_hmip_home_cloud_connection_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipCloudConnectionSensor."""
    entity_id = "binary_sensor.cloud_connection"
    entity_name = "Cloud Connection"
    device_model = None
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(test_devices=[])

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON

    await async_manipulate_test_data(hass, hmip_device, "connected", False)

    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF


async def test_hmip_acceleration_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipAccelerationSensor."""
    entity_id = "binary_sensor.garagentor_acceleration"
    entity_name = "Garagentor Acceleration"
    device_model = "HmIP-SAM"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000031"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON
    assert ha_state.attributes[ATTR_ACCELERATION_SENSOR_MODE] == "FLAT_DECT"
    assert ha_state.attributes[ATTR_ACCELERATION_SENSOR_NEUTRAL_POSITION] == "VERTICAL"
    assert (
        ha_state.attributes[ATTR_ACCELERATION_SENSOR_SENSITIVITY] == "SENSOR_RANGE_4G"
    )
    assert ha_state.attributes[ATTR_ACCELERATION_SENSOR_TRIGGER_ANGLE] == 45

    await async_manipulate_test_data(
        hass, hmip_device, "accelerationSensorTriggered", False, channel=1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF

    await async_manipulate_test_data(
        hass, hmip_device, "accelerationSensorTriggered", True, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_tilt_vibration_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipTiltVibrationSensor."""
    entity_id = "binary_sensor.garage_neigungs_und_erschutterungssensor_acceleration"
    entity_name = "Garage Neigungs- und Erschütterungssensor Acceleration"
    device_model = "HmIP-STV"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110TILTVIBRATIONSENSOR"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON
    assert ha_state.attributes[ATTR_ACCELERATION_SENSOR_MODE] == "FLAT_DECT"
    assert (
        ha_state.attributes[ATTR_ACCELERATION_SENSOR_SENSITIVITY] == "SENSOR_RANGE_2G"
    )
    assert ha_state.attributes[ATTR_ACCELERATION_SENSOR_TRIGGER_ANGLE] == 45

    await async_manipulate_test_data(
        hass, hmip_device, "accelerationSensorTriggered", False, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF

    await async_manipulate_test_data(
        hass, hmip_device, "accelerationSensorTriggered", True, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_contact_interface(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipContactInterface."""
    entity_id = "binary_sensor.kontakt_schnittstelle_unterputz_1_fach"
    entity_name = "Kontakt-Schnittstelle Unterputz – 1-fach"
    device_model = "HmIP-FCI1"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000029"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(
        hass, hmip_device, "windowState", WindowState.OPEN, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON

    await async_manipulate_test_data(hass, hmip_device, "windowState", None, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_UNKNOWN


async def test_hmip_shutter_contact(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipShutterContact."""
    entity_id = "binary_sensor.fenstergriffsensor"
    entity_name = "Fenstergriffsensor"
    device_model = "HmIP-SRH"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711AAAA000000000004"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON

    await async_manipulate_test_data(
        hass, hmip_device, "windowState", WindowState.OPEN.value, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON

    await async_manipulate_test_data(
        hass, hmip_device, "windowState", WindowState.CLOSED.value, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF

    await async_manipulate_test_data(hass, hmip_device, "windowState", None, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_UNKNOWN

    # test common attributes
    assert ha_state.attributes[ATTR_RSSI_DEVICE] == -54
    assert not ha_state.attributes.get(ATTR_SABOTAGE)
    await async_manipulate_test_data(hass, hmip_device, "sabotage", True, 0)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_SABOTAGE]


async def test_hmip_shutter_contact_optical(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipShutterContact."""
    entity_id = "binary_sensor.sitzplatzture"
    entity_name = "Sitzplatzt\u00fcre"
    device_model = "HmIP-SWDO-PL"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110SHUTTER_OPTICAL"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(
        hass, hmip_device, "windowState", WindowState.OPEN.value, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON

    await async_manipulate_test_data(hass, hmip_device, "windowState", None, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_UNKNOWN

    # test common attributes
    assert ha_state.attributes[ATTR_RSSI_DEVICE] == -72
    assert not ha_state.attributes.get(ATTR_SABOTAGE)
    await async_manipulate_test_data(hass, hmip_device, "sabotage", True, 0)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_SABOTAGE]


async def test_hmip_motion_detector(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipMotionDetector."""
    entity_id = "binary_sensor.bewegungsmelder_fur_55er_rahmen_innen_motion"
    entity_name = "Bewegungsmelder für 55er Rahmen – innen Motion"
    device_model = "HmIP-SMI55"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711000000000AAAAA25"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "motionDetected", True, 3)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_presence_detector(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipPresenceDetector."""
    entity_id = "binary_sensor.spi_1_presence"
    entity_name = "SPI_1 Presence"
    device_model = "HmIP-SPI"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711AAAAAAAAAAAAAA51"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "presenceDetected", True, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_pluggable_mains_failure_surveillance_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipPresenceDetector."""
    entity_id = "binary_sensor.netzausfalluberwachung"
    entity_name = "Netzausfallüberwachung"
    device_model = "HmIP-PMFS"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000ABCD50"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON
    await async_manipulate_test_data(hass, hmip_device, "powerMainsFailure", True, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF


async def test_hmip_smoke_detector(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipSmokeDetector."""
    entity_id = "binary_sensor.rauchwarnmelder_smoke"
    entity_name = "Rauchwarnmelder Smoke"
    device_model = "HmIP-SWSD"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000018"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(
        hass,
        hmip_device,
        "smokeDetectorAlarmType",
        SmokeDetectorAlarmType.PRIMARY_ALARM.value,
        1,
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON
    await async_manipulate_test_data(
        hass, hmip_device, "smokeDetectorAlarmType", None, 1
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF


async def test_hmip_water_detector(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipWaterDetector."""
    entity_id = "binary_sensor.wassersensor_water"
    entity_name = "Wassersensor Water"
    device_model = "HmIP-SWD"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000050"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "waterlevelDetected", True, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_moisture_detector(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipWaterDetector."""
    entity_id = "binary_sensor.wassersensor_moisture"
    entity_name = "Wassersensor Moisture"
    device_model = "HmIP-SWD"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000050"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "moistureDetected", True, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_storm_sensor(hass: HomeAssistant, default_mock_hap_factory) -> None:
    """Test HomematicipStormSensor."""
    entity_id = "binary_sensor.weather_sensor_plus_storm"
    entity_name = "Weather Sensor – plus Storm"
    device_model = "HmIP-SWO-PL"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000038"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "storm", True, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_rain_sensor(hass: HomeAssistant, default_mock_hap_factory) -> None:
    """Test HomematicipRainSensor."""
    entity_id = "binary_sensor.wettersensor_pro_raining"
    entity_name = "Wettersensor - pro Raining"
    device_model = "HmIP-SWO-PR"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711AAAA000000000001"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "raining", True, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_sunshine_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipSunshineSensor."""
    entity_id = "binary_sensor.wettersensor_pro_sunshine"
    entity_name = "Wettersensor - pro Sunshine"
    device_model = "HmIP-SWO-PR"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711AAAA000000000001"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON
    await async_manipulate_test_data(hass, hmip_device, "sunshine", False, 1)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF


async def test_hmip_battery_sensor(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipSunshineSensor."""
    entity_id = "binary_sensor.wohnungsture_battery"
    entity_name = "Wohnungstüre Battery"
    device_model = "HMIP-SWDO"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F7110000000000000006"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "lowBat", True, 0)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_security_zone_sensor_group(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipSecurityZoneSensorGroup."""
    entity_id = "binary_sensor.internal_securityzone"
    entity_name = "INTERNAL SecurityZone"
    device_model = "HmIP-SecurityZone"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_groups=["00000000-0000-0000-0000-000000000016"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    assert not ha_state.attributes.get(ATTR_MOTION_DETECTED)
    assert not ha_state.attributes.get(ATTR_PRESENCE_DETECTED)
    assert not ha_state.attributes.get(ATTR_GROUP_MEMBER_UNREACHABLE)
    assert not ha_state.attributes.get(ATTR_SABOTAGE)
    assert not ha_state.attributes.get(ATTR_WINDOW_STATE)

    await async_manipulate_test_data(hass, hmip_device, "motionDetected", True)
    await async_manipulate_test_data(hass, hmip_device, "presenceDetected", True)
    await async_manipulate_test_data(hass, hmip_device, "unreach", True)
    await async_manipulate_test_data(hass, hmip_device, "sabotage", True)
    await async_manipulate_test_data(
        hass, hmip_device, "windowState", WindowState.OPEN.value
    )
    ha_state = hass.states.get(entity_id)

    assert ha_state.state == STATE_ON
    assert ha_state.attributes[ATTR_MOTION_DETECTED]
    assert ha_state.attributes[ATTR_PRESENCE_DETECTED]
    assert ha_state.attributes[ATTR_GROUP_MEMBER_UNREACHABLE]
    assert ha_state.attributes[ATTR_SABOTAGE]
    assert ha_state.attributes[ATTR_WINDOW_STATE] == WindowState.OPEN.value


async def test_hmip_security_sensor_group(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipSecuritySensorGroup."""
    entity_id = "binary_sensor.buro_sensors"
    entity_name = "Büro Sensors"
    device_model = None
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_groups=["00000000-0000-0000-0000-000000000009"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    await async_manipulate_test_data(
        hass,
        hmip_device,
        "smokeDetectorAlarmType",
        SmokeDetectorAlarmType.PRIMARY_ALARM.value,
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON

    assert (
        ha_state.attributes["smoke_detector_alarm"]
        == SmokeDetectorAlarmType.PRIMARY_ALARM.value
    )
    await async_manipulate_test_data(
        hass,
        hmip_device,
        "smokeDetectorAlarmType",
        SmokeDetectorAlarmType.IDLE_OFF.value,
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF

    assert not ha_state.attributes.get(ATTR_LOW_BATTERY)
    assert not ha_state.attributes.get(ATTR_MOTION_DETECTED)
    assert not ha_state.attributes.get(ATTR_PRESENCE_DETECTED)
    assert not ha_state.attributes.get(ATTR_POWER_MAINS_FAILURE)
    assert not ha_state.attributes.get(ATTR_MOISTURE_DETECTED)
    assert not ha_state.attributes.get(ATTR_WATER_LEVEL_DETECTED)
    assert not ha_state.attributes.get(ATTR_GROUP_MEMBER_UNREACHABLE)
    assert not ha_state.attributes.get(ATTR_SABOTAGE)
    assert not ha_state.attributes.get(ATTR_WINDOW_STATE)

    await async_manipulate_test_data(hass, hmip_device, "lowBat", True)
    await async_manipulate_test_data(hass, hmip_device, "motionDetected", True)
    await async_manipulate_test_data(hass, hmip_device, "presenceDetected", True)
    await async_manipulate_test_data(hass, hmip_device, "powerMainsFailure", True)
    await async_manipulate_test_data(hass, hmip_device, "moistureDetected", True)
    await async_manipulate_test_data(hass, hmip_device, "waterlevelDetected", True)
    await async_manipulate_test_data(hass, hmip_device, "unreach", True)
    await async_manipulate_test_data(hass, hmip_device, "sabotage", True)
    await async_manipulate_test_data(
        hass, hmip_device, "windowState", WindowState.OPEN.value
    )
    ha_state = hass.states.get(entity_id)

    assert ha_state.state == STATE_ON
    assert ha_state.attributes[ATTR_LOW_BATTERY]
    assert ha_state.attributes[ATTR_MOTION_DETECTED]
    assert ha_state.attributes[ATTR_PRESENCE_DETECTED]
    assert ha_state.attributes[ATTR_POWER_MAINS_FAILURE]
    assert ha_state.attributes[ATTR_MOISTURE_DETECTED]
    assert ha_state.attributes[ATTR_WATER_LEVEL_DETECTED]
    assert ha_state.attributes[ATTR_GROUP_MEMBER_UNREACHABLE]
    assert ha_state.attributes[ATTR_SABOTAGE]
    assert ha_state.attributes[ATTR_WINDOW_STATE] == WindowState.OPEN.value

    await async_manipulate_test_data(
        hass,
        hmip_device,
        "smokeDetectorAlarmType",
        SmokeDetectorAlarmType.INTRUSION_ALARM.value,
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_multi_contact_interface(
    hass: HomeAssistant, default_mock_hap_factory
) -> None:
    """Test HomematicipMultiContactInterface."""
    entity_id = "binary_sensor.wired_eingangsmodul_32_fach_channel5"
    entity_name = "Wired Eingangsmodul – 32-fach Channel5"
    device_model = "HmIPW-DRI32"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["3014F711000WIREDINPUT32", "3014F7110000000000056775"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(
        hass, hmip_device, "windowState", WindowState.OPEN.value, channel=5
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON

    await async_manipulate_test_data(hass, hmip_device, "windowState", None, channel=5)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_UNKNOWN

    ha_state, hmip_device = get_and_check_entity_basics(
        hass,
        mock_hap,
        "binary_sensor.licht_flur_5",
        "Licht Flur 5",
        "HmIP-FCI6",
    )

    assert ha_state.state == STATE_UNKNOWN
