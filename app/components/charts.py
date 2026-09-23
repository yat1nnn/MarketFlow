import pandas as pd
import plotly.graph_objects as go


def plot_price_and_candlestick(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Build the main price chart with the two moving averages."""
    fig = go.Figure()

    # OHLC candlesticks
    fig.add_trace(
        go.Candlestick(
            x=df["trade_date"],
            open=df["open_price"],
            high=df["high_price"],
            low=df["low_price"],
            close=df["close_price"],
            name="OHLC Price",
            increasing_line_color="#22c55e",
            increasing_fillcolor="#22c55e",
            decreasing_line_color="#ef4444",
            decreasing_fillcolor="#ef4444",
        )
    )

    # Short-term moving average
    if "moving_avg_7" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["trade_date"],
                y=df["moving_avg_7"],
                mode="lines",
                name="7-Day SMA",
                line=dict(color="#f59e0b", width=1.8),
            )
        )

    # Longer moving average
    if "moving_avg_30" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["trade_date"],
                y=df["moving_avg_30"],
                mode="lines",
                name="30-Day SMA",
                line=dict(color="#3b82f6", width=2.0),
            )
        )

    fig.update_layout(
        title=dict(text=f"<b>{symbol} Price Action & Trend (OHLC + 7D/30D SMAs)</b>", font=dict(color="#f8fafc", size=16)),
        xaxis=dict(title="Date", gridcolor="#1e293b", color="#94a3b8"),
        yaxis=dict(title="Price (USD)", gridcolor="#1e293b", color="#94a3b8"),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        height=500,
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#cbd5e1")),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )

    return fig


def plot_historical_close(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Build the historical closing-price chart."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["trade_date"],
            y=df["close_price"],
            mode="lines",
            name="Close Price",
            line=dict(color="#3b82f6", width=2.2),
            fill="tozeroy",
            fillcolor="rgba(59, 130, 246, 0.12)",
        )
    )

    fig.update_layout(
        title=dict(text=f"<b>{symbol} Historical Closing Price</b>", font=dict(color="#f8fafc", size=16)),
        xaxis=dict(title="Date", gridcolor="#1e293b", color="#94a3b8"),
        yaxis=dict(title="Close Price (USD)", gridcolor="#1e293b", color="#94a3b8"),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        hovermode="x unified",
    )
    return fig


def plot_volume(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Build a daily trading-volume chart."""
    colors = [
        "#22c55e" if ret >= 0 else "#ef4444"
        for ret in df.get("daily_return_pct", [0] * len(df))
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["trade_date"],
            y=df["volume"],
            name="Trading Volume",
            marker_color=colors,
        )
    )

    fig.update_layout(
        title=dict(text=f"<b>{symbol} Daily Trading Volume</b>", font=dict(color="#f8fafc", size=16)),
        xaxis=dict(title="Date", gridcolor="#1e293b", color="#94a3b8"),
        yaxis=dict(title="Shares Traded", gridcolor="#1e293b", color="#94a3b8"),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        hovermode="x unified",
    )
    return fig


def plot_daily_returns(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Build a daily return chart around the zero line."""
    colors = [
        "#22c55e" if ret >= 0 else "#ef4444"
        for ret in df["daily_return_pct"]
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["trade_date"],
            y=df["daily_return_pct"],
            name="Daily Return (%)",
            marker_color=colors,
        )
    )

    # A zero line makes positive and negative returns easier to read.
    fig.add_hline(y=0.0, line_dash="dash", line_color="#64748b", line_width=1.2)

    fig.update_layout(
        title=dict(text=f"<b>{symbol} Daily Return Percentage (%)</b>", font=dict(color="#f8fafc", size=16)),
        xaxis=dict(title="Date", gridcolor="#1e293b", color="#94a3b8"),
        yaxis=dict(title="Return (%)", gridcolor="#1e293b", color="#94a3b8"),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        hovermode="x unified",
    )
    return fig


def plot_volatility(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Build the 30-day rolling volatility chart."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["trade_date"],
            y=df["volatility"],
            mode="lines",
            name="30D Volatility",
            line=dict(color="#a855f7", width=2.2),
            fill="tozeroy",
            fillcolor="rgba(168, 85, 247, 0.12)",
        )
    )

    fig.update_layout(
        title=dict(text=f"<b>{symbol} 30-Day Rolling Volatility (Daily Return Std. Dev.)</b>", font=dict(color="#f8fafc", size=16)),
        xaxis=dict(title="Date", gridcolor="#1e293b", color="#94a3b8"),
        yaxis=dict(title="Volatility (%)", gridcolor="#1e293b", color="#94a3b8"),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        hovermode="x unified",
    )
    return fig
