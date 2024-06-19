"""Support for HomematicIP Cloud lights."""

from __future__ import annotations

from typing import Any, TypedDict

from homematicip.action.functional_channel_actions import (
    async_set_dim_level_fc,
    async_set_optical_signal_fc,
    async_set_rgb_dim_level_with_time_fc,
    async_set_switch_state_fc,
)

# from homematicip.aio.device import (
#     AsyncBrandDimmer,
#     AsyncBrandSwitchMeasuring,
#     AsyncBrandSwitchNotificationLight,
#     AsyncDimmer,
#     AsyncDinRailDimmer3,
#     AsyncFullFlushDimmer,
#     AsyncPluggableDimmer,
#     AsyncWiredDimmer3,
# )
from homematicip.model.enums import OpticalSignalBehaviour, RGBColorState
from homematicip.model.model_components import FunctionalChannel
from packaging.version import Version

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_NAME,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN as HMIPC_DOMAIN, HomematicipGenericEntity
from .hap import HomematicipHAP


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomematicIP Cloud lights from a config entry."""
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
                elif channel.functionalChannelType == "NOTIFICATION_LIGHT_CHANNEL":
                    # Handle NOTIFICATION_LIGHT_CHANNEL separate because depending of
                    # the firmware version the device is a different class.
                    if Version(device.firmwareVersion) > Version("2.0.0"):
                        entities.append(
                            HomematicipNotificationLightV2(
                                hap, device, channel=channel.index
                            )
                        )
                    else:
                        entities.append(
                            HomematicipNotificationLight(
                                hap, device, channel=channel.index
                            )
                        )

    # for device in hap.home.devices:
    #     if isinstance(device, AsyncBrandSwitchMeasuring):
    #         entities.append(HomematicipLightMeasuring(hap, device))
    #     elif isinstance(device, AsyncBrandSwitchNotificationLight):
    #         device_version = Version(device.firmwareVersion)
    #         entities.append(HomematicipLight(hap, device))
    #         if device_version > Version("2.0.0"):
    #             entities.append(
    #                 HomematicipNotificationLightV2(
    #                     hap, device, device.topLightChannelIndex, "Top"
    #                 )
    #             )
    #             entities.append(
    #                 HomematicipNotificationLightV2(
    #                     hap, device, device.bottomLightChannelIndex, "Bottom"
    #                 )
    #             )
    #         else:
    #             entities.append(
    #                 HomematicipNotificationLight(
    #                     hap, device, device.topLightChannelIndex
    #                 )
    #             )
    #             entities.append(
    #                 HomematicipNotificationLight(
    #                     hap, device, device.bottomLightChannelIndex
    #                 )
    #             )
    #     elif isinstance(device, (AsyncWiredDimmer3, AsyncDinRailDimmer3)):
    #         entities.extend(
    #             HomematicipMultiDimmer(hap, device, channel=channel)
    #             for channel in range(1, 4)
    #         )
    #     elif isinstance(
    #         device,
    #         (AsyncDimmer, AsyncPluggableDimmer, AsyncBrandDimmer, AsyncFullFlushDimmer),
    #     ):
    #         entities.append(HomematicipDimmer(hap, device))

    async_add_entities(entities)


class HomematicipLight(HomematicipGenericEntity, LightEntity):
    """Representation of the HomematicIP light."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self.functional_channel.on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await async_set_switch_state_fc(
            rest_connection=self._hap.runner.rest_connection,
            fc=self.functional_channel,
            on=True,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await async_set_switch_state_fc(
            rest_connection=self._hap.runner.rest_connection,
            fc=self.functional_channel,
            on=False,
        )


class HomematicipLightMeasuring(HomematicipLight):
    """Representation of the HomematicIP measuring light."""


