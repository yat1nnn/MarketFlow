import datetime
from typing import Dict, Any, Optional
import streamlit as st

from src.config import CSV_SAMPLE_STOCKS, DEFAULT_SYMBOL, mask_key, TWELVE_DATA_API_KEY
from src.database import check_connection
from src.extractor import StockDataExtractor


@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_search_results(query: str, api_key: str):
    """Cache company search results for one hour."""
    extractor = StockDataExtractor()
    return extractor.search_symbols(query)


@st.cache_data(ttl=300, show_spinner=False)
def get_cached_api_usage(api_key: str):
    """Cache usage information for five minutes."""
    extractor = StockDataExtractor()
    return extractor.get_api_usage()


def render_sidebar() -> Dict[str, Any]:
    """Render the sidebar controls for the selected data source."""
    st.sidebar.markdown(
        """
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 2px;">
            <span style="font-size: 1.6rem;">📈</span>
            <span style="font-size: 1.4rem; font-weight: 700; color: #f8fafc;">MarketFlow</span>
        </div>
        <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 12px;">Stock data and analytics</div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")

    # Choose the data source.
    st.sidebar.subheader("📥 Data Source")
    data_source_options = ["CSV — Local Sample Data", "API — Twelve Data"]

    # Remember the last selected source.
    if "data_source_mode" not in st.session_state:
        st.session_state["data_source_mode"] = data_source_options[0]
    if "prev_data_source_mode" not in st.session_state:
        st.session_state["prev_data_source_mode"] = st.session_state["data_source_mode"]

    data_source = st.sidebar.radio(
        "Select data source",
        data_source_options,
        index=0 if st.session_state["data_source_mode"] == data_source_options[0] else 1,
        label_visibility="collapsed",
    )

    is_csv_mode = (data_source == "CSV — Local Sample Data")
    is_api_mode = not is_csv_mode

    # Clear state that belongs to the other source.
    if data_source != st.session_state["prev_data_source_mode"]:
        if is_csv_mode:
            # Switching to CSV clears the API search state.
            st.session_state["api_search_query"] = ""
            st.session_state["api_search_results"] = []
            st.session_state["api_selected_stock"] = None
            st.session_state["api_selected_symbol"] = None
            st.session_state["api_quote_data"] = None
        else:
            # Switching to API clears the CSV selection.
            st.session_state["csv_selected_stock"] = None

        st.session_state["data_source_mode"] = data_source
        st.session_state["prev_data_source_mode"] = data_source
        st.rerun()

    st.sidebar.markdown("---")

    # Values returned to the main page.
    selected_symbol = "AAPL"
    selected_company_name = "Apple Inc."
    selected_exchange = "NASDAQ"
    selected_country = "United States"
    refresh_quote_triggered = False

    # Render controls for the selected source only.
    if is_csv_mode:
        # CSV mode uses the stocks bundled with the project.
        st.sidebar.subheader("Stock Selection")
        csv_options = list(CSV_SAMPLE_STOCKS.keys())

        if "csv_selected_stock" not in st.session_state or st.session_state["csv_selected_stock"] not in csv_options:
            st.session_state["csv_selected_stock"] = DEFAULT_SYMBOL

        selected_symbol = st.sidebar.selectbox(
            "Select Stock",
            options=csv_options,
            index=csv_options.index(st.session_state["csv_selected_stock"]),
            format_func=lambda s: f"{s} — {CSV_SAMPLE_STOCKS.get(s, '')}",
            key="csv_stock_selector",
        )
        st.session_state["csv_selected_stock"] = selected_symbol
        selected_company_name = CSV_SAMPLE_STOCKS.get(selected_symbol, selected_symbol)

        st.sidebar.caption("📦 Using preloaded local warehouse/sample dataset.")

    else:
        # API mode uses Twelve Data symbol search.
        st.sidebar.subheader("Search Stock / Company")

        # Start with a clean search state.
        if "api_search_query" not in st.session_state:
            st.session_state["api_search_query"] = ""
        if "api_search_results" not in st.session_state:
            st.session_state["api_search_results"] = []
        if "api_selected_stock" not in st.session_state:
            st.session_state["api_selected_stock"] = None
        if "api_selected_symbol" not in st.session_state:
            st.session_state["api_selected_symbol"] = None

        search_query = st.sidebar.text_input(
            "Search company name or symbol...",
            value=st.session_state["api_search_query"],
            placeholder="e.g. Apple, AAPL, Tesla, NVDA",
            help="Type at least 2 characters. Searches Twelve Data API dynamically.",
            key="api_search_input_box",
        )
        st.session_state["api_search_query"] = search_query

        # Search after at least two characters are entered.
        if len(search_query.strip()) >= 2:
            if not TWELVE_DATA_API_KEY or TWELVE_DATA_API_KEY == "your_twelve_data_api_key_here":
                st.sidebar.error("⚠️ Twelve Data API key is not configured in .env.")
            else:
                with st.sidebar.status("Searching companies...", expanded=False):
                    try:
                        results = get_cached_search_results(search_query.strip(), TWELVE_DATA_API_KEY)
                        st.session_state["api_search_results"] = results
                    except Exception as err:
                        st.sidebar.warning(f"Search error: {err}")
                        st.session_state["api_search_results"] = []

                results = st.session_state["api_search_results"]
                if results:
                    st.sidebar.markdown(f"**Results ({len(results)} found):**")
                    options_map = {res["display"]: res for res in results}
                    selected_display = st.sidebar.selectbox(
                        "Choose Instrument",
                        options=list(options_map.keys()),
                        key="api_instrument_select",
                    )
                    chosen_res = options_map[selected_display]
                    st.session_state["api_selected_stock"] = chosen_res
                    st.session_state["api_selected_symbol"] = chosen_res["symbol"]
                else:
                    st.sidebar.info(f"No companies found for '{search_query}'.")
        elif len(search_query.strip()) == 1:
            st.sidebar.caption("Type at least 2 characters to search...")

        # Show the current API selection.
        if st.session_state.get("api_selected_stock"):
            chosen = st.session_state["api_selected_stock"]
            selected_symbol = chosen["symbol"]
            selected_company_name = chosen["company_name"]
            selected_exchange = chosen.get("exchange", "NASDAQ")
            selected_country = chosen.get("country", "United States")

            st.sidebar.success(
                f"**Selected Stock:**\n\n**{selected_company_name} ({selected_symbol})**\n\n"
                f"{selected_exchange} · {selected_country}"
            )
            refresh_quote_triggered = st.sidebar.button("🔄 Refresh Quote", use_container_width=True)
        else:
            # Nothing selected yet.
            selected_symbol = None
            selected_company_name = None

    st.sidebar.markdown("---")

    # Run ingestion
    trigger_pipeline = st.sidebar.button("⚡ Run ETL Ingestion", type="primary", use_container_width=True)

    # Date range
    st.sidebar.subheader("📅 Date Range Filter")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime.date(2026, 1, 1))
    with col2:
        end_date = st.date_input("End Date", value=datetime.date.today())

    if start_date > end_date:
        st.sidebar.error("Start date must be before end date.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔌 System Health")

    # Database status
    db_ok, db_msg = check_connection()
    if db_ok:
        st.sidebar.success("● Database: PostgreSQL Connected", icon="✅")
    else:
        st.sidebar.error("● Database: Disconnected", icon="❌")

    # API usage
    if is_api_mode:
        st.sidebar.markdown("---")
        st.sidebar.subheader("💳 Twelve Data API")

        masked_key = mask_key(TWELVE_DATA_API_KEY)
        if TWELVE_DATA_API_KEY and TWELVE_DATA_API_KEY != "your_twelve_data_api_key_here":
            st.sidebar.caption(f"API Key: `{masked_key}`")
            # Show usage only when the API provides it.
            usage = get_cached_api_usage(TWELVE_DATA_API_KEY)
            if usage.get("available"):
                used = usage.get("used", 0)
                limit = usage.get("limit", 0)
                remaining = usage.get("remaining", 0)
                st.sidebar.info(
                    f"**API Credits**\n\n"
                    f"• Used: **{used}**\n"
                    f"• Remaining: **{remaining}**\n"
                    f"• Daily Limit: **{limit}**",
                    icon="📊"
                )
            else:
                st.sidebar.info(
                    "**API Credits**\n\nUsage information unavailable",
                    icon="ℹ️"
                )
            st.sidebar.caption("🔒 *API requests are cached to conserve daily credits.*")
        else:
            st.sidebar.warning("API Key: Not Configured\n\n*(Please set TWELVE_DATA_API_KEY in .env)*")

    return {
        "mode": "CSV" if is_csv_mode else "API",
        "symbol": selected_symbol,
        "company_name": selected_company_name,
        "exchange": selected_exchange,
        "country": selected_country,
        "start_date": start_date,
        "end_date": end_date,
        "trigger_pipeline": trigger_pipeline,
        "refresh_quote": refresh_quote_triggered,
    }
