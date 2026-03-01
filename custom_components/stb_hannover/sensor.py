import voluptuous as vol
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv

from collections.abc import Callable

from homeassistant.components.asuswrt.device_tracker import add_entities
from homeassistant.components.sensor import (
    ConfigType,
    SensorDeviceClass,
    PLATFORM_SCHEMA,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    CONF_USERNAME,
    CONF_PASSWORD,
)

from .coordinator import StbApi, StbUpdateCoordinator

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.positive_int,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    session = async_get_clientsession(hass)

    username = str(config.get(CONF_USERNAME))
    password = str(config.get(CONF_PASSWORD))

    api = StbApi(
        session,
        username,
        password,
    )

    coordinator = StbUpdateCoordinator(hass, api)

    await coordinator.async_refresh()

    if coordinator.data is None:
        raise PlatformNotReady("Failed to get data from STB Hannover")

    async_add_entities([StbBookSensor(coordinator)])
    async_add_entities([StbNextReturnSensor(coordinator)])


class StbNextReturnSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: StbUpdateCoordinator) -> None:
        super().__init__(coordinator)

        self._attr_name: str = "next_book_return_{coordinator.api._username}"
        self.attrs = {}

    @property
    def device_class(self):
        return SensorDeviceClass.DATE

    @property
    def name(self):
        return "Next return date"

    @property
    def native_value(self):
        earliest_book = None

        for book in self.coordinator.data["books"]:
            if earliest_book == None:
                earliest_book = book
            else:
                if book["return_date"] < earliest_book["return_date"]:
                    earliest_book = book

        return earliest_book["return_date"]


class StbBookSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: StbUpdateCoordinator) -> None:
        super().__init__(coordinator)

        self._available = True

        self._attr_has_entity_name = True
        self._attr_name: str = f"loaned_books_{coordinator.api._username}"
        self._attr_unique_id = "loaned books_1707"
        self.name: str = f"Loaned Books from {coordinator.api._username}"
        self._attr_icon = "mdi:library-books"

    @property
    def available(self) -> bool:
        return self._available

    @property
    def extra_state_attributes(self) -> dict:
        attributes = {}
        attributes["books"] = self.coordinator.data["books"]

        return attributes

    @property
    def native_value(self):
        return len(self.coordinator.data["books"])

    @property
    def unit_of_measurement(self):
        return "books loaned"

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        await self.coordinator.async_request_refresh()
