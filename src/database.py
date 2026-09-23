import logging
from typing import Tuple
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    Float,
    String,
    Date,
    ForeignKey,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from src.config import DATABASE_URL

logger = logging.getLogger(__name__)

Base = declarative_base()


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), unique=True, nullable=False, index=True)
    company_name = Column(String(255), nullable=True)

    prices = relationship("StockPrice", back_populates="stock", cascade="all, delete-orphan")
    metrics = relationship("DailyMetric", back_populates="stock", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Stock(symbol='{self.symbol}', company='{self.company_name}')>"


class StockPrice(Base):
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)

    stock = relationship("Stock", back_populates="prices")

    __table_args__ = (
        UniqueConstraint("stock_id", "trade_date", name="uq_stock_prices_stock_date"),
    )

    def __repr__(self) -> str:
        return f"<StockPrice(stock_id={self.stock_id}, date={self.trade_date}, close={self.close_price})>"


class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    daily_change = Column(Float, nullable=True)
    daily_return_pct = Column(Float, nullable=True)
    moving_avg_7 = Column(Float, nullable=True)
    moving_avg_30 = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)

    stock = relationship("Stock", back_populates="metrics")

    __table_args__ = (
        UniqueConstraint("stock_id", "trade_date", name="uq_daily_metrics_stock_date"),
    )

    def __repr__(self) -> str:
        return f"<DailyMetric(stock_id={self.stock_id}, date={self.trade_date}, return={self.daily_return_pct})>"


def get_engine(db_url: str = None):
    """Create and return a SQLAlchemy engine with connection pooling."""
    url = db_url or DATABASE_URL
    # For SQLite (often used in tests), use special connect_args
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True,
    )


def get_session(engine=None) -> Session:
    """Create a new database session."""
    engine = engine or get_engine()
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return factory()


def init_db(engine=None) -> None:
    """Create all database tables if they do not exist."""
    engine = engine or get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")


def check_connection(engine=None) -> Tuple[bool, str]:
    """
    Test database connectivity.
    Return a success flag and a short status message.
    """
    try:
        eng = engine or get_engine()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection successful."
    except Exception as exc:
        logger.warning(f"Database connection check failed: {exc}")
        return False, str(exc)
