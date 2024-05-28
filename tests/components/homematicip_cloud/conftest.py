"""Initializer helpers for HomematicIP fake server."""

import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from homematicip.auth import Auth
from homematicip.connection.rest_connection import RestConnection

# from homematicip.aio.auth import AsyncAuth
# from homematicip.aio.connection import AsyncConnection
# from homematicip.aio.home import AsyncHome
from homematicip.model.model import Model, build_model_from_json
from homematicip.runner import Runner
import pytest

from homeassistant import config_entries
from homeassistant.components.homematicip_cloud import (
    DOMAIN as HMIPC_DOMAIN,
    async_setup as hmip_async_setup,
)
from homeassistant.components.homematicip_cloud.const import (
    HMIPC_AUTHTOKEN,
    HMIPC_HAPID,
    HMIPC_NAME,
    HMIPC_PIN,
)
from homeassistant.components.homematicip_cloud.hap import HomematicipHAP
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .helper import AUTH_TOKEN, HAPID, HAPPIN, HomeFactory

from tests.common import MockConfigEntry, load_fixture
from tests.components.light.conftest import mock_light_profiles  # noqa: F401


@pytest.fixture(name="fixture_data")
def fixture_data_fixture() -> str:
    """Return a simple fixture data string."""
    return load_fixture("homematicip_cloud.json", "homematicip_cloud")


@pytest.fixture(name="fixture_model")
def fixture_model_fixture(fixture_data) -> Model:
    """Return a simple fixture model."""
    return build_model_from_json(json.loads(fixture_data))


@pytest.fixture(name="mock_connection")
def mock_connection_fixture() -> RestConnection:
    """Return a mocked connection."""
    connection = MagicMock(spec=RestConnection)

    def _rest_call_side_effect(path, body=None):
        return path, body

    connection.async_post.side_effect = _rest_call_side_effect
    # connection.api_call = AsyncMock(return_value=True)
    # connection.init = AsyncMock(side_effect=True)

    return connection


@pytest.fixture(name="hmip_config_entry")
def hmip_config_entry_fixture() -> config_entries.ConfigEntry:
    """Create a mock config entry for homematic ip cloud."""
    entry_data = {
        HMIPC_HAPID: HAPID,
        HMIPC_AUTHTOKEN: AUTH_TOKEN,
        HMIPC_NAME: "",
        HMIPC_PIN: HAPPIN,
    }
    return MockConfigEntry(
        version=1,
        domain=HMIPC_DOMAIN,
        title="Home Test SN",
        unique_id=HAPID,
        data=entry_data,
        source=SOURCE_IMPORT,
    )


@pytest.fixture(name="default_mock_hap_factory")
async def default_mock_hap_factory_fixture(
    hass: HomeAssistant, mock_connection, hmip_config_entry
) -> HomematicipHAP:
    """Create a mocked homematic access point."""
    return HomeFactory(hass, mock_connection, hmip_config_entry)


@pytest.fixture(name="hmip_config")
def hmip_config_fixture() -> ConfigType:
    """Create a config for homematic ip cloud."""

    entry_data = {
        HMIPC_HAPID: HAPID,
        HMIPC_AUTHTOKEN: AUTH_TOKEN,
        HMIPC_NAME: "",
        HMIPC_PIN: HAPPIN,
    }

    return {HMIPC_DOMAIN: [entry_data]}


@pytest.fixture(name="dummy_config")
def dummy_config_fixture() -> ConfigType:
    """Create a dummy config."""
    return {"blabla": None}


@pytest.fixture(name="mock_hap_with_service")
async def mock_hap_with_service_fixture(
    hass: HomeAssistant, default_mock_hap_factory, dummy_config
) -> HomematicipHAP:
    """Create a fake homematic access point with hass services."""
    mock_hap = await default_mock_hap_factory.async_get_mock_hap()
    await hmip_async_setup(hass, dummy_config)
    await hass.async_block_till_done()
    hass.data[HMIPC_DOMAIN] = {HAPID: mock_hap}
    return mock_hap


@pytest.fixture(name="simple_mock_home")
def simple_mock_home_fixture(fixture_model):
    """Return a simple mocked connection."""

    fixture_model.devices = {}
    fixture_model.groups = {}

    mock_home = Mock(spec=Runner, name="Demo", model=fixture_model)

    with patch(
        "homeassistant.components.homematicip_cloud.hap.Runner",
        autospec=True,
        return_value=mock_home,
    ):
        yield


@pytest.fixture(name="mock_connection_init")
def mock_connection_init_fixture():
    """Return a simple mocked connection."""

    with (
        patch(
            "homeassistant.components.homematicip_cloud.hap.Runner.async_initialize_runner",
            return_value=None,
        ),
        patch(
            "homematicip.auth.RestConnection",
            return_value=None,
        ),
    ):
        yield


@pytest.fixture(name="simple_mock_auth")
def simple_mock_auth_fixture() -> Auth:
    """Return a simple AsyncAuth Mock."""
    return AsyncMock(spec=Auth, pin=HAPPIN, create=True)
