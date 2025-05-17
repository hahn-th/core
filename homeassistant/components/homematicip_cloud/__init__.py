"""Support for HomematicIP Cloud devices."""

import logging
from typing import TypedDict

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_ACCESSPOINT,
    CONF_AUTHTOKEN,
    DOMAIN,
    HMIPC_AUTHTOKEN,
    HMIPC_HAPID,
    HMIPC_NAME,
)
from .hap import HomematicIPConfigEntry, HomematicipHAP
from .services import async_setup_services, async_unload_services

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN, default=[]): vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Optional(CONF_NAME, default=""): vol.Any(cv.string),
                        vol.Required(CONF_ACCESSPOINT): cv.string,
                        vol.Required(CONF_AUTHTOKEN): cv.string,
                    }
                )
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)

_logger = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the HomematicIP Cloud component."""
    accesspoints = config.get(DOMAIN, [])

    for conf in accesspoints:
        if conf[CONF_ACCESSPOINT] not in {
            entry.data[HMIPC_HAPID]
            for entry in hass.config_entries.async_entries(DOMAIN)
        }:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": config_entries.SOURCE_IMPORT},
                    data={
                        HMIPC_HAPID: conf[CONF_ACCESSPOINT],
                        HMIPC_AUTHTOKEN: conf[CONF_AUTHTOKEN],
                        HMIPC_NAME: conf[CONF_NAME],
                    },
                )
            )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: HomematicIPConfigEntry) -> bool:
    """Set up an access point from a config entry."""

    # 0.104 introduced config entry unique id, this makes upgrading possible
    if entry.unique_id is None:
        new_data = dict(entry.data)

        hass.config_entries.async_update_entry(
            entry, unique_id=new_data[HMIPC_HAPID], data=new_data
        )

    hap = HomematicipHAP(hass, entry)

    entry.runtime_data = hap
    if not await hap.async_setup():
        return False

    await async_setup_services(hass)
    _async_remove_obsolete_entities(hass, entry, hap)

    # Register on HA stop event to gracefully shutdown HomematicIP Cloud connection
    hap.reset_connection_listener = hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP, hap.shutdown
    )

    # Register hap as device in registry.
    device_registry = dr.async_get(hass)

    home = hap.home
    hapname = home.label if home.label != entry.unique_id else f"Home-{home.label}"

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, home.id)},
        manufacturer="eQ-3",
        # Add the name from config entry.
        name=hapname,
    )
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: HomematicIPConfigEntry
) -> bool:
    """Unload a config entry."""
    hap = entry.runtime_data
    assert hap.reset_connection_listener is not None
    hap.reset_connection_listener()

    await async_unload_services(hass)

    return await hap.async_reset()


@callback
def _async_remove_obsolete_entities(
    hass: HomeAssistant, entry: HomematicIPConfigEntry, hap: HomematicipHAP
):
    """Remove obsolete entities from entity registry."""

    if hap.home.currentAPVersion < "2.2.12":
        return

    entity_registry = er.async_get(hass)
    er_entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    for er_entry in er_entries:
        if er_entry.unique_id.startswith("HomematicipAccesspointStatus"):
            entity_registry.async_remove(er_entry.entity_id)
            continue

        for hapid in hap.home.accessPointUpdateStates:
            if er_entry.unique_id == f"HomematicipBatterySensor_{hapid}":
                entity_registry.async_remove(er_entry.entity_id)


class MigrationClassConfig(TypedDict, total=False):
    """TypedDict for migration class configuration."""

    post: str
    channel_index: int | None


UNIQUE_ID_MIGRATION_CLASS_MAP: dict[str, MigrationClassConfig] = {
    "HomematicipBatterySensor": {
        "post": "battery",
        "channel_index": 0,
    },
    "HomematicipTiltVibrationSensor": {
        "post": "acceleration",
        "channel_index": 1,
    },
    "HomematicipMultiDimmer": {
        "post": "dimmer",
    },
}


async def async_migrate_entry(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
) -> bool:
    """Migrate the config entry to the latest version."""
    if config_entry.version == 1:
        async_migrate_v1_v2(hass, config_entry)
        hass.config_entries.async_update_entry(config_entry, version=2)

    return True


def async_migrate_v1_v2(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
) -> bool:
    """Migrate from version 1 to version 2."""
    entity_registry = er.async_get(hass)
    registered_entires = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    for entry in registered_entires:
        migrate_entity_unique_id(entry.entity_id, entry.unique_id, entity_registry)

    return True


def migrate_entity_unique_id(
    entity_id: str, old_unique_id: str, entity_registry: er.EntityRegistry
) -> None:
    """Migrate the unique_id of an entity."""
    splitted_old_unique_id = old_unique_id.split("_")

    if splitted_old_unique_id[0] in UNIQUE_ID_MIGRATION_CLASS_MAP:
        migration_class: MigrationClassConfig = UNIQUE_ID_MIGRATION_CLASS_MAP[
            splitted_old_unique_id[0]
        ]

        if len(splitted_old_unique_id) == 2:
            channel = f"Channel{migration_class['channel_index'] if migration_class['channel_index'] is not None else 1}"
        else:
            channel = splitted_old_unique_id[1]

        new_unique_id = (
            f"{splitted_old_unique_id[-1]}_{channel}_{migration_class['post']}"
        )

        entity_registry.async_update_entity(entity_id, new_unique_id=new_unique_id)

        _logger.info(
            "Migrated entity %s from %s to %s",
            entity_id,
            old_unique_id,
            new_unique_id,
        )
    else:
        _logger.warning(
            "Entity %s with unique_id %s not migrated, class not found.",
            entity_id,
            old_unique_id,
        )
