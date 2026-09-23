import streamlit as st
import pandas as pd
from src.loader import StockDataLoader
from src.config import CSV_SAMPLE_STOCKS

st.set_page_config(page_title="Data Explorer | MarketFlow", page_icon="📊", layout="wide")

st.title("📊 MarketFlow Data Explorer")
st.markdown("Explore, query, and export warehouse data loaded from the stock ETL pipeline.")

loader = StockDataLoader()

# Fetch available symbols in the database
available_stocks = loader.get_available_symbols()

if not available_stocks:
    st.info("No stock data found in PostgreSQL database. Please run an ETL ingestion from the main dashboard.")
else:
    col1, col2 = st.columns([1, 3])
    with col1:
        symbols_list = [s["symbol"] for s in available_stocks]
        selected_symbol = st.selectbox("Select Stock Symbol", symbols_list)

    with col2:
        stock_meta = next((s for s in available_stocks if s["symbol"] == selected_symbol), None)
        if stock_meta:
            st.markdown(
                f"**Company**: {stock_meta.get('company_name', 'N/A')} | "
                f"**Stored Records**: {stock_meta.get('record_count', 0)} | "
                f"**Date Range**: {stock_meta.get('min_date')} to {stock_meta.get('max_date')}"
            )

    df = loader.query_stock_data(selected_symbol)

    if not df.empty:
        st.subheader("Data Summary Statistics")
        desc = df[["open_price", "high_price", "low_price", "close_price", "volume", "daily_return_pct", "volatility"]].describe().T
        st.dataframe(desc.round(2), use_container_width=True)

        st.subheader(f"Historical Records for {selected_symbol}")
        st.dataframe(
            df.sort_values(by="trade_date", ascending=False),
            use_container_width=True,
            hide_index=True
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"📥 Download {selected_symbol} Data as CSV",
            data=csv,
            file_name=f"{selected_symbol}_marketflow_data.csv",
            mime="text/csv",
        )
