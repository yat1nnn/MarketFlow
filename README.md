# MarketFlow --- Market Data & Analytics Platform

MarketFlow is a stock market data application built with Python, Twelve
Data, PostgreSQL, Pandas, SQLAlchemy, Streamlit, Plotly, and Pytest.

The project takes market data from an API or a local CSV file, cleans
it, calculates a few time-series metrics, stores the results in
PostgreSQL, and displays the data in a Streamlit dashboard.

## What it does

-   Search for companies and tickers through Twelve Data.
-   Pull the latest quote and daily historical data.
-   Use the bundled CSV when working offline or when the API cannot be
    used.
-   Clean and standardize incoming rows before loading them.
-   Calculate daily change, daily return, 7-day average, 30-day average,
    and rolling volatility.
-   Store stock, price, and metric data in PostgreSQL.
-   Use upserts on `(stock_id, trade_date)` so a repeated load does not
    create duplicate daily rows.
-   Browse the stored data and view charts in Streamlit.

## Data flow

``` text
Twelve Data / Local CSV
          |
          v
      Extraction
          |
          v
  Cleaning & standardization
          |
          v
      Metric calculation
          |
          v
       PostgreSQL
          |
          v
    Streamlit dashboard
```

## Database tables

### `stocks`

Stores the stock symbol and company name.

### `stock_prices`

Stores the daily OHLCV data for each stock.

### `daily_metrics`

Stores the calculated daily change, return percentage, moving averages,
and volatility.

Both `stock_prices` and `daily_metrics` use `(stock_id, trade_date)` as
a unique key for daily observations.

## Local sample data

The repository includes sample data for:

-   AAPL --- Apple Inc.
-   MSFT --- Microsoft Corporation
-   GOOGL --- Alphabet Inc.
-   AMZN --- Amazon.com Inc.

The sample file contains 520 rows in total, with 130 rows per symbol,
covering March 23, 2026 through September 18, 2026.

## Project layout

``` text
MarketFlow/
|
├── app/
│   ├── components/
│   │   ├── charts.py
│   │   ├── metrics_cards.py
│   │   └── sidebar.py
│   ├── pages/
│   │   ├── 1_Data_Explorer.py
│   │   └── 2_Pipeline_Status.py
│   └── streamlit_app.py
│
├── data/
│   └── sample_stock_data.csv
│
├── src/
│   ├── api_client.py
│   ├── config.py
│   ├── database.py
│   ├── extractor.py
│   ├── loader.py
│   ├── metrics.py
│   └── transformer.py
│
├── tests/
│   ├── test_extractor.py
│   ├── test_loader.py
│   ├── test_metrics.py
│   └── test_transformer.py
│
├── .env.example
├── pytest.ini
├── README.md
├── requirements.txt
└── run_marketflow.py
```

## Setup

### 1. Create the database

Create a PostgreSQL database named `marketflow`.

### 2. Install dependencies

From the project directory:

``` powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Configure the environment

Create a local `.env` file from `.env.example` and set your PostgreSQL
connection string and Twelve Data key.

``` env
DATABASE_URL=postgresql://postgres:password@localhost:5432/marketflow
TWELVE_DATA_API_KEY=your_twelve_data_api_key_here
```

### 4. Run MarketFlow

``` powershell
python run_marketflow.py
```

Or run Streamlit directly:

``` powershell
python -m streamlit run app\streamlit_app.py
```

## Using the app

### CSV mode

Choose `CSV — Local Sample Data` in the sidebar and select one of the
bundled stocks. This mode does not need an API key.

### API mode

Choose `API — Twelve Data`, type at least two characters in the search
box, and select a company from the results. MarketFlow then uses the
returned ticker for the quote and historical data requests.

The app caches search results, quotes, and historical data for short
periods to avoid repeated API calls.

## Metrics

The transformation layer calculates:

-   Daily change
-   Daily return percentage
-   7-day simple moving average
-   30-day simple moving average
-   30-day rolling volatility

## Testing

The project has 31 automated tests covering the API client, extraction,
transformations, metrics, and database loading.

Run them with:

``` powershell
python -m pytest
```

The API tests use mocked responses, so they do not require a real Twelve
Data key or spend API credits.

## Notes on repeated loads

A daily stock observation is identified by the stock and trading date.
When the same observation is loaded again, PostgreSQL updates the
existing row instead of inserting another one.

That makes the loader safe to run again when historical data is
refreshed or new values arrive.

## Author

**Yatin**
