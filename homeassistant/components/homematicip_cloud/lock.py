"""Support for HomematicIP Cloud lock devices."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from homematicip.action.functional_channel_actions import action_set_door_state
from homematicip.model.enums import LockState, MotorState

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN as HMIPC_DOMAIN, HomematicipGenericEntity
from .helpers import handle_errors

_LOGGER = logging.getLogger(__name__)

ATTR_AUTO_RELOCK_DELAY = "auto_relock_delay"
ATTR_DOOR_HANDLE_TYPE = "door_handle_type"
ATTR_DOOR_LOCK_DIRECTION = "door_lock_direction"
ATTR_DOOR_LOCK_NEUTRAL_POSITION = "door_lock_neutral_position"
ATTR_DOOR_LOCK_TURNS = "door_lock_turns"

DEVICE_DLD_ATTRIBUTES = {
    "autoRelockDelay": ATTR_AUTO_RELOCK_DELAY,
    "doorHandleType": ATTR_DOOR_HANDLE_TYPE,
    "doorLockDirection": ATTR_DOOR_LOCK_DIRECTION,
    "doorLockNeutralPosition": ATTR_DOOR_LOCK_NEUTRAL_POSITION,
    "doorLockTurns": ATTR_DOOR_LOCK_TURNS,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomematicIP locks from a config entry."""
    hap = hass.data[HMIPC_DOMAIN][config_entry.unique_id]

    entities = []
    for device in hap.model.devices.values():
        if device.functionalChannels:
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

    if len(entities) > 0:
        async_add_entities(entities)


class HomematicipDoorLockDrive(HomematicipGenericEntity, LockEntity):
    """Representation of the HomematicIP DoorLockDrive."""

    _attr_supported_features = LockEntityFeature.OPEN

    @property
    def is_locked(self) -> bool | None:
        """Return true if device is locked."""
        return (
            self.functional_channel.lockState == LockState.LOCKED
            and self.functional_channel.motorState == MotorState.STOPPED
        )

    @property
    def is_locking(self) -> bool:
        """Return true if device is locking."""
        return self.functional_channel.motorState == MotorState.CLOSING

    @property
    def is_unlocking(self) -> bool:
        """Return true if device is unlocking."""
        return self.functional_channel.motorState == MotorState.OPENING

    @handle_errors
    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the device."""
        return await action_set_door_state(
            self._hap.runner.rest_connection, self.functional_channel, LockState.LOCKED
        )

    @handle_errors
    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the device."""
        return await action_set_door_state(
            self._hap.runner.rest_connection,
            self.functional_channel,
            LockState.UNLOCKED,
        )

    @handle_errors
    async def async_open(self, **kwargs: Any) -> None:
        """Open the door latch."""
        return await action_set_door_state(
            self._hap.runner.rest_connection, self.functional_channel, LockState.OPEN
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the device."""
        return super().extra_state_attributes | {
            attr_key: attr_value
            for attr, attr_key in DEVICE_DLD_ATTRIBUTES.items()
            if (attr_value := getattr(self.functional_channel, attr, None)) is not None
        }


class TypedMappingDict(TypedDict):
    """TypedDict for mapping functional channel types to their classes."""

    type: type
    is_multi_channel: bool
    post: str | None


MapFunctionalChannelDevice: dict[str, list[TypedMappingDict]] = {
    "DOOR_LOCK_CHANNEL": [
        {
            "type": HomematicipDoorLockDrive,
            "is_multi_channel": False,
            "post": None,
        }
    ],
}
