import logging
from typing import Dict, Any, Optional, List
import pandas as pd
from sqlalchemy import select, and_, text
from sqlalchemy.orm import Session

from src.database import Stock, StockPrice, DailyMetric, get_engine, get_session, init_db
from src.config import CSV_SAMPLE_STOCKS

logger = logging.getLogger(__name__)


class StockDataLoader:
    """Load cleaned prices and metrics into the database."""

    def __init__(self, engine=None):
        self.engine = engine or get_engine()
        # Create tables when they are not already present.
        init_db(self.engine)

    def get_or_create_stock(self, session: Session, symbol: str, company_name: Optional[str] = None) -> Stock:
        """Get a stock row, creating it when needed."""
        clean_symbol = symbol.strip().upper()
        stock = session.execute(select(Stock).where(Stock.symbol == clean_symbol)).scalar_one_or_none()

        if not stock:
            name = company_name or CSV_SAMPLE_STOCKS.get(clean_symbol, f"{clean_symbol} Corporation")
            stock = Stock(symbol=clean_symbol, company_name=name)
            session.add(stock)
            session.flush()
            logger.info(f"Created new Stock entry for symbol '{clean_symbol}' (id={stock.id}).")
        elif company_name and stock.company_name != company_name:
            stock.company_name = company_name
            session.flush()

        return stock

    def load_prices_idempotent(self, session: Session, stock_id: int, df: pd.DataFrame) -> int:
        """Insert or update daily price rows without duplicates."""
        if df.empty:
            return 0

        records = []
        for _, row in df.iterrows():
            records.append({
                "stock_id": stock_id,
                "trade_date": row["trade_date"],
                "open_price": float(row["open_price"]),
                "high_price": float(row["high_price"]),
                "low_price": float(row["low_price"]),
                "close_price": float(row["close_price"]),
                "volume": int(row["volume"]),
            })

        dialect_name = self.engine.dialect.name
        if dialect_name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(StockPrice).values(records)
            stmt = stmt.on_conflict_do_update(
                index_elements=["stock_id", "trade_date"],
                set_={
                    "open_price": stmt.excluded.open_price,
                    "high_price": stmt.excluded.high_price,
                    "low_price": stmt.excluded.low_price,
                    "close_price": stmt.excluded.close_price,
                    "volume": stmt.excluded.volume,
                },
            )
            session.execute(stmt)
        elif dialect_name == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            stmt = sqlite_insert(StockPrice).values(records)
            stmt = stmt.on_conflict_do_update(
                index_elements=["stock_id", "trade_date"],
                set_={
                    "open_price": stmt.excluded.open_price,
                    "high_price": stmt.excluded.high_price,
                    "low_price": stmt.excluded.low_price,
                    "close_price": stmt.excluded.close_price,
                    "volume": stmt.excluded.volume,
                },
            )
            session.execute(stmt)
        else:
            # Simple row-by-row fallback for other SQL dialects.
            for rec in records:
                existing = session.execute(
                    select(StockPrice).where(
                        and_(StockPrice.stock_id == rec["stock_id"], StockPrice.trade_date == rec["trade_date"])
                    )
                ).scalar_one_or_none()
                if existing:
                    existing.open_price = rec["open_price"]
                    existing.high_price = rec["high_price"]
                    existing.low_price = rec["low_price"]
                    existing.close_price = rec["close_price"]
                    existing.volume = rec["volume"]
                else:
                    session.add(StockPrice(**rec))

        return len(records)

    def load_metrics_idempotent(self, session: Session, stock_id: int, df: pd.DataFrame) -> int:
        """
        Load daily metrics with an upsert.
        """
        metric_cols = ["daily_change", "daily_return_pct", "moving_avg_7", "moving_avg_30", "volatility"]
        if df.empty or not any(col in df.columns for col in metric_cols):
            return 0

        records = []
        for _, row in df.iterrows():
            records.append({
                "stock_id": stock_id,
                "trade_date": row["trade_date"],
                "daily_change": float(row["daily_change"]) if pd.notna(row.get("daily_change")) else None,
                "daily_return_pct": float(row["daily_return_pct"]) if pd.notna(row.get("daily_return_pct")) else None,
                "moving_avg_7": float(row["moving_avg_7"]) if pd.notna(row.get("moving_avg_7")) else None,
                "moving_avg_30": float(row["moving_avg_30"]) if pd.notna(row.get("moving_avg_30")) else None,
                "volatility": float(row["volatility"]) if pd.notna(row.get("volatility")) else None,
            })

        dialect_name = self.engine.dialect.name
        if dialect_name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(DailyMetric).values(records)
            stmt = stmt.on_conflict_do_update(
                index_elements=["stock_id", "trade_date"],
                set_={
                    "daily_change": stmt.excluded.daily_change,
                    "daily_return_pct": stmt.excluded.daily_return_pct,
                    "moving_avg_7": stmt.excluded.moving_avg_7,
                    "moving_avg_30": stmt.excluded.moving_avg_30,
                    "volatility": stmt.excluded.volatility,
                },
            )
            session.execute(stmt)
        elif dialect_name == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            stmt = sqlite_insert(DailyMetric).values(records)
            stmt = stmt.on_conflict_do_update(
                index_elements=["stock_id", "trade_date"],
                set_={
                    "daily_change": stmt.excluded.daily_change,
                    "daily_return_pct": stmt.excluded.daily_return_pct,
                    "moving_avg_7": stmt.excluded.moving_avg_7,
                    "moving_avg_30": stmt.excluded.moving_avg_30,
                    "volatility": stmt.excluded.volatility,
                },
            )
            session.execute(stmt)
        else:
            for rec in records:
                existing = session.execute(
                    select(DailyMetric).where(
                        and_(DailyMetric.stock_id == rec["stock_id"], DailyMetric.trade_date == rec["trade_date"])
                    )
                ).scalar_one_or_none()
                if existing:
                    existing.daily_change = rec["daily_change"]
                    existing.daily_return_pct = rec["daily_return_pct"]
                    existing.moving_avg_7 = rec["moving_avg_7"]
                    existing.moving_avg_30 = rec["moving_avg_30"]
                    existing.volatility = rec["volatility"]
                else:
                    session.add(DailyMetric(**rec))

        return len(records)

    def load_stock_data(
        self,
        symbol: str,
        df: pd.DataFrame,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Load prices and metrics in one transaction."""
        clean_symbol = symbol.strip().upper()
        session = get_session(self.engine)

        try:
            stock = self.get_or_create_stock(session, clean_symbol, company_name)
            stock_id = stock.id

            prices_loaded = self.load_prices_idempotent(session, stock_id, df)
            metrics_loaded = self.load_metrics_idempotent(session, stock_id, df)

            session.commit()
            logger.info(f"Ingested {prices_loaded} prices and {metrics_loaded} metrics for {clean_symbol}.")
            return {
                "status": "success",
                "symbol": clean_symbol,
                "stock_id": stock_id,
                "prices_loaded": prices_loaded,
                "metrics_loaded": metrics_loaded,
            }
        except Exception as exc:
            session.rollback()
            logger.error(f"Transaction failed for symbol '{clean_symbol}': {exc}")
            raise
        finally:
            session.close()

    def query_stock_data(
        self,
        symbol: str,
        start_date=None,
        end_date=None
    ) -> pd.DataFrame:
        """Read price and metric data for one symbol."""
        clean_symbol = symbol.strip().upper()
        query = """
            SELECT 
                s.symbol,
                s.company_name,
                p.trade_date,
                p.open_price,
                p.high_price,
                p.low_price,
                p.close_price,
                p.volume,
                m.daily_change,
                m.daily_return_pct,
                m.moving_avg_7,
                m.moving_avg_30,
                m.volatility
            FROM stocks s
            JOIN stock_prices p ON s.id = p.stock_id
            LEFT JOIN daily_metrics m ON p.stock_id = m.stock_id AND p.trade_date = m.trade_date
            WHERE s.symbol = :symbol
        """
        params = {"symbol": clean_symbol}
        if start_date:
            query += " AND p.trade_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND p.trade_date <= :end_date"
            params["end_date"] = end_date

        query += " ORDER BY p.trade_date ASC"

        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params)

        if not df.empty:
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date

        return df

    def get_available_symbols(self) -> List[Dict[str, Any]]:
        """List stocks currently stored in the warehouse."""
        query = """
            SELECT 
                s.symbol,
                s.company_name,
                COUNT(p.id) as record_count,
                MIN(p.trade_date) as min_date,
                MAX(p.trade_date) as max_date
            FROM stocks s
            LEFT JOIN stock_prices p ON s.id = p.stock_id
            GROUP BY s.id, s.symbol, s.company_name
            ORDER BY s.symbol ASC
        """
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn)

        return df.to_dict(orient="records")
