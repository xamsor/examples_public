#!/usr/bin/env python3
"""
Sync Google Search Console data to local DuckDB warehouse.

Pulls search performance data and stores in warehouse.duckdb tables:
- gsc_daily: Daily search performance
- gsc_queries: Search queries with clicks/impressions
- gsc_pages: Page-level search performance
- gsc_countries: Country breakdown

Usage:
    python3 db_api/sync_gsc.py              # Sync last 30 days
    python3 db_api/sync_gsc.py --days 90    # Sync last 90 days
    python3 db_api/sync_gsc.py --full       # Sync all available (16 months)
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
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    print("ERROR: Required packages not installed. Run:")
    print("  pip3 install google-api-python-client google-auth")
    sys.exit(1)

# Configuration
GSC_SITE_URL = os.getenv('GSC_SITE_URL', 'https://fatgrid.com/')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    'GOOGLE_SERVICE_ACCOUNT_FILE',
    os.path.join(os.path.dirname(__file__), 'getlinkspro-453615-c0e5ea39671a.json')
)
WAREHOUSE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'warehouse.duckdb')


def log(msg):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_gsc_client():
    """Initialize GSC client."""
    if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Service account file not found: {GOOGLE_SERVICE_ACCOUNT_FILE}")

    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/webmasters.readonly']
    )
    return build('searchconsole', 'v1', credentials=credentials)


def fetch_gsc_data(service, start_date, end_date, dimensions, row_limit=25000):
    """Fetch GSC data for given dimensions."""
    request = {
        'startDate': start_date,
        'endDate': end_date,
        'dimensions': dimensions,
        'rowLimit': row_limit
    }

    response = service.searchanalytics().query(
        siteUrl=GSC_SITE_URL,
        body=request
    ).execute()

    return response.get('rows', [])


def sync_daily(service, conn, start_date, end_date):
    """Sync daily search performance."""
    log("Fetching daily performance...")

    rows = fetch_gsc_data(service, start_date, end_date, ['date'])
    log(f"  Got {len(rows)} days of data")

    if not rows:
        return 0

    # Create table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gsc_daily (
            date DATE PRIMARY KEY,
            clicks INTEGER,
            impressions INTEGER,
            ctr DOUBLE,
            position DOUBLE,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Upsert data
    for row in rows:
        date = row['keys'][0]
        conn.execute("""
            INSERT OR REPLACE INTO gsc_daily
            (date, clicks, impressions, ctr, position, synced_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            date,
            row.get('clicks', 0),
            row.get('impressions', 0),
            row.get('ctr', 0),
            row.get('position', 0)
        ])

    log(f"  Saved {len(rows)} rows to gsc_daily")
    return len(rows)


def sync_queries(service, conn, start_date, end_date):
    """Sync search queries."""
    log("Fetching search queries...")

    rows = fetch_gsc_data(service, start_date, end_date, ['query'], row_limit=25000)
    log(f"  Got {len(rows)} queries")

    if not rows:
        return 0

    # Create table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gsc_queries (
            date_range_start DATE,
            date_range_end DATE,
            query VARCHAR,
            clicks INTEGER,
            impressions INTEGER,
            ctr DOUBLE,
            position DOUBLE,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Delete existing and insert
    conn.execute("""
        DELETE FROM gsc_queries
        WHERE date_range_start = ? AND date_range_end = ?
    """, [start_date, end_date])

    for row in rows:
        conn.execute("""
            INSERT INTO gsc_queries
            (date_range_start, date_range_end, query, clicks, impressions, ctr, position, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            start_date, end_date,
            row['keys'][0],
            row.get('clicks', 0),
            row.get('impressions', 0),
            row.get('ctr', 0),
            row.get('position', 0)
        ])

    log(f"  Saved {len(rows)} rows to gsc_queries")
    return len(rows)


def sync_pages(service, conn, start_date, end_date):
    """Sync page-level search data."""
    log("Fetching page performance...")

    rows = fetch_gsc_data(service, start_date, end_date, ['page'], row_limit=25000)
    log(f"  Got {len(rows)} pages")

    if not rows:
        return 0

    # Create table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gsc_pages (
            date_range_start DATE,
            date_range_end DATE,
            page VARCHAR,
            clicks INTEGER,
            impressions INTEGER,
            ctr DOUBLE,
            position DOUBLE,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Delete existing and insert
    conn.execute("""
        DELETE FROM gsc_pages
        WHERE date_range_start = ? AND date_range_end = ?
    """, [start_date, end_date])

    for row in rows:
        conn.execute("""
            INSERT INTO gsc_pages
            (date_range_start, date_range_end, page, clicks, impressions, ctr, position, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            start_date, end_date,
            row['keys'][0],
            row.get('clicks', 0),
            row.get('impressions', 0),
            row.get('ctr', 0),
            row.get('position', 0)
        ])

    log(f"  Saved {len(rows)} rows to gsc_pages")
    return len(rows)


