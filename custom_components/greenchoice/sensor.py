from datetime import datetime, timedelta
import logging
import operator
import json
import itertools
import http.client
import urllib.parse

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, STATE_UNKNOWN)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

import homeassistant.helpers.config_validation as cv

__version__ = '0.0.2'

_LOGGER = logging.getLogger(__name__)
_RESOURCE = 'app.greenchoice.nl'

CONF_OVEREENKOMST_ID = 'overeenkomst_id'
CONF_USERNAME = 'username'
CONF_PASSWORD = 'password'

DEFAULT_NAME = 'Energieverbruik'
DEFAULT_DATE_FORMAT = "%y-%m-%dT%H:%M:%S"

ATTR_NAME = 'name'
ATTR_UPDATE_CYCLE = 'update_cycle'
ATTR_ICON = 'icon'
ATTR_MEASUREMENT_DATE = 'date'

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=3600)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_USERNAME, default=CONF_USERNAME): cv.string,
    vol.Optional(CONF_PASSWORD, default=CONF_USERNAME): cv.string,
    vol.Optional(CONF_OVEREENKOMST_ID, default=CONF_OVEREENKOMST_ID): cv.string,
})


def setup_platform(hass, config, add_entities, discovery_info=None):

    name = config.get(CONF_NAME)
    overeenkomst_id = config.get(CONF_OVEREENKOMST_ID)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    greenchoice_api = GreenchoiceApiData(overeenkomst_id,username,password)

    greenchoice_api.update()

    if greenchoice_api is None:
        raise PlatformNotReady

    sensors = []
    sensors.append(GreenchoiceSensor(greenchoice_api, name, overeenkomst_id, username, password, "currentGas"))
    sensors.append(GreenchoiceSensor(greenchoice_api, name, overeenkomst_id, username, password, "currentEnergyDay"))
    sensors.append(GreenchoiceSensor(greenchoice_api, name, overeenkomst_id, username, password, "currentEnergyNight"))
    sensors.append(GreenchoiceSensor(greenchoice_api, name, overeenkomst_id, username, password, "currentEnergyTotal"))
    add_entities(sensors, True)


class GreenchoiceSensor(Entity):
    def __init__(self, greenchoice_api, name, overeenkomst_id, username, password, measurement_type,):
        self._json_data = greenchoice_api
        self._name = name
        self._overeenkomst_id = overeenkomst_id
        self._username = username
        self._password = password
        self._measurement_type = measurement_type
        self._measurement_date = None
        self._state = None
        self._icon = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def overeenkomst_id(self):
        return self._overeenkomst_id

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        return self._state   

    @property
    def measurement_type(self):
        return self._measurement_type

    @property
    def measurement_date(self):
        return self._measurement_date

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return{
            ATTR_MEASUREMENT_DATE: self._measurement_date
        }

    def update(self):
        """Get the latest data from the Greenchoice API."""
        self._json_data.update()

        data = self._json_data.result

        if self._username == CONF_USERNAME or self._username is None:
            _LOGGER.error("Need a username!")
        elif self._password == CONF_PASSWORD or self._password is None:
            _LOGGER.error("Need a password!")
        elif self._overeenkomst_id == CONF_OVEREENKOMST_ID or self._overeenkomst_id is None:
            _LOGGER.error("Need a overeenkomst id (see docs how to get one)!")

        if data is None or self._measurement_type not in data:
            self._state = STATE_UNKNOWN
        else:
            self._state = data[self._measurement_type]
            self._measurement_date = data["measurementDate"]
          
        #TODO: Add m3 and kwh
        if self._measurement_type == "currentEnergyNight":
            self._icon = 'mdi:weather-sunset-down'
            self._name = 'currentEnergyNight'
        if self._measurement_type == "currentEnergyDay":
            self._icon = 'mdi:weather-sunset-up'
            self._name = 'currentEnergyDay'
        if self._measurement_type == "currentEnergyTotal":
            self._icon = 'mdi:power-plug'
            self._name = 'currentEnergyTotal'
        if self._measurement_type == "currentGas":
            self._icon = 'mdi:fire'
            self._name = 'currentGas'


class GreenchoiceApiData:
    def __init__(self, overeenkomst_id, username, password):
        self._resource = _RESOURCE
        self._overeenkomst_id = overeenkomst_id
        self.result = {}
        self.token = ""
        self._tokenheaders = {
            'Content-Type': "application/x-www-form-urlencoded",
            'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 5_0 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9A334 Safari/7534.48.3",
            'Host': "app.greenchoice.nl"
        }
        self._tokenquery = urllib.parse.urlencode({
            'grant_type': 'password',
            'client_id': 'MobileApp',
            'client_secret': 'A6E60EBF73521F57',
            'username': username,
            'password': password,
        })

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.result = {}

        try:
            response = http.client.HTTPSConnection(self._resource, timeout=10)
            response.request("POST", "/token", body = self._tokenquery, headers = self._tokenheaders)
            json_result = json.loads(response.getresponse().read().decode('utf-8'))
            _LOGGER.debug("token json_response=%s", json_result)

            if "access_token" in json_result and "error" not in json_result:
                self.token = json_result["access_token"]

                try:
                    response = http.client.HTTPSConnection(self._resource, timeout=10)
                    response.request("GET", "/api/v2/meterstanden/getstanden?overeenkomstid=" + self._overeenkomst_id, headers = {'Authorization': "Bearer "+self.token})
                    json_result = json.loads(response.getresponse().read().decode('utf-8'))
                    _LOGGER.debug("getstanden json_response=%s", json_result)

                    currentEnergy = [x for x in json_result if x['MeterstandenOutput'][0]['Product'] == 1]
                    currentGas = [x for x in json_result if x['MeterstandenOutput'][0]['Product'] == 3]
                    self.result["currentEnergyNight"] = 0 if len(currentEnergy) == 0 else currentEnergy[0]["MeterstandenOutput"][0]["Laag"]
                    self.result["currentEnergyDay"] = 0 if len(currentEnergy) == 0 else currentEnergy[0]["MeterstandenOutput"][0]["Hoog"]
                    self.result["currentEnergyTotal"] = 0 if len(currentEnergy) == 0 else currentEnergy[0]["MeterstandenOutput"][0]["Hoog"] + currentEnergy[0]["MeterstandenOutput"][0]["Laag"]
                    self.result["currentGas"] = 0 if len(currentGas) == 0 else currentGas[0]["MeterstandenOutput"][0]["Hoog"]
                    self.result["measurementDate"] = json_result[0]["DatumInvoer"]
                except http.client.HTTPException:
                    _LOGGER.error("Could not retrieve current numbers.")
                    self.result = "Could not retrieve current numbers."
            else:
                if "error_description" in json_result:
                    error_description = json_result["error_description"]
                else:
                    error_description = "unknown"
                self.result = f"Could not retrieve token ({error_description})."
                _LOGGER.error(self.result)

        except http.client.HTTPException:
            _LOGGER.error("Could not retrieve token.")
            self.result = "Could not retrieve token."
