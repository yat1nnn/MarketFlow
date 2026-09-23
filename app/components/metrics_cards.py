import pandas as pd
import streamlit as st


def render_metric_cards(df: pd.DataFrame) -> None:
    """Render the six summary cards shown above the charts."""
    if df is None or df.empty:
        st.warning("No data available to display metrics.")
        return

    latest = df.iloc[-1]

    # Read the latest row from the warehouse query.
    latest_price = float(latest.get("close_price", 0.0))
    daily_change = float(latest.get("daily_change", 0.0)) if pd.notna(latest.get("daily_change")) else 0.0
    daily_return = float(latest.get("daily_return_pct", 0.0)) if pd.notna(latest.get("daily_return_pct")) else 0.0
    volume = int(latest.get("volume", 0)) if pd.notna(latest.get("volume")) else 0
    ma_7 = latest.get("moving_avg_7", None)
    ma_30 = latest.get("moving_avg_30", None)

    # Use a compact format for large volumes.
    if volume >= 1_000_000_000:
        vol_str = f"{volume / 1_000_000_000:.2f}B"
    elif volume >= 1_000_000:
        vol_str = f"{volume / 1_000_000:.2f}M"
    elif volume >= 1_000:
        vol_str = f"{volume / 1_000:.2f}K"
    else:
        vol_str = f"{volume:,}"

    # Format the small change indicator shown under the value.
    def get_delta_html(val: float, is_pct: bool = False) -> str:
        if val > 0:
            color = "#22c55e"   # Positive value
            symbol = "▲ +"
        elif val < 0:
            color = "#ef4444"   # Negative value
            symbol = "▼ "
        else:
            color = "#94a3b8"   # No change
            symbol = "➖ "
        
        formatted = f"{val:.2f}%" if is_pct else f"${abs(val):,.2f}"
        return f'<span style="color: {color}; font-size: 0.85rem; font-weight: 600;">{symbol}{formatted}</span>'

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    card_style = """
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 12px 14px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.25);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 96px;
    """
    label_style = "color: #94a3b8; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;"
    val_style = "color: #f8fafc; font-size: 1.45rem; font-weight: 700; line-height: 1.2;"

    with col1:
        st.markdown(
            f"""
            <div style="{card_style}">
                <div style="{label_style}">Latest Price</div>
                <div style="{val_style}">${latest_price:,.2f}</div>
                <div style="font-size: 0.75rem; color: #64748b;">Closing Quote</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div style="{card_style}">
                <div style="{label_style}">Daily Change</div>
                <div style="{val_style}">${daily_change:+,.2f}</div>
                <div>{get_delta_html(daily_change, is_pct=False)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div style="{card_style}">
                <div style="{label_style}">Daily Return</div>
                <div style="{val_style}">{daily_return:+.2f}%</div>
                <div>{get_delta_html(daily_return, is_pct=True)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div style="{card_style}">
                <div style="{label_style}">Trading Volume</div>
                <div style="{val_style}">{vol_str}</div>
                <div style="font-size: 0.75rem; color: #64748b;">Shares Traded</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col5:
        ma7_str = f"${ma_7:,.2f}" if (ma_7 is not None and pd.notna(ma_7)) else "N/A"
        ma7_sub = f"${latest_price - ma_7:+.2f} vs MA" if (ma_7 is not None and pd.notna(ma_7)) else "Short-term trend"
        st.markdown(
            f"""
            <div style="{card_style}">
                <div style="{label_style}">7D Moving Avg</div>
                <div style="{val_style}">{ma7_str}</div>
                <div style="font-size: 0.75rem; color: #f59e0b;">{ma7_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col6:
        ma30_str = f"${ma_30:,.2f}" if (ma_30 is not None and pd.notna(ma_30)) else "N/A"
        ma30_sub = f"${latest_price - ma_30:+.2f} vs MA" if (ma_30 is not None and pd.notna(ma_30)) else "Medium-term trend"
        st.markdown(
            f"""
            <div style="{card_style}">
                <div style="{label_style}">30D Moving Avg</div>
                <div style="{val_style}">{ma30_str}</div>
                <div style="font-size: 0.75rem; color: #3b82f6;">{ma30_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