class HomematicipMultiDimmer(HomematicipGenericEntity, LightEntity):
    """Representation of HomematicIP Cloud dimmer."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def is_on(self) -> bool:
        """Return true if dimmer is on."""
        return (
            self.functional_channel.dimLevel is not None
            and self.functional_channel.dimLevel > 0.0
        )

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        return int((self.functional_channel.dimLevel or 0.0) * 255)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the dimmer on."""
        dim_level = 1.0
        if ATTR_BRIGHTNESS in kwargs:
            dim_level = kwargs[ATTR_BRIGHTNESS] / 255.0

        await async_set_dim_level_fc(
            rest_connection=self._hap.runner.rest_connection,
            fc=self.functional_channel,
            dim_level=dim_level,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the dimmer off."""
        await async_set_dim_level_fc(
            rest_connection=self._hap.runner.rest_connection,
            fc=self.functional_channel,
            dim_level=0.0,
        )


# class HomematicipDimmer(HomematicipMultiDimmer, LightEntity):
#     """Representation of HomematicIP Cloud dimmer."""

#     def __init__(self, hap: HomematicipHAP, device) -> None:
#         """Initialize the dimmer light entity."""
#         super().__init__(hap, device, is_multi_channel=False)


class HomematicipNotificationLight(HomematicipGenericEntity, LightEntity):
    """Representation of HomematicIP Cloud notification light."""

    _attr_color_mode = ColorMode.HS
    _attr_supported_color_modes = {ColorMode.HS}
    _attr_supported_features = LightEntityFeature.TRANSITION

    def __init__(self, hap: HomematicipHAP, device, channel: int) -> None:
        """Initialize the notification light entity."""
        super().__init__(hap, device, channel_index=channel, is_multi_channel=True)

        self._color_switcher: dict[str, tuple[float, float]] = {
            RGBColorState.WHITE: (0.0, 0.0),
            RGBColorState.RED: (0.0, 100.0),
            RGBColorState.YELLOW: (60.0, 100.0),
            RGBColorState.GREEN: (120.0, 100.0),
            RGBColorState.TURQUOISE: (180.0, 100.0),
            RGBColorState.BLUE: (240.0, 100.0),
            RGBColorState.PURPLE: (300.0, 100.0),
        }

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return (
            self.functional_channel.dimLevel is not None
            and self.functional_channel.dimLevel > 0.0
        )

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        return int((self.functional_channel.dimLevel or 0.0) * 255)

    @property
    def hs_color(self) -> tuple[float, float]:
        """Return the hue and saturation color value [float, float]."""
        simple_rgb_color = self.functional_channel.simpleRGBColorState
        if not isinstance(simple_rgb_color, RGBColorState):
            simple_rgb_color = RGBColorState[simple_rgb_color]
        return self._color_switcher.get(simple_rgb_color, (0.0, 0.0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the notification light sensor."""
        state_attr = super().extra_state_attributes

        if self.is_on:
            state_attr[ATTR_COLOR_NAME] = self.functional_channel.simpleRGBColorState

        return state_attr

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # Use hs_color from kwargs,
        # if not applicable use current hs_color.
        hs_color = kwargs.get(ATTR_HS_COLOR, self.hs_color)
        simple_rgb_color = _convert_color(hs_color)

        # Use brightness from kwargs,
        # if not applicable use current brightness.
        brightness = kwargs.get(ATTR_BRIGHTNESS, self.brightness)

        # If no kwargs, use default value.
        if not kwargs:
            brightness = 255

        # Minimum brightness is 10, otherwise the led is disabled
        brightness = max(10, brightness)
        dim_level = brightness / 255.0
        transition = kwargs.get(ATTR_TRANSITION, 0.5)

        await async_set_rgb_dim_level_with_time_fc(
            rest_connection=self._hap.runner.rest_connection,
            fc=self.functional_channel,
            rgb=simple_rgb_color,
            dim_level=dim_level,
            on_time=0,
            ramp_time=transition,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        simple_rgb_color = self.functional_channel.simpleRGBColorState
        transition = kwargs.get(ATTR_TRANSITION, 0.5)

        await async_set_rgb_dim_level_with_time_fc(
            rest_connection=self._hap.runner.rest_connection,
            fc=self.functional_channel,
            rgb=simple_rgb_color,
            dim_level=0.0,
            on_time=0,
            ramp_time=transition,
        )


class HomematicipNotificationLightV2(HomematicipGenericEntity, LightEntity):
    """Representation of HomematicIP Cloud notification light."""

    _attr_color_mode = ColorMode.HS
    _attr_supported_color_modes = {ColorMode.HS}
    _effect_list = [
        OpticalSignalBehaviour.BILLOW_MIDDLE,
        OpticalSignalBehaviour.BLINKING_MIDDLE,
        OpticalSignalBehaviour.FLASH_MIDDLE,
        OpticalSignalBehaviour.OFF,
        OpticalSignalBehaviour.ON,
    ]

    def __init__(
        self, hap: HomematicipHAP, device, channel: int, post: str = ""
    ) -> None:
        """Initialize the notification light entity."""
        super().__init__(
            hap, device, post=post, channel_index=channel, is_multi_channel=True
        )

        self._attr_supported_features |= LightEntityFeature.EFFECT
        self._color_switcher: dict[str, tuple[float, float]] = {
            RGBColorState.WHITE: (0.0, 0.0),
            RGBColorState.RED: (0.0, 100.0),
            RGBColorState.YELLOW: (60.0, 100.0),
            RGBColorState.GREEN: (120.0, 100.0),
            RGBColorState.TURQUOISE: (180.0, 100.0),
            RGBColorState.BLUE: (240.0, 100.0),
            RGBColorState.PURPLE: (300.0, 100.0),
        }

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        return int((self.functional_channel.dimLevel or 0.0) * 255)

    @property
    def hs_color(self) -> tuple[float, float]:
        """Return the hue and saturation color value [float, float]."""
        simple_rgb_color = self.functional_channel.simpleRGBColorState
        if not isinstance(simple_rgb_color, RGBColorState):
            simple_rgb_color = RGBColorState[simple_rgb_color]
        return self._color_switcher.get(simple_rgb_color, (0.0, 0.0))

    @property
    def effect_list(self) -> list[str] | None:
        """Return the list of supported effects."""
        return self._effect_list

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        return self.functional_channel.opticalSignalBehaviour

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self.functional_channel.on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the notification light sensor."""
        state_attr = super().extra_state_attributes

        if self.is_on:
            state_attr[ATTR_COLOR_NAME] = self.functional_channel.simpleRGBColorState

        return state_attr

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # Use hs_color from kwargs,
        # if not applicable use current hs_color.
        hs_color = kwargs.get(ATTR_HS_COLOR, self.hs_color)
        simple_rgb_color = _convert_color(hs_color)

        # If no kwargs, use default value.
        brightness = 255
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]

        # Minimum brightness is 10, otherwise the led is disabled
        brightness = max(10, brightness)
        dim_level = round(brightness / 255.0, 2)

        effect = self.effect
        if ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]

        await async_set_optical_signal_fc(
            rest_connection=self._hap.runner.rest_connection,
            fc=self.functional_channel,
            optical_signal_behaviour=OpticalSignalBehaviour(effect),
            rgb=simple_rgb_color,
            dim_level=dim_level,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await async_set_optical_signal_fc(
            rest_connection=self._hap.runner.rest_connection,
            fc=self.functional_channel,
            optical_signal_behaviour=OpticalSignalBehaviour.OFF,
            rgb=RGBColorState(self.functional_channel.simpleRGBColorState),
            dim_level=0.0,
        )
        # await self.functional_channel.async_turn_off()


def _convert_color(color: tuple) -> RGBColorState:
    """Convert the given color to the reduced RGBColorState color.

    RGBColorStat contains only 8 colors including white and black,
    so a conversion is required.
    """
    if color is None:
        return RGBColorState.WHITE

    hue = int(color[0])
    saturation = int(color[1])
    if saturation < 5:
        return RGBColorState.WHITE
    if 30 < hue <= 90:
        return RGBColorState.YELLOW
    if 90 < hue <= 160:
        return RGBColorState.GREEN
    if 150 < hue <= 210:
        return RGBColorState.TURQUOISE
    if 210 < hue <= 270:
        return RGBColorState.BLUE
    if 270 < hue <= 330:
        return RGBColorState.PURPLE
    return RGBColorState.RED


class TypedMappingDict(TypedDict):
    """TypedDict for mapping functional channel types to their classes."""

    type: type
    is_multi_channel: bool
    post: str | None


MapFunctionalChannelDevice: dict[str, list[TypedMappingDict]] = {
    "DIMMER_CHANNEL": [
        {
            "type": HomematicipMultiDimmer,
            "is_multi_channel": False,
            "post": None,
        }
    ],
    "MULTI_MODE_INPUT_DIMMER_CHANNEL": [
        {
            "type": HomematicipMultiDimmer,
            "is_multi_channel": True,
            "post": None,
        }
    ],
    "SWITCH_MEASURING_CHANNEL": [
        {
            "type": HomematicipLightMeasuring,
            "is_multi_channel": False,
            "post": None,
        }
    ],
}
