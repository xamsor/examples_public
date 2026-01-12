#!/usr/bin/env python3
"""
Sync Google Analytics 4 data to local DuckDB warehouse.

Pulls daily metrics and stores in warehouse.duckdb tables:
- ga4_daily: Daily traffic overview
- ga4_pages: Page-level metrics
- ga4_sources: Traffic sources
- ga4_countries: Country breakdown

Usage:
    python3 db_api/sync_ga4.py              # Sync last 30 days
    python3 db_api/sync_ga4.py --days 90    # Sync last 90 days
    python3 db_api/sync_ga4.py --full       # Sync all available data (365 days)
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

import duckdb
from dotenv import load_dotenv

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest,
        DateRange,
        Dimension,
        Metric,
    )
    from google.oauth2 import service_account
except ImportError:
    print("ERROR: Required packages not installed. Run:")
    print("  pip3 install google-analytics-data google-auth")
    sys.exit(1)

# Configuration
GA4_PROPERTY_ID = os.getenv('GA4_PROPERTY_ID', '480666040')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    'GOOGLE_SERVICE_ACCOUNT_FILE',
    os.path.join(os.path.dirname(__file__), 'getlinkspro-453615-c0e5ea39671a.json')
)
WAREHOUSE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'warehouse.duckdb')


def log(msg):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_ga4_client():
    """Initialize GA4 client."""
    if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Service account file not found: {GOOGLE_SERVICE_ACCOUNT_FILE}")

    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/analytics.readonly']
    )
    return BetaAnalyticsDataClient(credentials=credentials)


def fetch_report(client, dimensions, metrics, start_date, end_date, limit=10000):
    """Fetch a GA4 report."""
    property_name = f"properties/{GA4_PROPERTY_ID}"

    request = RunReportRequest(
        property=property_name,
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        limit=limit
    )

    return client.run_report(request)


def response_to_rows(response, dimensions, metrics):
    """Convert GA4 response to list of dicts."""
    rows = []
    for row in response.rows:
        data = {}
        for i, dim in enumerate(dimensions):
            data[dim] = row.dimension_values[i].value
        for i, met in enumerate(metrics):
            val = row.metric_values[i].value
            # Convert numeric strings
            try:
                if '.' in val:
                    data[met] = float(val)
                else:
                    data[met] = int(val)
            except ValueError:
                data[met] = val
        rows.append(data)
    return rows


def sync_daily(client, conn, start_date, end_date):
    """Sync daily traffic overview."""
    log("Fetching daily overview...")

    dimensions = ['date']
    metrics = ['sessions', 'totalUsers', 'newUsers', 'screenPageViews',
               'averageSessionDuration', 'bounceRate', 'engagedSessions']

    response = fetch_report(client, dimensions, metrics, start_date, end_date)
    rows = response_to_rows(response, dimensions, metrics)

    log(f"  Got {len(rows)} days of data")

    if not rows:
        return 0

    # Create table and insert
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ga4_daily (
            date DATE PRIMARY KEY,
            sessions INTEGER,
            total_users INTEGER,
            new_users INTEGER,
            pageviews INTEGER,
            avg_session_duration DOUBLE,
            bounce_rate DOUBLE,
            engaged_sessions INTEGER,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Upsert data
    for row in rows:
        date_str = row['date']
        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

        conn.execute("""
            INSERT OR REPLACE INTO ga4_daily
            (date, sessions, total_users, new_users, pageviews,
             avg_session_duration, bounce_rate, engaged_sessions, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            date_formatted,
            row['sessions'],
            row['totalUsers'],
            row['newUsers'],
            row['screenPageViews'],
            row['averageSessionDuration'],
            row.get('bounceRate', 0),
            row.get('engagedSessions', 0)
        ])

    log(f"  Saved {len(rows)} rows to ga4_daily")
    return len(rows)


