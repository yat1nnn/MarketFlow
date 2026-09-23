import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from src.api_client import (
    TwelveDataClient,
    TwelveDataRateLimitError,
    TwelveDataAuthError,
    TwelveDataNotFoundError,
    TwelveDataAPIError,
)
from src.extractor import StockDataExtractor
from src.config import mask_key


# Mock API responses
MOCK_TD_SUCCESS = {
    "meta": {
        "symbol": "AAPL",
        "interval": "1day",
        "currency": "USD",
        "exchange_timezone": "America/New_York",
        "exchange": "NASDAQ",
        "mic_code": "XNAS",
        "type": "Common Stock",
    },
    "values": [
        {
            "datetime": "2026-09-18",
            "open": "180.50",
            "high": "182.10",
            "low": "179.80",
            "close": "181.25",
            "volume": "45123000",
        },
        {
            "datetime": "2026-09-17",
            "open": "178.90",
            "high": "181.00",
            "low": "178.50",
            "close": "180.10",
            "volume": "41002000",
        },
    ],
    "status": "ok",
}

MOCK_TD_RATE_LIMIT_429 = {
    "code": 429,
    "message": "You have run out of API credits for the current minute. 8 API credits were used, with the current limit being 8.",
    "status": "error",
}

MOCK_TD_AUTH_ERROR = {
    "code": 401,
    "message": "Invalid apikey. Please visit https://twelvedata.com/ to get a free API key.",
    "status": "error",
}

MOCK_TD_NOT_FOUND = {
    "code": 404,
    "message": "Symbol or exchange is not found. Try switching the exchange.",
    "status": "error",
}

MOCK_TD_SEARCH_RESULTS = {
    "data": [
        {
            "symbol": "AAPL",
            "instrument_name": "Apple Inc.",
            "exchange": "NASDAQ",
            "mic_code": "XNAS",
            "exchange_timezone": "America/New_York",
            "instrument_type": "Common Stock",
            "country": "United States",
            "currency": "USD",
        },
        {
            "symbol": "AAPL.BA",
            "instrument_name": "Apple Inc.",
            "exchange": "BYMA",
            "mic_code": "XBUE",
            "exchange_timezone": "America/Argentina/Buenos_Aires",
            "instrument_type": "Common Stock",
            "country": "Argentina",
            "currency": "ARS",
        },
    ],
    "status": "ok",
}

# Twelve Data client tests

def test_daily_series_request_success():
    """Parse a normal historical response."""
    client = TwelveDataClient(api_key="mock_test_key_12345")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.json.return_value = MOCK_TD_SUCCESS

    with patch("requests.get", return_value=mock_response) as mock_get:
        data = client.fetch_daily_series("AAPL")
        assert "values" in data
        assert len(data["values"]) == 2
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["symbol"] == "AAPL"
        assert kwargs["params"]["apikey"] == "mock_test_key_12345"


