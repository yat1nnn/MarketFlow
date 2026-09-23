import datetime
import pytest
import pandas as pd
import numpy as np
from src.transformer import StockDataTransformer


def test_standardize_numbered_columns():
    transformer = StockDataTransformer()
    raw_df = pd.DataFrame([
        {
            "date": "2026-09-18",
            "1. open": "180.50",
            "2. high": "182.10",
            "3. low": "179.80",
            "4. close": "181.25",
            "5. volume": "45123000",
        }
    ])
    std_df = transformer.standardize_columns(raw_df)
    expected_cols = ["trade_date", "open_price", "high_price", "low_price", "close_price", "volume"]
    for col in expected_cols:
        assert col in std_df.columns


def test_standardize_columns_csv_format():
    transformer = StockDataTransformer()
    raw_df = pd.DataFrame([
        {
            "Date": "2026-09-18",
            "Open": 180.50,
            "High": 182.10,
            "Low": 179.80,
            "Close": 181.25,
            "Volume": 45123000,
        }
    ])
    std_df = transformer.standardize_columns(raw_df)
    assert "trade_date" in std_df.columns
    assert "open_price" in std_df.columns
    assert "close_price" in std_df.columns


def test_date_conversion():
    transformer = StockDataTransformer()
    df = pd.DataFrame({
        "trade_date": ["2026-09-18", "2026/09/17", "invalid-date", None],
        "open_price": [100.0, 101.0, 102.0, 103.0],
        "high_price": [105.0, 106.0, 107.0, 108.0],
        "low_price": [98.0, 99.0, 100.0, 101.0],
        "close_price": [104.0, 105.0, 106.0, 107.0],
        "volume": [1000, 2000, 3000, 4000],
    })
    parsed = transformer.parse_dates(df)
    assert len(parsed) == 2
    assert parsed["trade_date"].iloc[0] == datetime.date(2026, 9, 18)
    assert parsed["trade_date"].iloc[1] == datetime.date(2026, 9, 17)


def test_numeric_coercion():
    transformer = StockDataTransformer()
    df = pd.DataFrame({
        "trade_date": [datetime.date(2026, 9, 18)],
        "open_price": ["180.25"],
        "high_price": ["185.50"],
        "low_price": ["179.00"],
        "close_price": ["183.75"],
        "volume": ["5500000"],
    })
    numeric_df = transformer.convert_numeric_columns(df)
    assert isinstance(numeric_df["open_price"].iloc[0], (float, np.floating))
    assert isinstance(numeric_df["volume"].iloc[0], (int, np.integer))
    assert numeric_df["volume"].iloc[0] == 5500000


def test_handle_missing_and_invalid_data():
    transformer = StockDataTransformer()
    df = pd.DataFrame({
        "trade_date": [datetime.date(2026, 9, 18), datetime.date(2026, 9, 17), datetime.date(2026, 9, 16)],
        "open_price": [None, 100.0, 150.0],
        "high_price": [105.0, None, 140.0],  # 140 is lower than open 150 -> should be adjusted
        "low_price": [95.0, None, 160.0],   # 160 is higher than close 145 -> should be adjusted
        "close_price": [102.0, -10.0, 145.0], # Row 1 has negative close -> should be dropped
        "volume": [-500, 2000, 3000],        # Row 0 has negative volume -> should clip to 0
    })
    clean = transformer.handle_missing_and_invalid(df)
    assert len(clean) == 2  # Row with negative close dropped
    # The missing open price should use the close price.
    assert clean["open_price"].iloc[0] == 102.0
    assert clean["volume"].iloc[0] == 0
    # High and low should still contain the open/close range.
    assert clean["high_price"].iloc[1] >= 150.0
    assert clean["low_price"].iloc[1] <= 145.0


def test_deduplicate_and_sort():
    transformer = StockDataTransformer()
    df = pd.DataFrame({
        "trade_date": [
            datetime.date(2026, 9, 19),
            datetime.date(2026, 9, 17),
            datetime.date(2026, 9, 17), # Duplicate date
            datetime.date(2026, 9, 18),
        ],
        "close_price": [103.0, 100.0, 101.0, 102.0],
    })
    dedup = transformer.deduplicate_and_sort(df)
    assert len(dedup) == 3
    # Dates should be sorted from oldest to newest.
    assert list(dedup["trade_date"]) == [
        datetime.date(2026, 9, 17),
        datetime.date(2026, 9, 18),
        datetime.date(2026, 9, 19),
    ]
    # The last value for the duplicate date should be kept.
    assert dedup[dedup["trade_date"] == datetime.date(2026, 9, 17)]["close_price"].iloc[0] == 101.0


def test_full_transform_pipeline():
    transformer = StockDataTransformer()
    raw = pd.DataFrame({
        "date": ["2026-09-18", "2026-09-15", "2026-09-16"],
        "1. open": ["100", "90", "95"],
        "2. high": ["105", "92", "98"],
        "3. low": ["99", "88", "93"],
        "4. close": ["103", "91", "97"],
        "5. volume": ["1000", "2000", "1500"],
    })
    result = transformer.transform(raw)
    assert len(result) == 3
    assert list(result["trade_date"]) == [
        datetime.date(2026, 9, 15),
        datetime.date(2026, 9, 16),
        datetime.date(2026, 9, 18),
    ]
