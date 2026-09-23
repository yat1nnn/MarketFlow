"""Start MarketFlow after checking the local setup."""

import sys
import subprocess
from pathlib import Path

# Add the project root to the import path.
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def print_banner():
    banner = r"""
======================================================================
  __  __            _        _   ______ _                 
 |  \/  |          | |      | | |  ____| |                
 | \  / | __ _ _ __| | _____| |_| |__  | | _____      __  
 | |\/| |/ _` | '__| |/ / _ \ __|  __| | |/ _ \ \ /\ / /  
 | |  | | (_| | |  |   <  __/ |_| |    | | (_) \ V  V /   
 |_|  |_|\__,_|_|  |_|\_\___|\__|_|    |_|\___/ \_/\_/    
                                                          
 Market data and analytics platform
======================================================================
    """
    print(banner)


def check_configuration():
    print("[1/4] Checking configuration...")
    env_file = PROJECT_ROOT / ".env"
    env_example = PROJECT_ROOT / ".env.example"

    if not env_file.exists():
        if env_example.exists():
            print("  [!] .env not found. Copying .env.example to .env...")
            env_file.write_text(env_example.read_text())
        else:
            print("  [X] Neither .env nor .env.example found!")

    from src.config import DATABASE_URL, TWELVE_DATA_API_KEY, mask_key, SAMPLE_CSV_PATH
    print(f"  [OK] Database URL: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
    print(f"  [OK] Twelve Data API Key: {mask_key(TWELVE_DATA_API_KEY)}")
    print(f"  [OK] Sample CSV Path: {SAMPLE_CSV_PATH.name} ({'Found' if SAMPLE_CSV_PATH.exists() else 'Missing'})")


def check_database():
    print("[2/4] Checking PostgreSQL...")
    from src.database import check_connection, init_db, get_engine
    engine = get_engine()
    ok, msg = check_connection(engine)
    if ok:
        print(f"  [OK] PostgreSQL Connection Successful: {msg}")
        init_db(engine)
        print("  [OK] Database schema verified / initialized.")
        return True
    else:
        print(f"  [X] PostgreSQL Connection Failed: {msg}")
        print("  [!] Please ensure PostgreSQL is running and credentials in .env are correct.")
        return False


def seed_sample_data_if_needed():
    print("[3/4] Checking warehouse...")
    from src.loader import StockDataLoader
    from src.extractor import StockDataExtractor
    from src.transformer import StockDataTransformer
    from src.metrics import calculate_metrics

    loader = StockDataLoader()
    symbols = loader.get_available_symbols()

    if not symbols:
        print("  [INFO] Database is empty. Pre-loading sample data for AAPL, MSFT, GOOGL, AMZN...")
        extractor = StockDataExtractor()
        transformer = StockDataTransformer()

        for sym in ["AAPL", "MSFT", "GOOGL", "AMZN"]:
            try:
                raw_df, _, _ = extractor.extract(sym, source="CSV")
                clean_df = transformer.transform(raw_df)
                enriched_df = calculate_metrics(clean_df)
                loader.load_stock_data(sym, enriched_df)
                print(f"  [OK] Loaded {len(enriched_df)} records for {sym}.")
            except Exception as e:
                print(f"  [!] Could not load initial data for {sym}: {e}")
    else:
        print(f"  [OK] Warehouse ready with {len(symbols)} tracked stocks: {[s['symbol'] for s in symbols]}")


def start_streamlit():
    print("[4/4] Starting Streamlit...")
    app_path = PROJECT_ROOT / "app" / "streamlit_app.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    print(f"  --> Running: {' '.join(cmd)}\n")
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nMarketFlow Dashboard stopped by user.")


def main():
    print_banner()
    check_configuration()
    db_ok = check_database()
    if db_ok:
        seed_sample_data_if_needed()
    start_streamlit()


if __name__ == "__main__":
    main()
