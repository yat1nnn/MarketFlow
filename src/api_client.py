import logging
import requests
from typing import Dict, Any, List, Optional
from src.config import TWELVE_DATA_BASE_URL, TWELVE_DATA_API_KEY, mask_key

logger = logging.getLogger(__name__)


class TwelveDataError(Exception):
    """Base exception for Twelve Data errors."""
    pass


class TwelveDataRateLimitError(TwelveDataError):
    """Raised when the API limit has been reached."""
    pass


class TwelveDataAuthError(TwelveDataError):
    """Raised when the API key is missing or invalid."""
    pass


class TwelveDataNotFoundError(TwelveDataError):
    """Raised when the requested symbol cannot be found."""
    pass


class TwelveDataAPIError(TwelveDataError):
    """Raised when Twelve Data returns an API error."""
    pass



class TwelveDataClient:
    """Small wrapper around the Twelve Data endpoints used by the app."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: int = 15):
        self.api_key = (api_key if api_key is not None else TWELVE_DATA_API_KEY).strip()
        self.base_url = base_url or TWELVE_DATA_BASE_URL
        self.timeout = timeout
        self.last_headers: Dict[str, str] = {}
        self._cached_usage: Optional[Dict[str, Any]] = None

    def search_symbols(self, query: str, outputsize: int = 10) -> List[Dict[str, Any]]:
        """Search for companies or tickers."""
        if not query or len(query.strip()) < 2:
            return []

        clean_query = query.strip()
        self._require_api_key()

        params = {
            "symbol": clean_query,
            "apikey": self.api_key,
            "outputsize": 30,
        }

        masked = mask_key(self.api_key)
        logger.info(f"Searching Twelve Data symbols for query '{clean_query}' (key={masked})...")

        data = self._request("symbol_search", params)
        raw_items = data.get("data", [])
        if not isinstance(raw_items, list):
            return []

        # Keep only results that have enough information to show in the picker.
        filtered = []
        for item in raw_items:
            symbol = item.get("symbol", "").strip().upper()
            name = item.get("instrument_name", "").strip()
            exchange = item.get("exchange", "").strip()
            country = item.get("country", "").strip()
            instrument_type = item.get("instrument_type") or item.get("type", "")

            if symbol and name:
                filtered.append({
                    "symbol": symbol,
                    "company_name": name,
                    "exchange": exchange,
                    "country": country,
                    "instrument_type": instrument_type,
                    "display": f"{name} ({symbol}) · {exchange}{f' · {country}' if country else ''}"
                })

            if len(filtered) >= outputsize:
                break

        return filtered

    def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch the latest quote for a symbol."""
        if not symbol or not symbol.strip():
            raise ValueError("Stock symbol cannot be empty.")

        clean_symbol = symbol.strip().upper()
        self._require_api_key()

        params = {
            "symbol": clean_symbol,
            "apikey": self.api_key,
        }

        logger.info(f"Fetching quote for symbol '{clean_symbol}' from Twelve Data...")
        data = self._request("quote", params)

        # Convert the numeric fields returned by the API.
        try:
            return {
                "symbol": data.get("symbol", clean_symbol),
                "name": data.get("name", clean_symbol),
                "exchange": data.get("exchange", "N/A"),
                "currency": data.get("currency", "USD"),
                "datetime": data.get("datetime", "N/A"),
                "timestamp": data.get("timestamp"),
                "open": float(data["open"]) if data.get("open") is not None else None,
                "high": float(data["high"]) if data.get("high") is not None else None,
                "low": float(data["low"]) if data.get("low") is not None else None,
                "close": float(data["close"]) if data.get("close") is not None else None,
                "volume": int(float(data["volume"])) if data.get("volume") is not None else 0,
                "previous_close": float(data["previous_close"]) if data.get("previous_close") is not None else None,
                "change": float(data["change"]) if data.get("change") is not None else None,
                "percent_change": float(data["percent_change"]) if data.get("percent_change") is not None else None,
                "is_market_open": bool(data.get("is_market_open", False)),
            }
        except Exception as e:
            logger.warning(f"Error parsing quote values for {clean_symbol}: {e}")
            return data

    def fetch_daily_series(self, symbol: str, outputsize: int = 130) -> Dict[str, Any]:
        """Fetch daily historical data for a symbol."""
        if not symbol or not symbol.strip():
            raise ValueError("Stock symbol cannot be empty.")

        clean_symbol = symbol.strip().upper()
        self._require_api_key()

        params = {
            "symbol": clean_symbol,
            "interval": "1day",
            "outputsize": outputsize,
            "apikey": self.api_key,
        }

        logger.info(f"Fetching daily time series for '{clean_symbol}' from Twelve Data...")
        data = self._request("time_series", params)

        if "values" not in data:
            raise TwelveDataAPIError(f"No 'values' field returned for symbol '{clean_symbol}'.")

        return data

    def get_api_usage(self) -> Dict[str, Any]:
        """Return usage details when Twelve Data makes them available."""
        if not self.api_key or self.api_key == "your_twelve_data_api_key_here":
            return {"available": False, "message": "Usage information unavailable"}

        # A successful API call may include usage headers.
        header_used = self.last_headers.get("api-credits-used") or self.last_headers.get("x-rate-limit-used")
        header_left = self.last_headers.get("api-credits-left") or self.last_headers.get("x-rate-limit-remaining")
        header_limit = self.last_headers.get("api-credits-total") or self.last_headers.get("x-rate-limit-limit")

        if header_used is not None and header_limit is not None:
            try:
                used = int(header_used)
                limit = int(header_limit)
                remaining = int(header_left) if header_left is not None else (limit - used)
                return {
                    "available": True,
                    "used": used,
                    "limit": limit,
                    "remaining": remaining,
                    "source": "headers",
                }
            except (ValueError, TypeError):
                pass

        # Fall back to the usage endpoint when the headers do not help.
        try:
            params = {"apikey": self.api_key}
            resp = requests.get(f"{self.base_url}/api_usage", params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if "current_usage" in data and "plan_limit" in data:
                    used = int(data["current_usage"])
                    limit = int(data["plan_limit"])
                    remaining = max(0, limit - used)
                    return {
                        "available": True,
                        "used": used,
                        "limit": limit,
                        "remaining": remaining,
                        "source": "api_usage",
                    }
        except Exception as e:
            logger.debug(f"Could not fetch Twelve Data /api_usage: {e}")

        return {"available": False, "message": "Usage information unavailable"}

    def _require_api_key(self) -> None:
        """Raise an error when the API key is not configured."""
        if not self.api_key or self.api_key == "your_twelve_data_api_key_here":
            raise TwelveDataAuthError(
                "Twelve Data API key is missing or not configured. "
                "Please configure TWELVE_DATA_API_KEY in .env or use CSV mode."
            )

    def _request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make one HTTP request and translate common API errors."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            self.last_headers = dict(response.headers)
            data = response.json()
        except requests.exceptions.Timeout:
            raise TwelveDataAPIError("Connection timed out while connecting to Twelve Data.")
        except requests.exceptions.RequestException as e:
            raise TwelveDataAPIError(f"Network error while connecting to Twelve Data: {str(e)}")
        except ValueError:
            raise TwelveDataAPIError("Failed to parse Twelve Data response as JSON.")

        # Handle HTTP-level errors first.
        if response.status_code == 401:
            raise TwelveDataAuthError("Invalid Twelve Data API key.")
        if response.status_code == 429:
            raise TwelveDataRateLimitError("Twelve Data API rate limit exceeded or credits exhausted.")
        if response.status_code == 404:
            raise TwelveDataNotFoundError("Requested resource not found on Twelve Data.")

        # Twelve Data can also return errors with HTTP 200.
        if isinstance(data, dict):
            status = data.get("status", "")
            code = data.get("code")
            msg = data.get("message", "")

            if status == "error" or code is not None and code != 200:
                if code == 401 or "apikey" in msg.lower():
                    raise TwelveDataAuthError(f"Twelve Data authentication error: {msg}")
                elif code == 429 or "call limit" in msg.lower() or "minute" in msg.lower():
                    raise TwelveDataRateLimitError(f"Twelve Data rate limit hit: {msg}")
                elif code == 404 or "not found" in msg.lower():
                    raise TwelveDataNotFoundError(f"Symbol not found on Twelve Data: {msg}")
                else:
                    raise TwelveDataAPIError(f"Twelve Data API error ({code}): {msg}")

        return data