def sync_pages(client, conn, start_date, end_date):
    """Sync page-level metrics."""
    log("Fetching page metrics...")

    dimensions = ['pagePath', 'pageTitle']
    metrics = ['screenPageViews', 'totalUsers', 'averageSessionDuration', 'bounceRate']

    response = fetch_report(client, dimensions, metrics, start_date, end_date, limit=5000)
    rows = response_to_rows(response, dimensions, metrics)

    log(f"  Got {len(rows)} pages")

    if not rows:
        return 0

    # Create table (page_path + page_title as key since same path can have different titles)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ga4_pages (
            date_range_start DATE,
            date_range_end DATE,
            page_path VARCHAR,
            page_title VARCHAR,
            pageviews INTEGER,
            users INTEGER,
            avg_session_duration DOUBLE,
            bounce_rate DOUBLE,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Delete existing data for this date range and insert new
    conn.execute("""
        DELETE FROM ga4_pages
        WHERE date_range_start = ? AND date_range_end = ?
    """, [start_date, end_date])

    for row in rows:
        conn.execute("""
            INSERT INTO ga4_pages
            (date_range_start, date_range_end, page_path, page_title,
             pageviews, users, avg_session_duration, bounce_rate, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            start_date, end_date,
            row['pagePath'],
            row['pageTitle'][:500] if row['pageTitle'] else None,
            row['screenPageViews'],
            row['totalUsers'],
            row['averageSessionDuration'],
            row.get('bounceRate', 0)
        ])

    log(f"  Saved {len(rows)} rows to ga4_pages")
    return len(rows)


def sync_sources(client, conn, start_date, end_date):
    """Sync traffic sources."""
    log("Fetching traffic sources...")

    dimensions = ['sessionSource', 'sessionMedium', 'sessionCampaignName']
    metrics = ['sessions', 'totalUsers', 'newUsers', 'bounceRate']

    response = fetch_report(client, dimensions, metrics, start_date, end_date, limit=1000)
    rows = response_to_rows(response, dimensions, metrics)

    log(f"  Got {len(rows)} source combinations")

    if not rows:
        return 0

    # Create table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ga4_sources (
            date_range_start DATE,
            date_range_end DATE,
            source VARCHAR,
            medium VARCHAR,
            campaign VARCHAR,
            sessions INTEGER,
            users INTEGER,
            new_users INTEGER,
            bounce_rate DOUBLE,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date_range_start, date_range_end, source, medium, campaign)
        )
    """)

    # Delete existing and insert
    conn.execute("""
        DELETE FROM ga4_sources
        WHERE date_range_start = ? AND date_range_end = ?
    """, [start_date, end_date])

    for row in rows:
        conn.execute("""
            INSERT INTO ga4_sources
            (date_range_start, date_range_end, source, medium, campaign,
             sessions, users, new_users, bounce_rate, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            start_date, end_date,
            row['sessionSource'],
            row['sessionMedium'],
            row.get('sessionCampaignName', '(not set)'),
            row['sessions'],
            row['totalUsers'],
            row['newUsers'],
            row.get('bounceRate', 0)
        ])

    log(f"  Saved {len(rows)} rows to ga4_sources")
    return len(rows)


def sync_countries(client, conn, start_date, end_date):
    """Sync country breakdown."""
    log("Fetching country data...")

    dimensions = ['country', 'city']
    metrics = ['sessions', 'totalUsers', 'screenPageViews']

    response = fetch_report(client, dimensions, metrics, start_date, end_date, limit=2000)
    rows = response_to_rows(response, dimensions, metrics)

    log(f"  Got {len(rows)} country/city combinations")

    if not rows:
        return 0

    # Create table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ga4_countries (
            date_range_start DATE,
            date_range_end DATE,
            country VARCHAR,
            city VARCHAR,
            sessions INTEGER,
            users INTEGER,
            pageviews INTEGER,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date_range_start, date_range_end, country, city)
        )
    """)

    # Delete existing and insert
    conn.execute("""
        DELETE FROM ga4_countries
        WHERE date_range_start = ? AND date_range_end = ?
    """, [start_date, end_date])

    for row in rows:
        conn.execute("""
            INSERT INTO ga4_countries
            (date_range_start, date_range_end, country, city,
             sessions, users, pageviews, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            start_date, end_date,
            row['country'],
            row['city'],
            row['sessions'],
            row['totalUsers'],
            row['screenPageViews']
        ])

    log(f"  Saved {len(rows)} rows to ga4_countries")
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description='Sync GA4 data to DuckDB')
    parser.add_argument('--days', type=int, default=30, help='Number of days to sync (default: 30)')
    parser.add_argument('--full', action='store_true', help='Sync all available data (365 days)')
    args = parser.parse_args()

    days = 365 if args.full else args.days

    print("=" * 60)
    print("GA4 → DuckDB Sync")
    print("=" * 60)
    log(f"Property ID: {GA4_PROPERTY_ID}")
    log(f"Warehouse: {WAREHOUSE_PATH}")
    log(f"Date range: last {days} days")
    print("-" * 60)

    # Calculate date range
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    log(f"Syncing {start_date} to {end_date}")

    try:
        # Initialize
        log("Connecting to GA4...")
        client = get_ga4_client()
        log("  Connected")

        log("Opening warehouse...")
        conn = duckdb.connect(WAREHOUSE_PATH)
        log("  Connected")

        print("-" * 60)

        # Sync each dataset
        total_rows = 0

        total_rows += sync_daily(client, conn, start_date, end_date)
        total_rows += sync_pages(client, conn, start_date, end_date)
        total_rows += sync_sources(client, conn, start_date, end_date)
        total_rows += sync_countries(client, conn, start_date, end_date)

        conn.close()

        print("-" * 60)
        log(f"DONE! Synced {total_rows:,} total rows")
        print("=" * 60)

        # Show summary
        print("\nTo query the data:")
        print("  python3 -c \"import duckdb; print(duckdb.connect('warehouse.duckdb').sql('SELECT * FROM ga4_daily ORDER BY date DESC LIMIT 10'))\"")

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
