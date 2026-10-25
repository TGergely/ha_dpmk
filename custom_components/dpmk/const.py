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

CONF_LANGUAGE = "language"
LANG_SK = "sk"
LANG_EN = "en"
LANG_AUTO = "auto"  # follow the Home Assistant language
DEFAULT_LANGUAGE = LANG_AUTO

CONF_LOCATION = "location"
DEFAULT_RADIUS = 1500  # map radius in metres
CONF_MAP_RADIUS = "map_radius"
CONF_AUTO_LOCATION = "auto_location"  # a single stop: put the map where the stop is
CONF_IS_DEFAULT = "is_default"  # cards without an entity use this stop or place
CONF_STOP_NUMBER = "stop_number"  # the add-a-stop form: a number missing from the bundled list

# A "place": several stops near one spot, shown as one sensor and one map
CONF_PLACE_NAME = "place_name"
CONF_PLACE_LOCATION = "place_location"
CONF_PLACE_RADIUS = "place_radius"
CONF_STOP_IDS = "stop_ids"
DEFAULT_PLACE_RADIUS = 300
PLACE_CANDIDATE_RADIUS = 1000  # the options form offers stops this close to a place

DEFAULT_MAX_DEPARTURES = 8
CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_UPDATE_INTERVAL = 10  # seconds between refreshes (DPMK itself updates a vehicle ~every 20 s)
MIN_UPDATE_INTERVAL = 5  # hard floor: the live feed is never read more often than this
MAX_UPDATE_INTERVAL = 120
SCHEDULE_TTL_SECONDS = 12 * 3600

CARD_URL = "/dpmk_static/dpmk-departures-card.js"
