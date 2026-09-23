import os
from pathlib import Path
from dotenv import load_dotenv

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SAMPLE_CSV_PATH = DATA_DIR / "sample_stock_data.csv"

# Load local settings from .env
load_dotenv(BASE_DIR / ".env")

# Database settings
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/marketflow"
)

# Twelve Data settings
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()
TWELVE_DATA_BASE_URL = "https://api.twelvedata.com"


# Stocks included in the local sample data
CSV_SAMPLE_STOCKS = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
}

DEFAULT_SYMBOL = "AAPL"


def mask_key(key: str) -> str:
    """Mask an API key before it is shown in logs or the UI."""
    if not key or key == "your_twelve_data_api_key_here":
        return "Not Configured"
    if len(key) <= 4:
        return "****"
    return f"{'*' * (len(key) - 4)}{key[-4:]}"


def is_twelve_data_configured() -> bool:
    """Return True when a Twelve Data key is configured."""
    return bool(TWELVE_DATA_API_KEY and TWELVE_DATA_API_KEY != "your_twelve_data_api_key_here")
