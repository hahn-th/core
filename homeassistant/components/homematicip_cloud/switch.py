"""Support for HomematicIP Cloud switches."""

from __future__ import annotations

from typing import Any, TypedDict

from homematicip.action.functional_channel_actions import action_set_switch_state
from homematicip.action.group_actions import group_action_set_switch_state
from homematicip.model.hmip_base import HmipBaseModel
from homematicip.model.model_components import FunctionalChannel

# from homematicip.aio.group import AsyncExtendedLinkedSwitchingGroup, AsyncSwitchingGroup
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN as HMIPC_DOMAIN, HomematicipGenericEntity
from .generic_entity import ATTR_GROUP_MEMBER_UNREACHABLE
from .hap import HomematicipHAP


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomematicIP switch from a config entry."""
    hap = hass.data[HMIPC_DOMAIN][config_entry.unique_id]
    entities: list[HomematicipGenericEntity] = []
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
    # entities: list[HomematicipGenericEntity] = [
    #     HomematicipGroupSwitch(hap, group)
    #     for group in hap.home.groups
    #     if isinstance(group, (AsyncExtendedLinkedSwitchingGroup, AsyncSwitchingGroup))
    # ]
    # for device in hap.home.devices:
    #     if isinstance(device, AsyncBrandSwitchMeasuring):
    #         # BrandSwitchMeasuring inherits PlugableSwitchMeasuring
    #         # This entity is implemented in the light platform and will
    #         # not be added in the switch platform
    #         pass
    #     elif isinstance(
    #         device, (AsyncPlugableSwitchMeasuring, AsyncFullFlushSwitchMeasuring)
    #     ):
    #         entities.append(HomematicipSwitchMeasuring(hap, device))
    #     elif isinstance(device, AsyncWiredSwitch8):
    #         entities.extend(
    #             HomematicipMultiSwitch(hap, device, channel=channel)
    #             for channel in range(1, 9)
    #         )
    #     elif isinstance(device, AsyncDinRailSwitch):
    #         entities.append(HomematicipMultiSwitch(hap, device, channel=1))
    #     elif isinstance(device, AsyncDinRailSwitch4):
    #         entities.extend(
    #             HomematicipMultiSwitch(hap, device, channel=channel)
    #             for channel in range(1, 5)
    #         )
    #     elif isinstance(
    #         device,
    #         (
    #             AsyncPlugableSwitch,
    #             AsyncPrintedCircuitBoardSwitchBattery,
    #             AsyncFullFlushInputSwitch,
    #         ),
    #     ):
    #         entities.append(HomematicipSwitch(hap, device))
    #     elif isinstance(device, AsyncOpenCollector8Module):
    #         entities.extend(
    #             HomematicipMultiSwitch(hap, device, channel=channel)
    #             for channel in range(1, 9)
    #         )
    #     elif isinstance(
    #         device,
    #         (
    #             AsyncBrandSwitch2,
    #             AsyncPrintedCircuitBoardSwitch2,
    #             AsyncHeatingSwitch2,
    #             AsyncMultiIOBox,
    #         ),
    #     ):
    #         entities.extend(
    #             HomematicipMultiSwitch(hap, device, channel=channel)
    #             for channel in range(1, 3)
    #         )

    async_add_entities(entities)


class HomematicipSwitch(HomematicipGenericEntity, SwitchEntity):
    """Representation of the HomematicIP switch."""

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
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.functional_channel.on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await action_set_switch_state(
            self._hap.runner.rest_connection, self.functional_channel, True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await action_set_switch_state(
            self._hap.runner.rest_connection, self.functional_channel, False
        )


class HomematicipGroupSwitch(HomematicipGenericEntity, SwitchEntity):
    """Representation of the HomematicIP switching group."""

    def __init__(self, hap: HomematicipHAP, device, post: str = "Group") -> None:
        """Initialize switching group."""
        device.modelType = f"HmIP-{post}"
        super().__init__(hap, device, post)

    @property
    def is_on(self) -> bool:
        """Return true if group is on."""
        return self._device.on

    @property
    def available(self) -> bool:
        """Switch-Group available."""
        # A switch-group must be available, and should not be affected by the
        # individual availability of group members.
        # This allows switching even when individual group members
        # are not available.
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the switch-group."""
        state_attr = super().extra_state_attributes

        if self._device.unreach:
            state_attr[ATTR_GROUP_MEMBER_UNREACHABLE] = True

        return state_attr

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the group on."""
        await self._set_switch_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the group off."""
        await self._set_switch_state(False)

    async def _set_switch_state(self, state: bool) -> None:
        """Set the switch state of the group."""
        await group_action_set_switch_state(
            self._hap.runner.rest_connection, self._device, state
        )


class HomematicipSwitchMeasuring(HomematicipSwitch):
    """Representation of the HomematicIP measuring switch."""


# AsyncBrandSwitch2 = SWITCH_CHANNEL
# - set_switch_state
# AsyncBrandSwitchMeasuring = SWITCH_MEASURING_CHANNEL
# - reset_energy_counter
# AsyncDinRailSwitch = MULTI_MODE_INPUT_SWITCH_CHANNEL
# AsyncDinRailSwitch4 = MULTI_MODE_INPUT_SWITCH_CHANNEL
# AsyncFullFlushInputSwitch = MULTI_MODE_INPUT_SWITCH_CHANNEL
# AsyncFullFlushSwitchMeasuring = SWITCH_MEASURING_CHANNEL
# AsyncHeatingSwitch2 = SWITCH_CHANNEL
# AsyncMultiIOBox = SWITCH_CHANNEL
# AsyncOpenCollector8Module = SWITCH_CHANNEL
# AsyncPlugableSwitch = SWITCH_CHANNEL
# AsyncPlugableSwitchMeasuring = SWITCH_MEASURING_CHANNEL
# AsyncPrintedCircuitBoardSwitch2 = SWITCH_CHANNEL
# AsyncPrintedCircuitBoardSwitchBattery = SWITCH_CHANNEL
# AsyncWiredSwitch8 = SWITCH_CHANNEL


class TypedMappingDict(TypedDict):
    """TypedDict for mapping functional channel types to their classes."""

    type: type
    is_multi_channel: bool
    post: str | None


MapGroups: dict[str, list[TypedMappingDict]] = {
    "SWITCHING": [
        {
            "type": HomematicipGroupSwitch,
            "is_multi_channel": False,
            "post": "Group",
        }
    ],
    "EXTENDED_LINKED_SWITCHING": [
        {
            "type": HomematicipGroupSwitch,
            "is_multi_channel": False,
            "post": "Group",
        }
    ],
}


MapFunctionalChannelDevice: dict[str, list[TypedMappingDict]] = {
    "SWITCH_CHANNEL": [
        {
            "type": HomematicipSwitch,
            "is_multi_channel": True,
            "post": None,
        }
    ],
    "SWITCH_MEASURING_CHANNEL": [
        {
            "type": HomematicipSwitch,
            "is_multi_channel": True,
            "post": None,
        }
    ],
    "MULTI_MODE_INPUT_SWITCH_CHANNEL": [
        {
            "type": HomematicipSwitch,
            "is_multi_channel": True,
            "post": None,
        }
    ],
}
