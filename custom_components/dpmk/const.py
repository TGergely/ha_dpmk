"""Constants for the DPMK Košice integration."""

DOMAIN = "dpmk"
BASE_URL = "https://www.dpmk.sk"

CONF_STOP_ID = "stop_id"
CONF_STOP_NAME = "stop_name"
CONF_ROUTES = "routes"
CONF_MAX_DEPARTURES = "max_departures"
CONF_SCHOOL_MODE = "school_mode"

SCHOOL_AUTO = "auto"
SCHOOL_SCHOOL = "school"
SCHOOL_HOLIDAYS = "holidays"

CONF_MAP_SCOPE = "map_scope"
SCOPE_SERVING = "serving"
SCOPE_ALL = "all"

CONF_LOCATION = "location"
DEFAULT_RADIUS = 1500

DEFAULT_MAX_DEPARTURES = 8
CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_UPDATE_INTERVAL = 10  # seconds between refreshes (DPMK itself updates a vehicle ~every 20 s)
MIN_UPDATE_INTERVAL = 5  # hard floor: the live feed is never read more often than this
MAX_UPDATE_INTERVAL = 120
SCHEDULE_TTL_SECONDS = 12 * 3600

CARD_URL = "/dpmk_static/dpmk-departures-card.js"
