#!/usr/bin/env python3
"""
Sync BigQuery data (GA4, GSC, Clarity) to local DuckDB warehouse.

Pulls data from BigQuery and stores in warehouse.duckdb tables:
- bq_gsc_site_impressions: Search Console site-level data
- bq_gsc_url_impressions: Search Console URL-level data
- bq_clarity_*: Clarity metrics (snapshots, devices, countries, etc.)
- bq_ga4_events: GA4 raw events (when available)

Usage:
    python3 db_api/sync_bigquery.py              # Sync all available data
    python3 db_api/sync_bigquery.py --days 30    # Sync last 30 days
    python3 db_api/sync_bigquery.py --source gsc # Sync only GSC
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

import duckdb
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

try:
    from google.cloud import bigquery
    from google.oauth2 import service_account
except ImportError:
    print("ERROR: Required packages not installed. Run:")
    print("  pip3 install google-cloud-bigquery google-auth")
    sys.exit(1)

# Configuration
PROJECT_ID = 'getlinkspro-453615'
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    'GOOGLE_SERVICE_ACCOUNT_FILE',
    os.path.join(os.path.dirname(__file__), 'getlinkspro-453615-c0e5ea39671a.json')
)
WAREHOUSE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'warehouse.duckdb')


def log(msg):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_bigquery_client():
    """Initialize BigQuery client."""
    if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Service account file not found: {GOOGLE_SERVICE_ACCOUNT_FILE}")

    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/bigquery']
    )
    return bigquery.Client(credentials=credentials, project=PROJECT_ID)


def sync_gsc_data(bq_client, conn, days=None):
    """Sync Google Search Console data."""
    log("Syncing GSC data...")

    # Sync site impressions
    log("  Fetching searchdata_site_impression...")
    query = """
        SELECT *
        FROM `getlinkspro-453615.searchconsole_fatgrid.searchdata_site_impression`
    """
    if days:
        query += f" WHERE data_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)"
    query += " ORDER BY data_date DESC"

    df = bq_client.query(query).to_dataframe()
    log(f"    Got {len(df)} rows")

    if len(df) > 0:
        # Convert db_dtypes.Date to datetime
        for col in df.columns:
            if hasattr(df[col].dtype, 'name') and 'dbdate' in str(df[col].dtype).lower():
                df[col] = df[col].astype('datetime64[ns]')

        conn.execute("CREATE OR REPLACE TABLE bq_gsc_site_impressions AS SELECT * FROM df")
        log(f"    Saved to bq_gsc_site_impressions")

    # Sync URL impressions
    log("  Fetching searchdata_url_impression...")
    query = """
        SELECT *
        FROM `getlinkspro-453615.searchconsole_fatgrid.searchdata_url_impression`
    """
    if days:
        query += f" WHERE data_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)"
    query += " ORDER BY data_date DESC"

    df = bq_client.query(query).to_dataframe()
    log(f"    Got {len(df)} rows")

    if len(df) > 0:
        # Convert db_dtypes.Date to datetime
        for col in df.columns:
            if hasattr(df[col].dtype, 'name') and 'dbdate' in str(df[col].dtype).lower():
                df[col] = df[col].astype('datetime64[ns]')

        conn.execute("CREATE OR REPLACE TABLE bq_gsc_url_impressions AS SELECT * FROM df")
        log(f"    Saved to bq_gsc_url_impressions")

    return len(df)


def sync_clarity_data(bq_client, conn):
    """Sync Clarity data from BigQuery."""
    log("Syncing Clarity data...")

    tables = ['snapshots', 'devices', 'countries', 'browsers', 'os', 'pages']
    total_rows = 0

    for table in tables:
        log(f"  Fetching {table}...")
        query = f"""
            SELECT *
            FROM `getlinkspro-453615.clarity.{table}`
        """

        df = bq_client.query(query).to_dataframe()
        log(f"    Got {len(df)} rows")

        if len(df) > 0:
            table_name = f"bq_clarity_{table}"
            conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
            log(f"    Saved to {table_name}")
            total_rows += len(df)

    return total_rows


def sync_ga4_data(bq_client, conn, days=None):
    """Sync GA4 events data."""
    log("Syncing GA4 data...")

    # Check if tables exist
    query = """
        SELECT table_name
        FROM `getlinkspro-453615.fatgrid_analytics.INFORMATION_SCHEMA.TABLES`
        WHERE table_name LIKE 'events_%'
    """

    try:
        tables = bq_client.query(query).to_dataframe()
        if len(tables) == 0:
            log("  No GA4 tables found yet (export still pending)")
            return 0

        log(f"  Found {len(tables)} GA4 event tables")

        # For now, just get a summary - full event sync would be huge
        # We'll aggregate daily metrics instead of raw events
        log("  Aggregating daily metrics...")

        date_filter = ""
        if days:
            date_filter = f"WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY))"

        query = f"""
            SELECT
                PARSE_DATE('%Y%m%d', event_date) as date,
                COUNT(*) as events,
                COUNT(DISTINCT user_pseudo_id) as users,
                COUNT(DISTINCT CONCAT(user_pseudo_id,
                    CAST(event_timestamp AS STRING))) as sessions,
                COUNTIF(event_name = 'page_view') as pageviews
            FROM `getlinkspro-453615.fatgrid_analytics.events_*`
            {date_filter}
            GROUP BY date
            ORDER BY date DESC
        """

        df = bq_client.query(query).to_dataframe()
        log(f"    Got {len(df)} days of data")

        if len(df) > 0:
            conn.execute("CREATE OR REPLACE TABLE bq_ga4_daily AS SELECT * FROM df")
            log(f"    Saved to bq_ga4_daily")

        return len(df)

    except Exception as e:
        log(f"  Error syncing GA4: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(description='Sync BigQuery data to DuckDB')
    parser.add_argument('--days', type=int, help='Only sync last N days')
    parser.add_argument('--source', choices=['gsc', 'clarity', 'ga4'],
                        help='Only sync specific source')
    parser.add_argument('--full', action='store_true',
                        help='Sync all available data (default)')
    args = parser.parse_args()

    print("=" * 60)
    print("BigQuery → DuckDB Sync")
    print("=" * 60)
    log(f"Warehouse: {WAREHOUSE_PATH}")
    if args.days:
        log(f"Date range: Last {args.days} days")
    print("-" * 60)

    try:
        # Connect to BigQuery
        log("Connecting to BigQuery...")
        bq_client = get_bigquery_client()
        log("  Connected")

        # Connect to DuckDB
        log("Opening warehouse...")
        conn = duckdb.connect(WAREHOUSE_PATH)
        log("  Connected")

        print("-" * 60)

        total_rows = 0

        # Sync each source
        if not args.source or args.source == 'gsc':
            total_rows += sync_gsc_data(bq_client, conn, args.days)

        if not args.source or args.source == 'clarity':
            total_rows += sync_clarity_data(bq_client, conn)

        if not args.source or args.source == 'ga4':
            total_rows += sync_ga4_data(bq_client, conn, args.days)

        # Add sync metadata
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                source VARCHAR,
                last_sync TIMESTAMP,
                rows_synced INTEGER
            )
        """)

        conn.close()

        print("-" * 60)
        log(f"DONE! Synced {total_rows:,} total rows")
        print("=" * 60)

        # Show summary
        print("\nTo query the data:")
        print("  python3 -c \"import duckdb; print(duckdb.connect('warehouse.duckdb').sql('SHOW TABLES'))\"")

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
