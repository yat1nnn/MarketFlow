import logging
from typing import Dict
import pandas as pd

logger = logging.getLogger(__name__)

# Accepted input column names mapped to the warehouse schema.
COLUMN_ALIASES: Dict[str, str] = {
    "date": "trade_date",
    "trade_date": "trade_date",
    "timestamp": "trade_date",
    "1. open": "open_price",
    "open": "open_price",
    "open_price": "open_price",
    "2. high": "high_price",
    "high": "high_price",
    "high_price": "high_price",
    "3. low": "low_price",
    "low": "low_price",
    "low_price": "low_price",
    "4. close": "close_price",
    "close": "close_price",
    "close_price": "close_price",
    "5. volume": "volume",
    "volume": "volume",
    "symbol": "symbol",
}


class StockDataTransformer:
    """Clean stock data before it is written to the warehouse."""

    @staticmethod
    def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Standardize incoming column names."""
        if df.empty:
            return df.copy()

        df_out = df.copy()
        # Normalize headers first, then apply known aliases.
        rename_map = {}
        for col in df_out.columns:
            cleaned = str(col).strip().lower()
            if cleaned in COLUMN_ALIASES:
                rename_map[col] = COLUMN_ALIASES[cleaned]
            else:
                rename_map[col] = cleaned.replace(" ", "_")

        df_out.rename(columns=rename_map, inplace=True)

        required_cols = ["trade_date", "open_price", "high_price", "low_price", "close_price", "volume"]
        missing = [c for c in required_cols if c not in df_out.columns]
        if missing:
            raise ValueError(f"Dataframe is missing required stock columns: {missing}. Available: {list(df_out.columns)}")

        return df_out

    @staticmethod
    def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
        """Convert dates and discard rows that cannot be parsed."""
        if df.empty:
            return df.copy()

        df_out = df.copy()
        df_out["trade_date"] = pd.to_datetime(df_out["trade_date"], format="mixed", errors="coerce").dt.date
        initial_len = len(df_out)
        df_out = df_out.dropna(subset=["trade_date"])
        dropped = initial_len - len(df_out)
        if dropped > 0:
            logger.warning(f"Dropped {dropped} rows with invalid dates.")
        return df_out

    @staticmethod
    def convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Convert price and volume columns to numeric values."""
        if df.empty:
            return df.copy()

        df_out = df.copy()
        price_cols = ["open_price", "high_price", "low_price", "close_price"]
        for col in price_cols:
            df_out[col] = pd.to_numeric(df_out[col], errors="coerce")

        df_out["volume"] = pd.to_numeric(df_out["volume"], errors="coerce").fillna(0).astype("int64")
        return df_out

    @staticmethod
    def handle_missing_and_invalid(df: pd.DataFrame) -> pd.DataFrame:
        """Fill missing fields and remove invalid price rows."""
        if df.empty:
            return df.copy()

        df_out = df.copy()

        # A non-positive close is not useful for the downstream calculations.
        valid_close = (df_out["close_price"].notna()) & (df_out["close_price"] > 0)
        df_out = df_out[valid_close].copy()

        # Use the close price when one of the OHLC fields is missing.
        df_out["open_price"] = df_out["open_price"].fillna(df_out["close_price"])
        df_out["high_price"] = df_out["high_price"].fillna(df_out[["open_price", "close_price"]].max(axis=1))
        df_out["low_price"] = df_out["low_price"].fillna(df_out[["open_price", "close_price"]].min(axis=1))

        # Keep OHLC values internally consistent.
        df_out["high_price"] = df_out[["high_price", "open_price", "close_price"]].max(axis=1)
        df_out["low_price"] = df_out[["low_price", "open_price", "close_price"]].min(axis=1)

        # Negative volume values are treated as zero.
        df_out["volume"] = df_out["volume"].clip(lower=0)

        # Prices are stored at two decimal places.
        for col in ["open_price", "high_price", "low_price", "close_price"]:
            df_out[col] = df_out[col].round(2)

        return df_out

    @staticmethod
    def deduplicate_and_sort(df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate observations and sort by date."""
        if df.empty:
            return df.copy()

        df_out = df.copy()
        subset = ["trade_date"]
        if "symbol" in df_out.columns:
            subset.append("symbol")

        # When duplicates are present, keep the last observation.
        df_out = df_out.drop_duplicates(subset=subset, keep="last")
        df_out = df_out.sort_values(by="trade_date", ascending=True).reset_index(drop=True)
        return df_out

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run the standard cleaning steps in order."""
        if df is None or df.empty:
            raise ValueError("Cannot transform empty or None dataframe.")

        df_standard = self.standardize_columns(df)
        df_dates = self.parse_dates(df_standard)
        df_numeric = self.convert_numeric_columns(df_dates)
        df_clean = self.handle_missing_and_invalid(df_numeric)
        df_final = self.deduplicate_and_sort(df_clean)

        logger.info(f"Transformation complete. Clean records: {len(df_final)}")
        return df_final
