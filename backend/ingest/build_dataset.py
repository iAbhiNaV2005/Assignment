"""Build clean SQLite database from Elexon BMRS API data and generate quality audit report."""

import logging
import os
import sqlite3

import pandas as pd

from backend.ingest.clean import clean_fuelhh_data, clean_windfor_data
from backend.ingest.fetch import fetch_fuelhh_actuals, fetch_windfor_forecasts

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "wind_data.db")


def init_database(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Initialize SQLite database schema and indices."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actuals (
            startTime TEXT PRIMARY KEY,
            settlementDate TEXT NOT NULL,
            settlementPeriod INTEGER NOT NULL,
            generation REAL NOT NULL,
            publishTime TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publishTime TEXT NOT NULL,
            startTime TEXT NOT NULL,
            generation REAL NOT NULL
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actuals_date ON actuals(settlementDate)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forecasts_target ON forecasts(startTime, publishTime)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forecasts_pub ON forecasts(publishTime)")

    conn.commit()
    return conn


def save_to_database(df_actuals: pd.DataFrame, df_forecasts: pd.DataFrame, db_path: str = DEFAULT_DB_PATH):
    """Save cleaned dataframes into SQLite with replacement."""
    conn = init_database(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM actuals")
    cursor.execute("DELETE FROM forecasts")
    conn.commit()

    logger.info(f"Writing {len(df_actuals)} actual records to database...")
    df_actuals.to_sql("actuals", conn, if_exists="append", index=False)

    logger.info(f"Writing {len(df_forecasts)} forecast records to database...")
    df_forecasts.to_sql("forecasts", conn, if_exists="append", index=False)

    conn.commit()
    conn.close()
    logger.info(f"Database successfully saved to {db_path} ({os.path.getsize(db_path) / (1024*1024):.2f} MB)")


def generate_quality_report(db_path: str = DEFAULT_DB_PATH) -> dict:
    """Run data quality verification and print audit report."""
    conn = sqlite3.connect(db_path)

    df_act = pd.read_sql("SELECT * FROM actuals ORDER BY startTime", conn)
    df_fc = pd.read_sql("SELECT * FROM forecasts ORDER BY publishTime, startTime", conn)
    conn.close()

    total_actual_periods = len(df_act)
    expected_actual_periods = 31 * 48  # January has 31 days
    missing_actual_periods = expected_actual_periods - total_actual_periods

    report = {
        "actuals": {
            "total_rows": total_actual_periods,
            "expected_rows": expected_actual_periods,
            "missing_periods": missing_actual_periods,
            "min_gen_mw": float(df_act["generation"].min()) if not df_act.empty else 0.0,
            "max_gen_mw": float(df_act["generation"].max()) if not df_act.empty else 0.0,
            "mean_gen_mw": float(df_act["generation"].mean()) if not df_act.empty else 0.0,
            "start_time_min": df_act["startTime"].min() if not df_act.empty else None,
            "start_time_max": df_act["startTime"].max() if not df_act.empty else None,
        },
        "forecasts": {
            "total_rows": len(df_fc),
            "unique_publish_times": df_fc["publishTime"].nunique() if not df_fc.empty else 0,
            "unique_target_times": df_fc["startTime"].nunique() if not df_fc.empty else 0,
            "min_gen_mw": float(df_fc["generation"].min()) if not df_fc.empty else 0.0,
            "max_gen_mw": float(df_fc["generation"].max()) if not df_fc.empty else 0.0,
            "mean_gen_mw": float(df_fc["generation"].mean()) if not df_fc.empty else 0.0,
            "publish_time_min": df_fc["publishTime"].min() if not df_fc.empty else None,
            "publish_time_max": df_fc["publishTime"].max() if not df_fc.empty else None,
        },
    }

    print("\n" + "=" * 60)
    print("           ELEXON DATA QUALITY AUDIT REPORT")
    print("=" * 60)
    print("FUELHH Actuals (January 2026):")
    print(f"  Total records:      {report['actuals']['total_rows']} / {expected_actual_periods} (Missing: {missing_actual_periods})")
    print(f"  Generation (MW):    Min={report['actuals']['min_gen_mw']:.1f}, Mean={report['actuals']['mean_gen_mw']:.1f}, Max={report['actuals']['max_gen_mw']:.1f}")
    print(f"  Target Range:       {report['actuals']['start_time_min']} to {report['actuals']['start_time_max']}")
    print("-" * 60)
    print("WINDFOR Forecasts:")
    print(f"  Total records:      {report['forecasts']['total_rows']}")
    print(f"  Unique publishTimes:{report['forecasts']['unique_publish_times']}")
    print(f"  Unique startTimes:  {report['forecasts']['unique_target_times']}")
    print(f"  Generation (MW):    Min={report['forecasts']['min_gen_mw']:.1f}, Mean={report['forecasts']['mean_gen_mw']:.1f}, Max={report['forecasts']['max_gen_mw']:.1f}")
    print(f"  Publish Range:      {report['forecasts']['publish_time_min']} to {report['forecasts']['publish_time_max']}")
    print("=" * 60 + "\n")

    return report


def build_dataset(db_path: str = DEFAULT_DB_PATH):
    """Main pipeline execution: fetch, clean, store, and verify."""
    logger.info("Starting ingest pipeline...")

    # 1. Fetch
    raw_fuelhh = fetch_fuelhh_actuals("2026-01-01", "2026-01-31", "WIND")
    raw_windfor = fetch_windfor_forecasts("2025-12-25T00:00:00Z", "2026-01-31T23:59:59Z", chunk_days=7)

    # 2. Clean
    df_act = clean_fuelhh_data(raw_fuelhh)
    df_fc = clean_windfor_data(raw_windfor)

    # 3. Store
    save_to_database(df_act, df_fc, db_path)

    # 4. Report
    generate_quality_report(db_path)
    logger.info("Ingest pipeline completed successfully.")


if __name__ == "__main__":
    build_dataset()
