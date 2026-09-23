import datetime
import pytest
import pandas as pd
import numpy as np
from src.metrics import (
    calculate_daily_change,
    calculate_daily_return_pct,
    calculate_moving_average,
    calculate_rolling_volatility,
    calculate_metrics,
)


def test_daily_change():
    close = pd.Series([100.0, 105.0, 102.0, 107.0])
    open_p = pd.Series([98.0, 101.0, 104.0, 103.0])
    change = calculate_daily_change(close, open_p)

    # First row uses the same-day open/close change.
    assert change.iloc[0] == 2.0
    # Later rows compare consecutive closes.
    assert change.iloc[1] == 5.0   # 105 - 100
    assert change.iloc[2] == -3.0  # 102 - 105
    assert change.iloc[3] == 5.0   # 107 - 102


def test_daily_return_pct():
    close = pd.Series([100.0, 110.0, 99.0])
    returns = calculate_daily_return_pct(close)

    # No previous close exists for the first row.
    assert returns.iloc[0] == 0.0
    # 100 -> 110 is a 10% increase.
    assert returns.iloc[1] == 10.0
    # 110 -> 99 is a 10% decrease.
    assert returns.iloc[2] == -10.0


def test_moving_averages():
    prices = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0])
    ma_3 = calculate_moving_average(prices, window=3)

    # Index 0: 10.0
    assert ma_3.iloc[0] == 10.0
    # Index 1: (10 + 20) / 2 = 15.0
    assert ma_3.iloc[1] == 15.0
    # Index 2: (10 + 20 + 30) / 3 = 20.0
    assert ma_3.iloc[2] == 20.0
    # Index 3: (20 + 30 + 40) / 3 = 30.0
    assert ma_3.iloc[3] == 30.0


def test_rolling_volatility():
    # Constant returns have zero volatility.
    returns = pd.Series([2.0, 2.0, 2.0, 2.0, 2.0])
    vol = calculate_rolling_volatility(returns, window=3)
    assert vol.iloc[0] == 0.0
    assert vol.iloc[2] == 0.0

    # Changing returns should produce non-zero volatility.
    var_returns = pd.Series([1.0, -1.0, 2.0, -2.0, 1.5])
    vol_var = calculate_rolling_volatility(var_returns, window=3)
    assert vol_var.iloc[2] > 0.0


def test_calculate_metrics_integration():
    dates = [datetime.date(2026, 9, 1) + datetime.timedelta(days=i) for i in range(10)]
    df = pd.DataFrame({
        "trade_date": dates,
        "open_price": [100.0 + i for i in range(10)],
        "high_price": [105.0 + i for i in range(10)],
        "low_price": [98.0 + i for i in range(10)],
        "close_price": [102.0 + i for i in range(10)],
        "volume": [1000000 for _ in range(10)],
    })

    result = calculate_metrics(df)

    expected_cols = ["daily_change", "daily_return_pct", "moving_avg_7", "moving_avg_30", "volatility"]
    for col in expected_cols:
        assert col in result.columns
        assert not result[col].isna().any()

    # The first full 7-day window should be populated.
    assert result["moving_avg_7"].iloc[6] > 0
