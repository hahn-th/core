"""Access point for the HomematicIP Cloud component."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from typing import Any

from homematicip.auth import Auth
from homematicip.configuration.config import Config
from homematicip.connection.rest_connection import ConnectionContext
from homematicip.events.event_types import ModelUpdateEvent
from homematicip.exceptions.connection_exceptions import HmipConnectionError
from homematicip.model.hmip_base import HmipBaseModel
from homematicip.model.model import Model
from homematicip.model.model_components import Device
from homematicip.runner import AbstractRunner, Runner

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .const import HMIPC_AUTHTOKEN, HMIPC_HAPID, HMIPC_NAME, HMIPC_PIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


class HomematicipAuth:
    """Manages HomematicIP client registration."""

    auth: Auth

    def __init__(self, hass: HomeAssistant, config: dict[str, str]) -> None:
        """Initialize HomematicIP Cloud client registration."""
        self.hass = hass
        self.config = config

    async def async_setup(self) -> bool:
        """Connect to HomematicIP for registration."""
        try:
            self.auth = await self.get_auth(
                self.hass, self.config.get(HMIPC_HAPID), self.config.get(HMIPC_PIN)
            )
        except HmipConnectionError:
            return False
        return self.auth is not None

    async def async_checkbutton(self) -> bool:
        """Check blue butten has been pressed."""
        try:
            return await self.auth.is_request_acknowledged()
        except HmipConnectionError:
            return False

    async def async_register(self):
        """Register client at HomematicIP."""
        try:
            authtoken = await self.auth.request_auth_token()
            await self.auth.confirm_auth_token(authtoken)
        except HmipConnectionError:
            return False
        return authtoken

    async def get_auth(self, hass: HomeAssistant, hapid, pin):
        """Create a HomematicIP access point object."""
        ctx = ConnectionContext(accesspoint_id=hapid, auth_token=None)
        auth = Auth(ctx)  # hass.loop is not needed here
        try:
            await auth.connection_request("HomeAssistant", pin=pin)
        except HmipConnectionError:
            return None
        return auth


class HomematicipHAP:
    """Manages HomematicIP HTTP and WebSocket connection."""

    runner: AbstractRunner = None
    _listening_task: asyncio.Task | None = None

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize HomematicIP Cloud connection."""
        self.hass = hass
        self.config_entry = config_entry

        self._ws_close_requested = False
        self._retry_task: asyncio.Task | None = None
        self._tries = 0
        self._accesspoint_connected = True
        self.hmip_device_by_entity_id: dict[str, Any] = {}
        self.reset_connection_listener: Callable | None = None

    async def async_setup(self, tries: int = 0) -> bool:
        """Initialize connection."""
        try:
            self.runner = await self.get_runner(
                self.hass,
                self.config_entry.data.get(HMIPC_HAPID),
                self.config_entry.data.get(HMIPC_AUTHTOKEN),
                self.config_entry.data.get(HMIPC_NAME),
            )
            self._listening_task = self.hass.loop.create_task(
                self.runner.async_listening_for_updates()
            )

        except HmipConnectionError as err:
            raise ConfigEntryNotReady from err
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Error connecting with HomematicIP Cloud: %s", err)
            return False

        _LOGGER.info(
            "Connected to HomematicIP with HAP %s", self.config_entry.unique_id
        )

        await self.hass.config_entries.async_forward_entry_setups(
            self.config_entry, PLATFORMS
        )

        return True

    @callback
    def async_update(self, *args, **kwargs) -> None:
        """Async update the home device.

        Triggered when the HMIP HOME_CHANGED event has fired.
        There are several occasions for this event to happen.
        1. We are interested to check whether the access point
        is still connected. If not, entity state changes cannot
        be forwarded to hass. So if access point is disconnected all devices
        are set to unavailable.
        2. We need to update home including devices and groups after a reconnect.
        3. We need to update home without devices and groups in all other cases.

        """
        if not self.runner.websocket_connected:
            _LOGGER.error("HMIP access point has lost connection with the cloud")
            self._accesspoint_connected = False
            self.set_all_to_unavailable()
        elif not self._accesspoint_connected:
            # Now the HOME_CHANGED event has fired indicating the access
            # point has reconnected to the cloud again.
            # Explicitly getting an update as entity states might have
            # changed during access point disconnect."""

            job = self.hass.async_create_task(self.get_state())
            job.add_done_callback(self.get_state_finished)
            self._accesspoint_connected = True

    @property
    def model(self) -> Model:
        """Return the model of the access point."""
        return self.runner.model

    @callback
    def async_create_entity(
        self, event_type: ModelUpdateEvent, hmip_base: HmipBaseModel
    ) -> None:
        """Create an entity or a group."""
        is_device = isinstance(hmip_base, Device)
        self.hass.async_create_task(self.async_create_entity_lazy(is_device))

    async def async_create_entity_lazy(self, is_device=True) -> None:
        """Delay entity creation to allow the user to enter a device name."""
        if is_device:
            await asyncio.sleep(30)
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)

    async def get_state(self) -> None:
        """Update HMIP state and tell Home Assistant."""
        await self.runner.async_get_current_state()
        self.update_all()

    def get_state_finished(self, future) -> None:
        """Execute when get_state coroutine has finished."""
        try:
            future.result()
        except HmipConnectionError:
            # Somehow connection could not recover. Will disconnect and
            # so reconnect loop is taking over.
            _LOGGER.error("Updating state after HMIP access point reconnect failed")
            if self._listening_task is not None:
                self._listening_task.cancel()
                self._listening_task = None

    def set_all_to_unavailable(self) -> None:
        """Set all devices to unavailable and tell Home Assistant."""
        for device in self.runner.model.devices:
            device.unreach = True
        self.update_all()

    def update_all(self) -> None:
        """Signal all devices to update their state."""
        for device in self.runner.model.devices:
            device.fire_on_update()

    async def async_connect(self) -> None:
        """Start WebSocket connection."""
        tries = 0
        while True:
            retry_delay = 2 ** min(tries, 8)

            try:
                await self.runner.async_get_current_state()

                self._listening_task = self.hass.loop.create_task(
                    self.runner.async_listening_for_updates()
                )
                tries = 0
            except HmipConnectionError:
                _LOGGER.error(
                    (
                        "Error connecting to HomematicIP with HAP %s. "
                        "Retrying in %d seconds"
                    ),
                    self.config_entry.unique_id,
                    retry_delay,
                )

            if self._ws_close_requested:
                break
            self._ws_close_requested = False
            tries += 1

            try:
                self._retry_task = self.hass.async_create_task(
                    asyncio.sleep(retry_delay)
                )
                await self._retry_task
            except asyncio.CancelledError:
                break

    async def async_reset(self) -> bool:
        """Close the websocket connection."""
        self._ws_close_requested = True
        if self._retry_task is not None:
            self._retry_task.cancel()

        if self._listening_task is not None:
            self._listening_task.cancel()
            self._listening_task = None
        _LOGGER.info("Closed connection to HomematicIP cloud server")
        await self.hass.config_entries.async_unload_platforms(
            self.config_entry, PLATFORMS
        )
        self.hmip_device_by_entity_id = {}
        return True

    @callback
    def shutdown(self, event) -> None:
        """Wrap the call to async_reset.

        Used as an argument to EventBus.async_listen_once.
        """
        self.hass.async_create_task(self.async_reset())
        _LOGGER.debug(
            "Reset connection to access point id %s", self.config_entry.unique_id
        )

    async def get_runner(
        self, hass: HomeAssistant, hapid, authtoken, name
    ) -> AbstractRunner:
        """Initialize a runner for the HomematicIP Cloud."""
        cfg = Config(
            accesspoint_id=hapid,
            auth_token=authtoken,
        )

        runner = Runner(external_loop=self.hass.loop, config=cfg)
        runner.event_manager.subscribe(ModelUpdateEvent.ITEM_UPDATED, self.async_update)
        runner.event_manager.subscribe(
            ModelUpdateEvent.ITEM_REMOVED, self.async_create_entity
        )
        await runner.async_initialize_runner()

        # Use the title of the config entry as title for the home.
        runner.name = name
        runner.label = self.config_entry.title
        runner.model.home.modelType = "HomematicIP Cloud Home"

        return runner

    # async def get_hap(
    #     self,
    #     hass: HomeAssistant,
    #     hapid: str | None,
    #     authtoken: str | None,
    #     name: str | None,
    # ) -> AsyncHome:
    #     """Create a HomematicIP access point object."""
    #     home = AsyncHome(hass.loop, async_get_clientsession(hass))

    #     home.name = name
    #     # Use the title of the config entry as title for the home.
    #     home.label = self.config_entry.title
    #     home.modelType = "HomematicIP Cloud Home"

    #     home.set_auth_token(authtoken)
    #     try:
    #         await home.init(hapid)
    #         await home.get_current_state()
    #     except HmipConnectionError as err:
    #         raise HmipcConnectionError from err
    #     home.on_update(self.async_update)
    #     home.on_create(self.async_create_entity)
    #     hass.loop.create_task(self.async_connect())

    #     return home
