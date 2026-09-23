import streamlit as st
import pandas as pd
from sqlalchemy import text
from src.database import get_engine, check_connection
from src.loader import StockDataLoader

st.set_page_config(page_title="Pipeline Status | MarketFlow", page_icon="⚙️", layout="wide")

st.title("⚙️ MarketFlow Pipeline Health & Data Warehouse")
st.markdown("Live monitoring of PostgreSQL storage, schema integrity, and pipeline execution status.")

# Connection check
engine = get_engine()
is_connected, msg = check_connection(engine)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Database Health")
    if is_connected:
        st.success(f"Status: Healthy ({msg})")
        st.write(f"**Dialect**: {engine.dialect.name.upper()}")
        st.write(f"**Pool Size**: {engine.pool.size()} (Max Overflow: {engine.pool._max_overflow})")
    else:
        st.error(f"Status: Unhealthy ({msg})")

with col2:
    st.subheader("Relational Schema Row Counts")
    if is_connected:
        try:
            with engine.connect() as conn:
                stocks_count = conn.execute(text("SELECT COUNT(*) FROM stocks")).scalar()
                prices_count = conn.execute(text("SELECT COUNT(*) FROM stock_prices")).scalar()
                metrics_count = conn.execute(text("SELECT COUNT(*) FROM daily_metrics")).scalar()

            counts_df = pd.DataFrame([
                {"Table Name": "stocks", "Description": "Stock Tickers & Company Names", "Row Count": stocks_count},
                {"Table Name": "stock_prices", "Description": "OHLCV Cleaned Trade Records", "Row Count": prices_count},
                {"Table Name": "daily_metrics", "Description": "Derived Financial Metrics (MAs, Volatility)", "Row Count": metrics_count},
            ])
            st.dataframe(counts_df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error reading table counts: {e}")

st.markdown("---")
st.subheader("🧪 Live Idempotency Verification")
st.markdown("Click below to test reloading data and verify that record counts remain stable without creating duplicate rows.")

if st.button("Run Idempotency Verification Check"):
    loader = StockDataLoader(engine=engine)
    with st.spinner("Executing idempotent reload verification..."):
        try:
            from src.extractor import StockDataExtractor
            from src.transformer import StockDataTransformer
            from src.metrics import calculate_metrics

            extractor = StockDataExtractor()
            transformer = StockDataTransformer()

            raw_df, _, _ = extractor.extract("AAPL", source="CSV")
            clean_df = transformer.transform(raw_df)
            metrics_df = calculate_metrics(clean_df)

            # Ingest once
            res1 = loader.load_stock_data("AAPL", metrics_df)
            with engine.connect() as conn:
                count1 = conn.execute(text("SELECT COUNT(*) FROM stock_prices WHERE stock_id = :sid"), {"sid": res1["stock_id"]}).scalar()

            # Ingest second time
            res2 = loader.load_stock_data("AAPL", metrics_df)
            with engine.connect() as conn:
                count2 = conn.execute(text("SELECT COUNT(*) FROM stock_prices WHERE stock_id = :sid"), {"sid": res2["stock_id"]}).scalar()

            if count1 == count2:
                st.success(f"✅ Idempotency Verified! Initial count = {count1}, Second run count = {count2}. Zero duplicate records created.")
            else:
                st.error(f"❌ Idempotency Failure: Count changed from {count1} to {count2}!")
        except Exception as err:
            st.error(f"Test failed with error: {err}")
