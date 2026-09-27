"""Constants for the Livebox Call Monitor integration."""

DOMAIN = "livebox_callmon"

CONF_HOST = "host"
CONF_PASSWORD = "password"
CONF_USERNAME = "username"
CONF_POLL_INTERVAL = "poll_interval"
CONF_COUNTRY_PREFIX = "country_prefix"

DEFAULT_HOST = "http://192.168.1.1"
DEFAULT_USERNAME = "admin"
DEFAULT_POLL_INTERVAL = 15          # seconds — call-list poll
DEFAULT_RING_INTERVAL = 3           # seconds — fast poll while a ring is active
DEFAULT_COUNTRY_PREFIX = "33"
DEFAULT_HISTORY_LEN = 50

# Storage
STORAGE_KEY = "livebox_callmon_contacts"
STORAGE_VERSION = 1

# Contact tags
TAGS = ["family", "work", "spam", "other"]

# Events fired on the HA bus
EVENT_RING = f"{DOMAIN}_ring"          # fired when the phone starts ringing
EVENT_NEW_CALL = f"{DOMAIN}_new_call"  # fired when a new call is logged

# Services
SERVICE_ADD_CONTACT = "add_contact"
SERVICE_EDIT_CONTACT = "edit_contact"
SERVICE_DELETE_CONTACT = "delete_contact"

DIRECTION_INCOMING = "incoming"
DIRECTION_OUTGOING = "outgoing"
DIRECTION_MISSED = "missed"
