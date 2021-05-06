"""Support for N26 bank accounts."""
from datetime import datetime, timedelta, timezone
import logging

from n26.api import Api
from n26.config import Config
from requests import HTTPError
import voluptuous as vol

from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform
from homeassistant.util import Throttle

from .const import CONF_DEVICE_TOKEN, DATA, DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

# define configuration parameters
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                {
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                    vol.Required(CONF_DEVICE_TOKEN): cv.string,
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): cv.time_period,
                }
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = ["sensor", "switch"]


def setup(hass, config):
    """Set up N26 Component."""
    acc_list = config[DOMAIN]

    api_data_list = []

    for acc in acc_list:
        user = acc[CONF_USERNAME]
        password = acc[CONF_PASSWORD]
        device_token = acc[CONF_DEVICE_TOKEN]

        conf = Config(validate=False)

        conf.USERNAME.value = user
        conf.PASSWORD.value = password
        conf.DEVICE_TOKEN.value = device_token

        conf.LOGIN_DATA_STORE_PATH.value = "~/.config/n26/token"
        conf.MFA_TYPE.value = "app"
        conf.validate()

        api = Api(conf)

        try:
            api.get_token()
        except HTTPError as err:
            _LOGGER.error(str(err))
            return False

        api_data = N26Data(api)
        api_data.update()

        api_data_list.append(api_data)

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][DATA] = api_data_list

    # Load platforms for supported devices
    for platform in PLATFORMS:
        load_platform(hass, platform, DOMAIN, {}, config)

    return True


def timestamp_ms_to_date(epoch_ms) -> datetime or None:
    """Convert millisecond timestamp to datetime."""
    if epoch_ms:
        return datetime.fromtimestamp(epoch_ms / 1000, timezone.utc)


class N26Data:
    """Handle N26 API object and limit updates."""

    def __init__(self, api):
        """Initialize the data object."""
        self._api = api

        self._account_info = {}
        self._balance = {}
        self._limits = {}
        self._account_statuses = {}

        self._cards = {}
        self._spaces = {}

    @property
    def api(self):
        """Return N26 api client."""
        return self._api

    @property
    def account_info(self):
        """Return N26 account info."""
        return self._account_info

    @property
    def balance(self):
        """Return N26 account balance."""
        return self._balance

    @property
    def limits(self):
        """Return N26 account limits."""
        return self._limits

    @property
    def account_statuses(self):
        """Return N26 account statuses."""
        return self._account_statuses

    @property
    def cards(self):
        """Return N26 cards."""
        return self._cards

    def card(self, card_id: str, default: dict = None):
        """Return a card by its id or the given default."""
        return next((card for card in self.cards if card["id"] == card_id), default)

    @property
    def spaces(self):
        """Return N26 spaces."""
        return self._spaces

    def space(self, space_id: str, default: dict = None):
        """Return a space by its id or the given default."""
        return next(
            (space for space in self.spaces["spaces"] if space["id"] == space_id),
            default,
        )

    @Throttle(min_time=DEFAULT_SCAN_INTERVAL * 0.8)
    def update_account(self):
        """Get the latest account data from N26."""
        self._account_info = self._api.get_account_info()
        self._balance = self._api.get_balance()
        self._limits = self._api.get_account_limits()
        self._account_statuses = self._api.get_account_statuses()

    @Throttle(min_time=DEFAULT_SCAN_INTERVAL * 0.8)
    def update_cards(self):
        """Get the latest cards data from N26."""
        self._cards = self._api.get_cards()

    @Throttle(min_time=DEFAULT_SCAN_INTERVAL * 0.8)
    def update_spaces(self):
        """Get the latest spaces data from N26."""
        self._spaces = self._api.get_spaces()

    def update(self):
        """Get the latest data from N26."""
        self.update_account()
        self.update_cards()
        self.update_spaces()
