import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import pandas as pd

from src.api_client import (
    TwelveDataClient,
    TwelveDataError,
    TwelveDataRateLimitError,
    TwelveDataAuthError,
    TwelveDataNotFoundError,
    TwelveDataAPIError,
)
from src.config import SAMPLE_CSV_PATH, CSV_SAMPLE_STOCKS

logger = logging.getLogger(__name__)


class StockDataExtractor:
    """Read stock data from Twelve Data or the bundled CSV file."""

    def __init__(self, api_client: Optional[TwelveDataClient] = None, sample_csv_path: Optional[Path] = None):
        self.api_client = api_client or TwelveDataClient()
        self.sample_csv_path = Path(sample_csv_path or SAMPLE_CSV_PATH)

    def search_symbols(self, query: str) -> List[Dict[str, Any]]:
        """Search instruments using Twelve Data."""
        return self.api_client.search_symbols(query)

    def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch real-time / latest market quote from Twelve Data."""
        return self.api_client.fetch_quote(symbol)

    def get_api_usage(self) -> Dict[str, Any]:
        """Fetch API credit usage information."""
        return self.api_client.get_api_usage()

    def extract_from_api(self, symbol: str) -> pd.DataFrame:
        """Fetch daily data from Twelve Data and return it as a DataFrame."""
        symbol = symbol.strip().upper()
        raw_json = self.api_client.fetch_daily_series(symbol)
        values = raw_json.get("values", [])

        if not values:
            raise ValueError(f"No daily historical records returned for symbol '{symbol}'.")

        df = pd.DataFrame(values)
        if "datetime" in df.columns:
            df.rename(columns={"datetime": "date"}, inplace=True)
        df["symbol"] = symbol
        logger.info("Loaded %s daily records for %s from Twelve Data.", len(df), symbol)
        return df

    def extract_from_csv(self, symbol: Optional[str] = None, file_path: Optional[Path] = None) -> pd.DataFrame:
        """Read stock data from the bundled CSV file."""
        target_path = Path(file_path or self.sample_csv_path)
        if not target_path.exists():
            raise FileNotFoundError(f"Sample data CSV not found at: {target_path}")

        df = pd.read_csv(target_path)
        logger.info(f"Loaded {len(df)} records from CSV: {target_path}")

        if symbol:
            sym_clean = symbol.strip().upper()
            if "symbol" in df.columns:
                filtered_df = df[df["symbol"].str.upper() == sym_clean].copy()
                if not filtered_df.empty:
                    return filtered_df
                else:
                    logger.warning(f"Symbol '{sym_clean}' not in CSV. Using available symbols.")
                    first_sym = df["symbol"].iloc[0]
                    return df[df["symbol"] == first_sym].copy()
            else:
                df["symbol"] = sym_clean

        return df

    def extract(
        self,
        symbol: str,
        source: str = "API",
        fallback_to_csv: bool = True
    ) -> Tuple[pd.DataFrame, str, str]:
        """Load data from the selected source, with CSV fallback for API failures."""
        sym = symbol.strip().upper()
        if source.upper() == "CSV":
            df = self.extract_from_csv(sym)
            return df, "Local CSV", f"Successfully loaded {len(df)} records from local CSV."

        # Attempt extraction from API
        try:
            df = self.extract_from_api(sym)
            return df, "Twelve Data API", f"Successfully fetched {len(df)} records from Twelve Data API."
        except TwelveDataRateLimitError as rle:
            logger.warning(f"Twelve Data rate limit hit for {sym}: {rle}")
            if fallback_to_csv:
                logger.info("Falling back to local CSV sample data...")
                df = self.extract_from_csv(sym)
                return df, "CSV Fallback (Rate Limit)", f"Twelve Data rate limit reached. Loaded {len(df)} records from CSV fallback."
            raise
        except (TwelveDataAuthError, TwelveDataAPIError, TwelveDataNotFoundError, Exception) as err:
            logger.warning(f"API error for {sym}: {err}")
            if fallback_to_csv:
                logger.info("Falling back to local CSV sample data...")
                df = self.extract_from_csv(sym)
                return df, "CSV Fallback (API Error)", f"API error encountered ({str(err)}). Loaded {len(df)} records from CSV fallback."
            raise
