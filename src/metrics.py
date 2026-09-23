import logging
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_daily_change(close_series: pd.Series, open_series: pd.Series) -> pd.Series:
    """Calculate the daily price change."""
    prior_close_diff = close_series.diff()
    intraday_diff = close_series - open_series
    return prior_close_diff.fillna(intraday_diff).round(2)


def calculate_daily_return_pct(close_series: pd.Series) -> pd.Series:
    """Calculate day-over-day return as a percentage."""
    return (close_series.pct_change() * 100.0).fillna(0.0).round(4)


def calculate_moving_average(series: pd.Series, window: int) -> pd.Series:
    """Calculate a rolling simple moving average."""
    return series.rolling(window=window, min_periods=1).mean().round(2)


def calculate_rolling_volatility(return_series: pd.Series, window: int = 30) -> pd.Series:
    """Calculate rolling volatility from daily returns."""
    return return_series.rolling(window=window, min_periods=2).std().fillna(0.0).round(4)


def calculate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add the derived metrics used by the dashboard."""
    if df is None or df.empty:
        raise ValueError("Cannot calculate metrics on empty dataframe.")

    df_out = df.copy()

    # Check that the price columns needed for the calculations are present.
    if "close_price" not in df_out.columns or "open_price" not in df_out.columns:
        raise ValueError("Dataframe must contain 'close_price' and 'open_price' columns.")

    # Build each metric from the cleaned prices.
    df_out["daily_change"] = calculate_daily_change(df_out["close_price"], df_out["open_price"])
    df_out["daily_return_pct"] = calculate_daily_return_pct(df_out["close_price"])
    df_out["moving_avg_7"] = calculate_moving_average(df_out["close_price"], window=7)
    df_out["moving_avg_30"] = calculate_moving_average(df_out["close_price"], window=30)
    df_out["volatility"] = calculate_rolling_volatility(df_out["daily_return_pct"], window=30)

    logger.info(f"Computed financial metrics for {len(df_out)} rows.")
    return df_out
