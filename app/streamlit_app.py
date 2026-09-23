import sys
from pathlib import Path
import streamlit as st
import pandas as pd

# Make project imports work when Streamlit is launched from the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import CSV_SAMPLE_STOCKS, TWELVE_DATA_API_KEY
from src.extractor import StockDataExtractor
from src.transformer import StockDataTransformer
from src.metrics import calculate_metrics
from src.loader import StockDataLoader
from app.components.sidebar import render_sidebar
from app.components.metrics_cards import render_metric_cards
from app.components.charts import (
    plot_price_and_candlestick,
    plot_historical_close,
    plot_volume,
    plot_daily_returns,
    plot_volatility,
)

# Page settings
st.set_page_config(
    page_title="MarketFlow | Stock Market Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dashboard styling
st.markdown(
    """
    <style>
    /* Keep the main content close to the top of the page. */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 100% !important;
    }
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        height: 2.2rem !important;
    }
    
    /* Main heading and subtitle */
    .main-header {
        font-size: 2.0rem;
        font-weight: 700;
        color: #f8fafc !important;
        margin-bottom: 0.1rem;
        line-height: 1.2;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #94a3b8 !important;
        margin-bottom: 1.0rem;
    }

    /* Source badges */
    .source-badge-csv {
        background-color: #065f46;
        color: #34d399;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 9999px;
        border: 1px solid #059669;
        display: inline-block;
    }
    .source-badge-api {
        background-color: #1e3a8a;
        color: #60a5fa;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 9999px;
        border: 1px solid #2563eb;
        display: inline-block;
    }

    /* Latest quote */
    .quote-box {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Pipeline services
extractor = StockDataExtractor()
transformer = StockDataTransformer()
loader = StockDataLoader()

# Sidebar controls
sidebar_state = render_sidebar()
mode = sidebar_state["mode"]
symbol = sidebar_state["symbol"]
company_name = sidebar_state["company_name"]
exchange = sidebar_state.get("exchange", "NASDAQ")
country = sidebar_state.get("country", "United States")
start_date = sidebar_state["start_date"]
end_date = sidebar_state["end_date"]
trigger_pipeline = sidebar_state["trigger_pipeline"]
refresh_quote = sidebar_state["refresh_quote"]

# Cache API history to avoid repeated requests.
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_cached_api_historical(sym: str, api_key: str):
    """Cache historical data for a short period."""
    return extractor.extract_from_api(sym)

# Cache quotes separately because they change more often.
@st.cache_data(ttl=300, show_spinner=False)
def fetch_cached_quote(sym: str, api_key: str):
    """Cache the latest quote for five minutes."""
    return extractor.fetch_quote(sym)


# Header
col_title, col_source = st.columns([3, 1])

with col_title:
    display_title = f"{symbol} — {company_name}" if symbol else "MarketFlow Stock Analytics"
    st.markdown(f"<div class='main-header'>📈 {display_title}</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='sub-header'>Market data from Twelve Data or the local sample, stored in PostgreSQL</div>",
        unsafe_allow_html=True,
    )

with col_source:
    if mode == "CSV":
        st.markdown(
            """
            <div style="text-align: right; padding-top: 8px;">
                <span class="source-badge-csv">Data Source: Local CSV</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="text-align: right; padding-top: 8px;">
                <span class="source-badge-api">Data Source: Twelve Data API</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


# Latest quote
if mode == "API" and symbol:
    if not TWELVE_DATA_API_KEY or TWELVE_DATA_API_KEY == "your_twelve_data_api_key_here":
        st.warning("⚠️ Twelve Data API key is not configured in .env. Showing local warehouse data where available.")
    else:
        # Clear the quote cache when the user asks for a refresh.
        if refresh_quote:
            fetch_cached_quote.clear()
            st.toast("Refreshing live quote from Twelve Data...", icon="🔄")

        with st.spinner("Loading live quote from Twelve Data..."):
            try:
                quote = fetch_cached_quote(symbol, TWELVE_DATA_API_KEY)
                st.session_state["api_quote_data"] = quote
            except Exception as e:
                logger_msg = str(e)
                st.info(f"Quote notice for {symbol}: {logger_msg}")
                quote = st.session_state.get("api_quote_data")

        if quote and isinstance(quote, dict) and "close" in quote and quote["close"] is not None:
            q_price = quote.get("close", 0.0)
            q_change = quote.get("change", 0.0)
            q_pct = quote.get("percent_change", 0.0)
            q_open = quote.get("open")
            q_high = quote.get("high")
            q_low = quote.get("low")
            q_prev_close = quote.get("previous_close")
            q_vol = quote.get("volume", 0)
            q_time = quote.get("datetime", "N/A")
            q_is_open = quote.get("is_market_open", False)

            # Format quote details for display.
            market_badge = (
                '<span style="background-color: #065f46; color: #34d399; font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; font-weight: 600;">Market Open</span>'
                if q_is_open else
                '<span style="background-color: #374151; color: #9ca3af; font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; font-weight: 600;">Market Closed</span>'
            )
            chg_color = "#22c55e" if q_change >= 0 else "#ef4444"
            chg_sign = "+" if q_change >= 0 else ""

            vol_fmt = f"{q_vol:,}" if q_vol else "N/A"
            open_fmt = f"${q_open:,.2f}" if q_open else "N/A"
            high_fmt = f"${q_high:,.2f}" if q_high else "N/A"
            low_fmt = f"${q_low:,.2f}" if q_low else "N/A"
            prev_fmt = f"${q_prev_close:,.2f}" if q_prev_close else "N/A"

            st.markdown(
                f"""
                <div class="quote-box">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid #1f2937; padding-bottom: 8px;">
                        <div>
                            <span style="font-size: 1.1rem; font-weight: 700; color: #f8fafc;">Latest Market Quote</span>
                            <span style="margin-left: 10px;">{market_badge}</span>
                        </div>
                        <div style="font-size: 0.8rem; color: #94a3b8;">
                            Last Updated: <strong style="color: #cbd5e1;">{q_time}</strong>
                        </div>
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 24px; align-items: baseline;">
                        <div>
                            <span style="font-size: 2.2rem; font-weight: 800; color: #f8fafc;">${q_price:,.2f}</span>
                            <span style="font-size: 1.1rem; font-weight: 700; color: {chg_color}; margin-left: 8px;">
                                {chg_sign}${q_change:,.2f} ({chg_sign}{q_pct:.2f}%)
                            </span>
                        </div>
                        <div style="display: flex; gap: 16px; font-size: 0.85rem; color: #94a3b8; align-items: center;">
                            <div>Open: <strong style="color: #e2e8f0;">{open_fmt}</strong></div>
                            <div>High: <strong style="color: #e2e8f0;">{high_fmt}</strong></div>
                            <div>Low: <strong style="color: #e2e8f0;">{low_fmt}</strong></div>
                            <div>Prev Close: <strong style="color: #e2e8f0;">{prev_fmt}</strong></div>
                            <div>Volume: <strong style="color: #e2e8f0;">{vol_fmt}</strong></div>
                            <div>Exchange: <strong style="color: #e2e8f0;">{quote.get('exchange', exchange)}</strong></div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# Run the pipeline
if trigger_pipeline and symbol:
    with st.spinner(f"Executing ETL Pipeline for {symbol} ({mode})..."):
        try:
            if mode == "API":
                raw_df = fetch_cached_api_historical(symbol, TWELVE_DATA_API_KEY)
                actual_source = "Twelve Data API"
            else:
                raw_df = extractor.extract_from_csv(symbol)
                actual_source = "Local CSV"

            # Transform the extracted rows.
            clean_df = transformer.transform(raw_df)

            # Calculate derived metrics.
            enriched_df = calculate_metrics(clean_df)

            # Write the results to PostgreSQL.
            load_result = loader.load_stock_data(symbol, enriched_df, company_name=company_name)

            st.success(
                f"Pipeline completed. Stored {load_result['prices_loaded']} records in PostgreSQL "
                f"via {actual_source}."
            )
        except Exception as exc:
            st.error(f"ETL Ingestion notice: {exc}")


# Read warehouse data and render the dashboard
if not symbol:
    st.info(
        "Select a company or ticker in the sidebar to view its quote and historical data."
    )
else:
    df_stock = loader.query_stock_data(symbol, start_date=start_date, end_date=end_date)

    # Seed the warehouse from the bundled CSV when needed.
    if df_stock.empty:
        with st.spinner(f"Initializing warehouse records for '{symbol}'..."):
            try:
                if mode == "CSV":
                    raw_df = extractor.extract_from_csv(symbol)
                else:
                    raw_df = fetch_cached_api_historical(symbol, TWELVE_DATA_API_KEY)
                clean_df = transformer.transform(raw_df)
                enriched_df = calculate_metrics(clean_df)
                loader.load_stock_data(symbol, enriched_df, company_name=company_name)
                df_stock = loader.query_stock_data(symbol, start_date=start_date, end_date=end_date)
            except Exception as err:
                if mode == "API":
                    st.warning(f"Could not fetch historical API records for '{symbol}'. ({err})")
                else:
                    st.warning(f"Could not load CSV data for '{symbol}': {err}")

    if not df_stock.empty:
        # KPI cards
        render_metric_cards(df_stock)

        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

        # Charts
        tab_overview, tab_candlestick, tab_volume, tab_returns, tab_volatility = st.tabs([
            "📊 Candlestick & Moving Averages",
            "📈 Historical Closing Price",
            "📦 Trading Volume",
            "📉 Daily Returns",
            "⚡ Rolling Volatility",
        ])

        with tab_overview:
            fig_candle = plot_price_and_candlestick(df_stock, symbol)
            st.plotly_chart(fig_candle, use_container_width=True)

        with tab_candlestick:
            fig_close = plot_historical_close(df_stock, symbol)
            st.plotly_chart(fig_close, use_container_width=True)

        with tab_volume:
            fig_vol = plot_volume(df_stock, symbol)
            st.plotly_chart(fig_vol, use_container_width=True)

        with tab_returns:
            fig_returns = plot_daily_returns(df_stock, symbol)
            st.plotly_chart(fig_returns, use_container_width=True)

        with tab_volatility:
            fig_volatility = plot_volatility(df_stock, symbol)
            st.plotly_chart(fig_volatility, use_container_width=True)

        st.markdown("---")

        # Recent records
        st.subheader(f"📋 Warehouse Records for {symbol} ({len(df_stock)} Days)")
        cols_display = [
            "trade_date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "daily_change",
            "daily_return_pct",
            "moving_avg_7",
            "moving_avg_30",
            "volatility",
        ]
        available_cols = [c for c in cols_display if c in df_stock.columns]
        st.dataframe(
            df_stock[available_cols].tail(15).sort_values(by="trade_date", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(f"No records available in warehouse for '{symbol}'. Click **Run ETL Ingestion** to populate.")
