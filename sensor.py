"""
Support for Daily Netto Power Result Sensor.

Private, never meant to be used online.
Take first measurement of the day of the DSMR sensors and stores these:
  - sensor.power_consumption_low
  - sensor.power_consumption_normal
  - sensor.power_production_low
  - sensor.power_production_normal
"""

from datetime import timedelta
from decimal import Decimal
import logging

from homeassistant.components import history
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.util import dt


_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
})

INTERESTING_ENTITY_IDS = (
    'sensor.power_consumption_low',
    'sensor.power_consumption_normal',
    'sensor.power_production_low',
    'sensor.power_production_normal',
)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)


def setup_platform(hass, config, add_devices, discovery_debug=None):
    """Set up the Daily Counter sensor."""
    _LOGGER.debug('net_power_results.setup_platform()')
    device = NettoPowerResultSensor(hass)
    add_devices([device], True)


class NettoPowerResultSensor(Entity):
    """Calculating sensor."""

    def __init__(self, hass):
        """Initialize entity."""
        self._hass = hass
        self._state = STATE_UNKNOWN

    @property
    def state(self):
        """Return the state of sensor, if available, translate if needed."""
        _LOGGER.debug('%s.state()', self)

        return self._state

    def _get_states(self, entity_ids, timestamp):
        """Get the current states for entity_ids."""
        _LOGGER.debug('%s._get_states()')
        states = {}
        for entity_id in entity_ids:
            state = history.get_state(self._hass, timestamp, entity_id)
            states[entity_id] = state
        return states

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update: calculate new values."""
        _LOGGER.debug('%s.update()', self)

        # get states at start of day
        start_of_day = dt.start_of_local_day()
        start_of_day_utc = dt.as_utc(start_of_day)
        states_start_of_day = self._get_states(INTERESTING_ENTITY_IDS, start_of_day_utc)
        if len(states_start_of_day) != len(INTERESTING_ENTITY_IDS):
            _LOGGER.debug('%s.update(): do not have all events for start of day', self)
            return
        usage_start_of_day = self._calculate_total(states_start_of_day)
        _LOGGER.debug('%s.update(): usage_start_of_day: %s', self, usage_start_of_day)

        # get states at now
        now = dt.now()
        now_utc = dt.as_utc(now)
        states_now = self._get_states(INTERESTING_ENTITY_IDS, now_utc)
        if len(states_now) != len(INTERESTING_ENTITY_IDS):
            _LOGGER.debug('%s.update(): do not have all events for now', self)
            return
        usage_now = self._calculate_total(states_now)
        _LOGGER.debug('%s.update(): usage_now: %s', self, usage_now)

        # store new state
        self._state = usage_now - usage_start_of_day

    def _calculate_total(self, states):
        """Calculate current """
        consumption = Decimal(states['sensor.power_consumption_low'].state) + \
            Decimal(states['sensor.power_consumption_normal'].state)
        production = Decimal(states['sensor.power_production_low'].state) + \
            Decimal(states['sensor.power_production_normal'].state)
        return consumption - production

    @property
    def name(self):
        """Get name."""
        return 'Todays net power'

    @property
    def unit_of_measurement(self):
        """Get unit of measurement."""
        return ENERGY_KILO_WATT_HOUR

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return 'mdi:flash'

    def __str__(self):
        """To string."""
        return "<{}()>".format(self.__class__.__name__)
