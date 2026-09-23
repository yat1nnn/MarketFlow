# MarketFlow — Market Data Engineering Platform

An end-to-end market data engineering project built with Python, Twelve Data, PostgreSQL, Pandas, SQLAlchemy, Streamlit, Plotly, and Pytest.

MarketFlow ingests stock market data from an external API or local CSV data, cleans and standardizes the incoming records, calculates time-series metrics, loads the results into PostgreSQL, and exposes the stored data through a Streamlit analytics dashboard.

---

## 🚀 Project Overview

MarketFlow demonstrates a complete batch-oriented data pipeline:

```text
Twelve Data API ─────┐
                     │
                     ▼
               ┌───────────┐
Local CSV ────►│ Extraction│
               └─────┬─────┘
                     │
                     ▼
               ┌───────────┐
               │ Cleaning  │
               │ &         │
               │ Transform │
               └─────┬─────┘
                     │
                     ▼
               ┌───────────┐
               │  Metrics  │
               │ Calculation│
               └─────┬─────┘
                     │
                     ▼
               ┌───────────┐
               │PostgreSQL │
               │ Warehouse │
               └─────┬─────┘
                     │
                     ▼
               ┌───────────┐
               │ Streamlit │
               │ Dashboard │
               └───────────┘
```

The project is designed to demonstrate practical Data Engineering concepts rather than only dashboard development.

---

## 🧰 Tech Stack

| Technology | Purpose |
|---|---|
| Python | Pipeline and application logic |
| Pandas | Data cleaning and transformation |
| Twelve Data API | External market-data source |
| PostgreSQL | Persistent data storage |
| SQLAlchemy | Database interaction and ORM |
| Streamlit | Interactive application/dashboard |
| Plotly | Data visualization |
| Pytest | Automated testing |
| python-dotenv | Environment configuration |

---

## 🔄 Data Pipeline

The pipeline follows these stages:

### 1. Extraction

Market data can be obtained from:

- Twelve Data API
- Bundled local CSV sample data

The CSV source also provides an offline/fallback mode when the API is unavailable.

### 2. Cleaning & Standardization

Incoming records are cleaned before they are loaded into PostgreSQL.

The transformation layer handles tasks such as:

- Standardizing column names
- Parsing dates
- Converting numeric fields
- Handling invalid values
- Removing duplicate observations
- Validating OHLC data
- Handling volume values
- Sorting observations by date

### 3. Metric Calculation

The pipeline calculates:

- Daily change
- Daily return percentage
- 7-day simple moving average
- 30-day simple moving average
- 30-day rolling volatility

### 4. Loading

Cleaned stock data and calculated metrics are stored in PostgreSQL.

The loader uses an upsert strategy based on:

```text
(stock_id, trade_date)
```

This prevents repeated pipeline runs from creating duplicate daily observations.

### 5. Analytics

The Streamlit application reads the stored data and provides:

- Company/ticker selection
- Market data exploration
- Price charts
- Calculated metrics
- Pipeline status information

---

## 🗄️ Database Design

MarketFlow uses PostgreSQL with three primary tables.

### `stocks`

Stores stock identity information:

```text
id
symbol
company_name
```

### `stock_prices`

Stores daily OHLCV market data:

```text
stock_id
trade_date
open_price
high_price
low_price
close_price
volume
```

### `daily_metrics`

Stores calculated analytical metrics:

```text
stock_id
trade_date
daily_change
daily_return_pct
moving_avg_7
moving_avg_30
volatility
```

Both `stock_prices` and `daily_metrics` use:

```text
(stock_id, trade_date)
```

as the unique key for daily observations.

---

## 🔁 Idempotent Loading

A key Data Engineering concept demonstrated by MarketFlow is idempotent loading.

If the same daily observation is processed multiple times, the database does not create duplicate rows. Instead, PostgreSQL updates the existing observation through the project's upsert logic.

Conceptually:

```text
First run
    ↓
Load 130 rows
    ↓
PostgreSQL

Second run with same data
    ↓
Upsert
    ↓
Existing observations updated
    ↓
No duplicate daily rows
```

This makes the loader safe to run again when historical data is refreshed or new values arrive.

---

## ✅ Data Quality

The transformation layer performs validation and cleanup before database loading.

The project handles:

- Date parsing
- Numeric conversion
- Missing/invalid values
- Duplicate observations
- OHLC consistency
- Volume validation
- Standardized column naming

