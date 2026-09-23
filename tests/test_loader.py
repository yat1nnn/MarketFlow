import datetime
import pytest
import pandas as pd
from sqlalchemy import create_engine, select, func
from src.database import Base, Stock, StockPrice, DailyMetric, get_session
from src.loader import StockDataLoader


@pytest.fixture
def in_memory_engine():
    """Create an isolated in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def sample_metrics_df():
    dates = [
        datetime.date(2026, 9, 15),
        datetime.date(2026, 9, 16),
        datetime.date(2026, 9, 17),
    ]
    return pd.DataFrame({
        "trade_date": dates,
        "open_price": [150.0, 152.0, 151.0],
        "high_price": [155.0, 156.0, 154.0],
        "low_price": [148.0, 150.0, 149.0],
        "close_price": [153.0, 151.0, 153.5],
        "volume": [1000000, 1200000, 1100000],
        "daily_change": [3.0, -2.0, 2.5],
        "daily_return_pct": [2.0, -1.3072, 1.6556],
        "moving_avg_7": [153.0, 152.0, 152.5],
        "moving_avg_30": [153.0, 152.0, 152.5],
        "volatility": [0.0, 2.3385, 1.9876],
    })


def test_idempotent_loading_prices(in_memory_engine, sample_metrics_df):
    loader = StockDataLoader(engine=in_memory_engine)

    # First load should create three rows.
    res1 = loader.load_stock_data("TEST_SYM", sample_metrics_df, company_name="Test Corp")
    assert res1["status"] == "success"
    assert res1["prices_loaded"] == 3
    assert res1["metrics_loaded"] == 3

    # Check the row counts.
    session = get_session(in_memory_engine)
    count_prices = session.query(func.count(StockPrice.id)).scalar()
    count_metrics = session.query(func.count(DailyMetric.id)).scalar()
    assert count_prices == 3
    assert count_metrics == 3
    session.close()

    # Loading the same data again should not add duplicates.
    res2 = loader.load_stock_data("TEST_SYM", sample_metrics_df, company_name="Test Corp")
    assert res2["status"] == "success"

    # The counts should still be three.
    session = get_session(in_memory_engine)
    count_prices_after = session.query(func.count(StockPrice.id)).scalar()
    count_metrics_after = session.query(func.count(DailyMetric.id)).scalar()
    assert count_prices_after == 3
    assert count_metrics_after == 3
    session.close()


def test_upsert_updates_existing_price(in_memory_engine, sample_metrics_df):
    loader = StockDataLoader(engine=in_memory_engine)
    loader.load_stock_data("TEST_SYM", sample_metrics_df)

    # Change the last close and load the data again.
    modified_df = sample_metrics_df.copy()
    modified_df.loc[2, "close_price"] = 999.99

    loader.load_stock_data("TEST_SYM", modified_df)

    # The existing row should have been updated.
    session = get_session(in_memory_engine)
    updated_price = session.execute(
        select(StockPrice).where(StockPrice.trade_date == datetime.date(2026, 9, 17))
    ).scalar_one()
    assert updated_price.close_price == 999.99
    session.close()


def test_query_stock_data(in_memory_engine, sample_metrics_df):
    loader = StockDataLoader(engine=in_memory_engine)
    loader.load_stock_data("TEST_SYM", sample_metrics_df, company_name="Test Corp")

    df = loader.query_stock_data("TEST_SYM")
    assert len(df) == 3
    assert "trade_date" in df.columns
    assert "close_price" in df.columns
    assert "daily_return_pct" in df.columns
    assert df["symbol"].iloc[0] == "TEST_SYM"
    assert df["company_name"].iloc[0] == "Test Corp"


def test_get_available_symbols(in_memory_engine, sample_metrics_df):
    loader = StockDataLoader(engine=in_memory_engine)
    loader.load_stock_data("SYM_A", sample_metrics_df, company_name="Corp A")
    loader.load_stock_data("SYM_B", sample_metrics_df, company_name="Corp B")

    symbols = loader.get_available_symbols()
    assert len(symbols) == 2
    sym_names = [s["symbol"] for s in symbols]
    assert "SYM_A" in sym_names
    assert "SYM_B" in sym_names
