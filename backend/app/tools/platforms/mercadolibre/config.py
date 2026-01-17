"""Mercado Libre platform constants and configuration."""

# Default Site ID (Argentina)
DEFAULT_SITE_ID = "MLA"

# Supported Site IDs
SUPPORTED_SITES = {
    "MLA": "Argentina",
    "MLB": "Brazil",
    "MLM": "Mexico",
    "MLC": "Chile",
    "MLU": "Uruguay",
    "MCO": "Colombia",
    "MPE": "Peru",
    "MLV": "Venezuela",
}

# API Endpoints
ITEMS_ENDPOINT = "items"
USERS_ENDPOINT = "users"
QUESTIONS_ENDPOINT = "questions"
ANSWERS_ENDPOINT = "answers"
CATEGORIES_ENDPOINT = "categories"
SITES_ENDPOINT = "sites"
SIZE_CHARTS_ENDPOINT = "catalog/charts"

# Item status values
STATUS_ACTIVE = "active"
STATUS_PAUSED = "paused"
STATUS_CLOSED = "closed"

# Question status values
QUESTION_STATUS_UNANSWERED = "UNANSWERED"
QUESTION_STATUS_ANSWERED = "ANSWERED"

# Listing types
LISTING_TYPE_GOLD_SPECIAL = "gold_special"
LISTING_TYPE_GOLD_PRO = "gold_pro"
LISTING_TYPE_GOLD = "gold"
LISTING_TYPE_SILVER = "silver"
LISTING_TYPE_BRONZE = "bronze"
LISTING_TYPE_FREE = "free"

# Buying modes
BUYING_MODE_BUY_IT_NOW = "buy_it_now"
BUYING_MODE_AUCTION = "auction"

# Conditions
CONDITION_NEW = "new"
CONDITION_USED = "used"
CONDITION_REFURBISHED = "refurbished"