This keeps the database layer focused on cleaned and structured records.

---

## 📊 Sample Dataset

The repository includes local sample data for:

- AAPL — Apple Inc.
- MSFT — Microsoft Corporation
- GOOGL — Alphabet Inc.
- AMZN — Amazon.com Inc.

The bundled sample contains:

```text
520 total rows
130 rows per symbol
```

covering:

```text
March 23, 2026 → September 18, 2026
```

The local CSV mode allows the application to be used without a Twelve Data API key.

---

## 🖥️ Application

MarketFlow includes a Streamlit application with:

### Data Explorer

Explore stored stock data and visualize market information.

### Pipeline Status

View pipeline-related status information through the Streamlit interface.

### API Mode

Search for companies/tickers through Twelve Data.

The API workflow requires at least two characters in the search field and uses the selected ticker for quote and historical-data requests.

### CSV Mode

Use:

```text
CSV — Local Sample Data
```

to work with the bundled dataset without requiring an API key.

The application also caches search results, quotes, and historical data for short periods to reduce repeated API calls.

---

## 🧪 Testing

The project includes **31 automated tests** covering:

- API client behavior
- API error handling
- Data extraction
- Data transformations
- Metric calculations
- Database loading
- Repeated/idempotent loads

Run the test suite with:

```powershell
python -m pytest
```

The API tests use mocked responses, so they do not require a real Twelve Data API key or API credits.

Expected result:

```text
31 passed
```

---

## 📁 Project Structure

```text
MarketFlow/
│
├── app/
│   ├── components/
│   │   ├── charts.py
│   │   ├── metrics_cards.py
│   │   └── sidebar.py
│   │
│   ├── pages/
│   │   ├── 1_Data_Explorer.py
│   │   └── 2_Pipeline_Status.py
│   │
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

---

## ⚙️ Setup

### 1. Clone the repository

```powershell
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd MarketFlow
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Create the PostgreSQL database

Create a PostgreSQL database named:

```text
marketflow
```

### 5. Configure environment variables

Create a local `.env` file from `.env.example`.

Example:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/marketflow
TWELVE_DATA_API_KEY=your_twelve_data_api_key_here
```

**Do not commit `.env` or real API keys/passwords to GitHub.**

### 6. Run the project

```powershell
python run_marketflow.py
```

Or launch Streamlit directly:

```powershell
python -m streamlit run app\streamlit_app.py
```

---

## 🔐 Security Notes

MarketFlow is designed to load credentials through environment variables rather than hard-coding them into application code.

Recommended repository practices:

- Keep `.env` out of version control
- Commit `.env.example` instead of real secrets
- Never expose API keys in source code
- Never commit database passwords
- Use parameterized database queries
- Use API request timeouts
- Rotate credentials immediately if a secret is accidentally exposed

For local development, `.env` should remain a local-only file.

---

## 📈 Data Engineering Concepts Demonstrated

This project demonstrates practical concepts relevant to Data Engineering:

- API-based data ingestion
- Batch data processing
- ETL pipeline design
- Data cleaning and standardization
- Data validation
- Data transformation
- Time-series metric calculation
- Relational data modeling
- PostgreSQL
- SQLAlchemy
- Upsert-based loading
- Idempotent processing
- Automated testing
- Offline/fallback ingestion
- Analytics data presentation

---

## 🎯 Project Scope

MarketFlow is primarily a portfolio and learning project focused on demonstrating core Data Engineering skills through a complete local data pipeline.

It is **not presented as a production cloud deployment**. Advanced production infrastructure such as cloud orchestration, distributed processing, managed warehouses, and production monitoring is outside the current project scope.

---

## 🔮 Future Improvements

Potential next steps for the project include:

- Docker and Docker Compose
- Incremental data ingestion
- Pipeline run/audit metadata
- More extensive data-quality reporting
- Workflow orchestration with Airflow, Prefect, or Dagster
- Database migrations with Alembic
- GitHub Actions CI/CD
- Dependency/security scanning
- Production monitoring and alerting
- Cloud deployment
- Data warehouse integration

These improvements would extend the current local ETL architecture toward a more production-oriented Data Engineering system.

---

## 👨‍💻 Author

**Yatin**

Built as a Data Engineering portfolio project focused on market-data ingestion, transformation, storage, testing, and analytics.