def test_rate_limit_response_raises():
    """Treat a rate-limit response body as a limit error."""
    client = TwelveDataClient(api_key="mock_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200        # Twelve Data returns 200 even for rate errors
    mock_resp.headers = {}
    mock_resp.json.return_value = MOCK_TD_RATE_LIMIT_429

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(TwelveDataRateLimitError):
            client.fetch_daily_series("AAPL")


def test_http_429_raises_rate_limit():
    """Treat HTTP 429 as a rate-limit error."""
    client = TwelveDataClient(api_key="mock_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.headers = {}
    mock_resp.json.return_value = {"status": "error", "message": "rate limit"}

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(TwelveDataRateLimitError):
            client.fetch_daily_series("AAPL")


def test_invalid_symbol_response_raises():
    """Raise the not-found error returned by the API."""
    client = TwelveDataClient(api_key="mock_key")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.json.return_value = MOCK_TD_NOT_FOUND

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(TwelveDataNotFoundError):
            client.fetch_daily_series("NON_EXISTENT_XYZ")


def test_auth_error_response_raises():
    """Raise the authentication error returned by the API."""
    client = TwelveDataClient(api_key="bad_key")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.json.return_value = MOCK_TD_AUTH_ERROR

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(TwelveDataAuthError):
            client.fetch_daily_series("AAPL")


def test_missing_api_key_raises_auth_error():
    """Reject an empty API key before making a request."""
    client = TwelveDataClient(api_key="")
    with pytest.raises(TwelveDataAuthError):
        client.fetch_daily_series("AAPL")


def test_mask_key_security():
    secret_key = "MY_SUPER_SECRET_KEY_1234"
    masked = mask_key(secret_key)
    assert secret_key not in masked
    assert masked.endswith("1234")
    assert mask_key("") == "Not Configured"
    assert mask_key("ab") == "****"


# Extractor tests

def test_extractor_from_api_parsing():
    """extract_from_api returns DataFrame with date column from Twelve Data values."""
    client = TwelveDataClient(api_key="mock_key")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.json.return_value = MOCK_TD_SUCCESS

    with patch("requests.get", return_value=mock_response):
        extractor = StockDataExtractor(api_client=client)
        df = extractor.extract_from_api("AAPL")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        # Twelve Data 'datetime' field is renamed to 'date' by extract_from_api
        assert "date" in df.columns
        assert "open" in df.columns
        assert "close" in df.columns
        assert "symbol" in df.columns
        assert df["symbol"].iloc[0] == "AAPL"


def test_extractor_fallback_on_rate_limit(tmp_path):
    """Rate-limit response triggers CSV fallback in extract()."""
    csv_file = tmp_path / "test_sample.csv"
    sample_df = pd.DataFrame([
        {"symbol": "AAPL", "date": "2026-09-18", "open": 180.0, "high": 182.0, "low": 179.0, "close": 181.0, "volume": 50000000}
    ])
    sample_df.to_csv(csv_file, index=False)

    client = TwelveDataClient(api_key="mock_key")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.json.return_value = MOCK_TD_RATE_LIMIT_429

    with patch("requests.get", return_value=mock_response):
        extractor = StockDataExtractor(api_client=client, sample_csv_path=csv_file)
        df, source_used, msg = extractor.extract("AAPL", source="API", fallback_to_csv=True)

        assert "Fallback" in source_used
        assert len(df) == 1
        assert df["symbol"].iloc[0] == "AAPL"


def test_extractor_direct_csv_source(tmp_path):
    """Requesting CSV source returns 'Local CSV' label and correct data."""
    csv_file = tmp_path / "test_sample.csv"
    sample_df = pd.DataFrame([
        {"symbol": "MSFT", "date": "2026-09-18", "open": 400.0, "high": 405.0, "low": 398.0, "close": 402.0, "volume": 25000000}
    ])
    sample_df.to_csv(csv_file, index=False)

    extractor = StockDataExtractor(sample_csv_path=csv_file)
    df, source_used, msg = extractor.extract("MSFT", source="CSV")

    assert source_used == "Local CSV"
    assert len(df) == 1
    assert df["symbol"].iloc[0] == "MSFT"


def test_symbol_search_returns_results():
    """Turn a symbol-search response into picker options."""
    client = TwelveDataClient(api_key="mock_key")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.json.return_value = MOCK_TD_SEARCH_RESULTS

    with patch("requests.get", return_value=mock_response):
        results = client.search_symbols("app")

    assert isinstance(results, list)
    assert len(results) >= 1
    first = results[0]
    assert first["symbol"] == "AAPL"
    assert first["company_name"] == "Apple Inc."
    assert first["exchange"] == "NASDAQ"
    assert first["country"] == "United States"


def test_symbol_search_minimum_chars():
    """Do not search for one-character queries."""
    client = TwelveDataClient(api_key="mock_key")
    result = client.search_symbols("a")
    assert result == []
    result2 = client.search_symbols("")
    assert result2 == []


def test_api_usage_unavailable_when_no_key():
    """Report usage as unavailable when no key is configured."""
    client = TwelveDataClient(api_key="")
    usage = client.get_api_usage()
    assert usage["available"] is False


def test_api_usage_from_headers():
    """Read credit counts from response headers when present."""
    client = TwelveDataClient(api_key="mock_key")
    client.last_headers = {
        "api-credits-used": "12",
        "api-credits-total": "800",
    }
    usage = client.get_api_usage()
    assert usage["available"] is True
    assert usage["used"] == 12
    assert usage["limit"] == 800
    assert usage["remaining"] == 788


def test_symbol_is_normalized_before_request():
    """The client sends ticker symbols in uppercase."""
    client = TwelveDataClient(api_key="mock_key")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.json.return_value = MOCK_TD_SUCCESS

    with patch("requests.get", return_value=mock_response) as mock_get:
        client.fetch_daily_series("aapl")

    assert mock_get.call_args.kwargs["params"]["symbol"] == "AAPL"