def sync_countries(service, conn, start_date, end_date):
    """Sync country breakdown."""
    log("Fetching country data...")

    rows = fetch_gsc_data(service, start_date, end_date, ['country'], row_limit=250)
    log(f"  Got {len(rows)} countries")

    if not rows:
        return 0

    # Create table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gsc_countries (
            date_range_start DATE,
            date_range_end DATE,
            country VARCHAR,
            clicks INTEGER,
            impressions INTEGER,
            ctr DOUBLE,
            position DOUBLE,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Delete existing and insert
    conn.execute("""
        DELETE FROM gsc_countries
        WHERE date_range_start = ? AND date_range_end = ?
    """, [start_date, end_date])

    for row in rows:
        conn.execute("""
            INSERT INTO gsc_countries
            (date_range_start, date_range_end, country, clicks, impressions, ctr, position, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            start_date, end_date,
            row['keys'][0],
            row.get('clicks', 0),
            row.get('impressions', 0),
            row.get('ctr', 0),
            row.get('position', 0)
        ])

    log(f"  Saved {len(rows)} rows to gsc_countries")
    return len(rows)


def sync_devices(service, conn, start_date, end_date):
    """Sync device breakdown."""
    log("Fetching device data...")

    rows = fetch_gsc_data(service, start_date, end_date, ['device'], row_limit=10)
    log(f"  Got {len(rows)} device types")

    if not rows:
        return 0

    # Create table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gsc_devices (
            date_range_start DATE,
            date_range_end DATE,
            device VARCHAR,
            clicks INTEGER,
            impressions INTEGER,
            ctr DOUBLE,
            position DOUBLE,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Delete existing and insert
    conn.execute("""
        DELETE FROM gsc_devices
        WHERE date_range_start = ? AND date_range_end = ?
    """, [start_date, end_date])

    for row in rows:
        conn.execute("""
            INSERT INTO gsc_devices
            (date_range_start, date_range_end, device, clicks, impressions, ctr, position, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            start_date, end_date,
            row['keys'][0],
            row.get('clicks', 0),
            row.get('impressions', 0),
            row.get('ctr', 0),
            row.get('position', 0)
        ])

    log(f"  Saved {len(rows)} rows to gsc_devices")
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description='Sync GSC data to DuckDB')
    parser.add_argument('--days', type=int, default=30, help='Number of days to sync (default: 30)')
    parser.add_argument('--full', action='store_true', help='Sync all available data (~16 months)')
    args = parser.parse_args()

    # GSC has max ~16 months of data
    days = 480 if args.full else args.days

    print("=" * 60)
    print("GSC → DuckDB Sync")
    print("=" * 60)
    log(f"Site: {GSC_SITE_URL}")
    log(f"Warehouse: {WAREHOUSE_PATH}")
    log(f"Date range: last {days} days")
    print("-" * 60)

    # Calculate date range (GSC data has 2-3 day delay)
    end_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    log(f"Syncing {start_date} to {end_date}")

    try:
        # Initialize
        log("Connecting to GSC...")
        service = get_gsc_client()
        log("  Connected")

        log("Opening warehouse...")
        conn = duckdb.connect(WAREHOUSE_PATH)
        log("  Connected")

        print("-" * 60)

        # Sync each dataset
        total_rows = 0

        total_rows += sync_daily(service, conn, start_date, end_date)
        total_rows += sync_queries(service, conn, start_date, end_date)
        total_rows += sync_pages(service, conn, start_date, end_date)
        total_rows += sync_countries(service, conn, start_date, end_date)
        total_rows += sync_devices(service, conn, start_date, end_date)

        conn.close()

        print("-" * 60)
        log(f"DONE! Synced {total_rows:,} total rows")
        print("=" * 60)

        # Show summary
        print("\nTo query the data:")
        print("  python3 -c \"import duckdb; print(duckdb.connect('warehouse.duckdb').sql('SELECT * FROM gsc_queries ORDER BY clicks DESC LIMIT 10'))\"")

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
