"""Support for HomematicIP Cloud button devices."""

from __future__ import annotations

from typing import TypedDict

from homematicip.action.functional_channel_actions import async_start_impulse_fc

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN as HMIPC_DOMAIN, HomematicipGenericEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomematicIP button from a config entry."""
    hap = hass.data[HMIPC_DOMAIN][config_entry.unique_id]

    devices = []
    for device in hap.model.devices.values():
        if device.functionalChannels:
            for channel in device.functionalChannels.values():
                if channel.functionalChannelType in MapFunctionalChannelDevice:
                    for target_dict in MapFunctionalChannelDevice[
                        channel.functionalChannelType
                    ]:
                        target_type: type = target_dict["type"]
                        devices.append(
                            target_type(
                                hap=hap,
                                device=device,
                                channel_index=channel.index,
                                is_multi_channel=target_dict["is_multi_channel"],
                                post=target_dict["post"],
                            )
                        )

    if len(devices) > 0:
        async_add_entities(devices)


class HomematicipGarageDoorControllerButton(HomematicipGenericEntity, ButtonEntity):
    """Representation of the HomematicIP Wall mounted Garage Door Controller."""

    @property
    def icon(self) -> str | None:
        """Return icon for the entity."""
        return "mdi:arrow-up-down"

    async def async_press(self) -> None:
        """Handle the button press."""
        await async_start_impulse_fc(
            self._hap.runner.rest_connection, self.functional_channel
        )


class TypedMappingDict(TypedDict):
    """TypedDict for mapping functional channel types to their classes."""

    type: type
    is_multi_channel: bool
    post: str | None


MapFunctionalChannelDevice: dict[str, list[TypedMappingDict]] = {
    "IMPULSE_OUTPUT_CHANNEL": [
        {
            "type": HomematicipGarageDoorControllerButton,
            "is_multi_channel": False,
            "post": None,
        }
    ],
}
