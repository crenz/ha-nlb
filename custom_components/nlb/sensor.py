"""Sensors for the NLB integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import NlbConfigEntry, NlbData
from .entity import NlbEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class NlbSensorDescription(SensorEntityDescription):
    """Describes an NLB sensor."""

    value_fn: Callable[[NlbData], int | None]


SENSORS: tuple[NlbSensorDescription, ...] = (
    NlbSensorDescription(
        key="loans",
        translation_key="loans",
        native_unit_of_measurement="loans",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.loans,
    ),
    NlbSensorDescription(
        key="overdue_loans",
        translation_key="overdue_loans",
        native_unit_of_measurement="loans",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.overdue_loans,
    ),
    NlbSensorDescription(
        key="days_until_next_due",
        translation_key="days_until_next_due",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.days_until_next_due,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NlbConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors of one NLB account."""
    async_add_entities(NlbSensor(entry, description) for description in SENSORS)


class NlbSensor(NlbEntity, SensorEntity):
    """A sensor reading from the account coordinator."""

    entity_description: NlbSensorDescription

    def __init__(
        self, entry: NlbConfigEntry, description: NlbSensorDescription
    ) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> int | None:
        return self.entity_description.value_fn(self.coordinator.data)
