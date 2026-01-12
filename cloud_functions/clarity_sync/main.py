"""
Cloud Function: Sync Microsoft Clarity data to BigQuery

Triggered daily by Cloud Scheduler. Fetches last 72h of Clarity data
and appends to BigQuery tables in the `clarity` dataset.

Tables created:
- clarity.snapshots: Daily metrics snapshots
- clarity.devices: Device breakdown
- clarity.countries: Country breakdown
- clarity.browsers: Browser breakdown
- clarity.os: OS breakdown
- clarity.pages: Popular pages

Environment variables (set in Cloud Function config):
- CLARITY_API_TOKEN: Clarity Data Export API token
- CLARITY_PROJECT_ID: Clarity project ID
- GCP_PROJECT_ID: Google Cloud project ID (default: getlinkspro-453615)
- BQ_DATASET: BigQuery dataset name (default: clarity)
"""

import os
import json
import functions_framework
from datetime import datetime
from google.cloud import bigquery
import requests


# Configuration from environment
CLARITY_API_TOKEN = os.environ.get('CLARITY_API_TOKEN')
CLARITY_PROJECT_ID = os.environ.get('CLARITY_PROJECT_ID', 'pf8kyjwawu')
GCP_PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'getlinkspro-453615')
BQ_DATASET = os.environ.get('BQ_DATASET', 'clarity')

CLARITY_API_BASE = "https://www.clarity.ms/export-data/api/v1"


def log(msg):
    """Print with timestamp for Cloud Function logs."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def fetch_clarity_data(num_days=3):
    """Fetch Clarity live insights for last N days (max 3)."""
    if not CLARITY_API_TOKEN:
        raise ValueError("CLARITY_API_TOKEN environment variable not set")

    headers = {
        'Authorization': f'Bearer {CLARITY_API_TOKEN}',
        'Content-Type': 'application/json'
    }

    params = {'numOfDays': num_days}
    url = f"{CLARITY_API_BASE}/project-live-insights"

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return response.json()


def parse_metrics(data):
    """Parse raw Clarity response into structured metrics."""
    metrics = {}

    for item in data:
        metric_name = item.get('metricName')
        info = item.get('information', [])

        if metric_name == 'Traffic':
            if info:
                metrics['total_sessions'] = int(info[0].get('totalSessionCount', 0))
                metrics['bot_sessions'] = int(info[0].get('totalBotSessionCount', 0))
                metrics['distinct_users'] = int(info[0].get('distinctUserCount', 0))
                metrics['pages_per_session'] = float(info[0].get('pagesPerSessionPercentage', 0))

        elif metric_name == 'ScrollDepth':
            if info:
                metrics['avg_scroll_depth'] = float(info[0].get('averageScrollDepth', 0))

        elif metric_name == 'EngagementTime':
            if info:
                metrics['total_time_sec'] = int(info[0].get('totalTime', 0))
                metrics['active_time_sec'] = int(info[0].get('activeTime', 0))

        elif metric_name == 'DeadClickCount':
            if info:
                metrics['dead_click_pct'] = float(info[0].get('sessionsWithMetricPercentage', 0))
                metrics['dead_clicks'] = int(info[0].get('subTotal', 0))

        elif metric_name == 'RageClickCount':
            if info:
                metrics['rage_click_pct'] = float(info[0].get('sessionsWithMetricPercentage', 0))
                metrics['rage_clicks'] = int(info[0].get('subTotal', 0))

        elif metric_name == 'QuickbackClick':
            if info:
                metrics['quickback_pct'] = float(info[0].get('sessionsWithMetricPercentage', 0))
                metrics['quickbacks'] = int(info[0].get('subTotal', 0))

        elif metric_name == 'ScriptErrorCount':
            if info:
                metrics['script_error_pct'] = float(info[0].get('sessionsWithMetricPercentage', 0))

    return metrics


def parse_dimension_data(data, dimension_name):
    """Parse dimension breakdown from Clarity response."""
    items = []
    for item in data:
        if item.get('metricName') == dimension_name:
            for info in item.get('information', []):
                items.append({
                    'name': info.get('name'),
                    'sessions': int(info.get('sessionsCount', 0))
                })
    return items


def parse_pages(data):
    """Parse popular pages from Clarity response."""
    items = []
    for item in data:
        if item.get('metricName') == 'PopularPages':
            for info in item.get('information', []):
                items.append({
                    'url': info.get('url'),
                    'visits': int(info.get('visitsCount', 0))
                })
    return items


def ensure_dataset_exists(client):
    """Create BigQuery dataset if it doesn't exist."""
    dataset_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = "US"

    try:
        client.get_dataset(dataset_id)
        log(f"Dataset {dataset_id} already exists")
    except Exception:
        dataset = client.create_dataset(dataset, exists_ok=True)
        log(f"Created dataset {dataset_id}")


def sync_snapshot(client, data, num_days):
    """Save metrics snapshot to BigQuery."""
    log("Processing metrics snapshot...")

    metrics = parse_metrics(data)
    if not metrics:
        log("  No metrics found")
        return 0

    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.snapshots"

    # Define schema
    schema = [
        bigquery.SchemaField("snapshot_time", "TIMESTAMP"),
        bigquery.SchemaField("period_hours", "INTEGER"),
        bigquery.SchemaField("total_sessions", "INTEGER"),
        bigquery.SchemaField("bot_sessions", "INTEGER"),
        bigquery.SchemaField("distinct_users", "INTEGER"),
        bigquery.SchemaField("pages_per_session", "FLOAT"),
        bigquery.SchemaField("avg_scroll_depth", "FLOAT"),
        bigquery.SchemaField("total_time_sec", "INTEGER"),
        bigquery.SchemaField("active_time_sec", "INTEGER"),
        bigquery.SchemaField("dead_click_pct", "FLOAT"),
        bigquery.SchemaField("dead_clicks", "INTEGER"),
        bigquery.SchemaField("rage_click_pct", "FLOAT"),
        bigquery.SchemaField("rage_clicks", "INTEGER"),
        bigquery.SchemaField("quickback_pct", "FLOAT"),
        bigquery.SchemaField("quickbacks", "INTEGER"),
        bigquery.SchemaField("script_error_pct", "FLOAT"),
    ]

    # Create table if not exists
    table = bigquery.Table(table_id, schema=schema)
    table = client.create_table(table, exists_ok=True)

    # Insert row
    now = datetime.utcnow().isoformat()
    rows = [{
        "snapshot_time": now,
        "period_hours": num_days * 24,
        "total_sessions": metrics.get('total_sessions', 0),
        "bot_sessions": metrics.get('bot_sessions', 0),
        "distinct_users": metrics.get('distinct_users', 0),
        "pages_per_session": metrics.get('pages_per_session', 0),
        "avg_scroll_depth": metrics.get('avg_scroll_depth', 0),
        "total_time_sec": metrics.get('total_time_sec', 0),
        "active_time_sec": metrics.get('active_time_sec', 0),
        "dead_click_pct": metrics.get('dead_click_pct', 0),
        "dead_clicks": metrics.get('dead_clicks', 0),
        "rage_click_pct": metrics.get('rage_click_pct', 0),
        "rage_clicks": metrics.get('rage_clicks', 0),
        "quickback_pct": metrics.get('quickback_pct', 0),
        "quickbacks": metrics.get('quickbacks', 0),
        "script_error_pct": metrics.get('script_error_pct', 0),
    }]

    errors = client.insert_rows_json(table_id, rows)
    if errors:
        log(f"  Errors inserting snapshot: {errors}")
        return 0

    log(f"  Saved snapshot: {metrics.get('total_sessions', 0)} sessions, {metrics.get('distinct_users', 0)} users")
    return 1


def sync_dimension(client, data, dimension_name, table_name):
    """Sync a dimension breakdown to BigQuery."""
    log(f"Processing {dimension_name}...")

    items = parse_dimension_data(data, dimension_name)
    if not items:
        log(f"  No {dimension_name} data found")
        return 0

    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{table_name}"

    schema = [
        bigquery.SchemaField("snapshot_time", "TIMESTAMP"),
        bigquery.SchemaField("name", "STRING"),
        bigquery.SchemaField("sessions", "INTEGER"),
    ]

    table = bigquery.Table(table_id, schema=schema)
    table = client.create_table(table, exists_ok=True)

    now = datetime.utcnow().isoformat()
    rows = [
        {"snapshot_time": now, "name": item['name'], "sessions": item['sessions']}
        for item in items
    ]

    errors = client.insert_rows_json(table_id, rows)
    if errors:
        log(f"  Errors inserting {table_name}: {errors}")
        return 0

    log(f"  Saved {len(items)} rows to {table_name}")
    return len(items)


def sync_pages(client, data):
    """Sync popular pages to BigQuery."""
    log("Processing popular pages...")

    items = parse_pages(data)
    if not items:
        log("  No pages data found")
        return 0

    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.pages"

    schema = [
        bigquery.SchemaField("snapshot_time", "TIMESTAMP"),
        bigquery.SchemaField("url", "STRING"),
        bigquery.SchemaField("visits", "INTEGER"),
    ]

    table = bigquery.Table(table_id, schema=schema)
    table = client.create_table(table, exists_ok=True)

    now = datetime.utcnow().isoformat()
    rows = [
        {"snapshot_time": now, "url": item['url'], "visits": item['visits']}
        for item in items
    ]

    errors = client.insert_rows_json(table_id, rows)
    if errors:
        log(f"  Errors inserting pages: {errors}")
        return 0

    log(f"  Saved {len(items)} rows to pages")
    return len(items)


@functions_framework.http
def sync_clarity(request):
    """
    HTTP Cloud Function entry point.

    Can be triggered by:
    - Cloud Scheduler (daily cron)
    - Manual HTTP request

    Query params:
    - days: Number of days to fetch (1-3, default 3)
    """
    log("=" * 60)
    log("Clarity -> BigQuery Sync (Cloud Function)")
    log("=" * 60)

    # Parse request
    request_json = request.get_json(silent=True)
    request_args = request.args

    num_days = 3  # Default to max (72h)
    if request_args and 'days' in request_args:
        num_days = min(3, max(1, int(request_args['days'])))
    elif request_json and 'days' in request_json:
        num_days = min(3, max(1, int(request_json['days'])))

    log(f"Project ID: {CLARITY_PROJECT_ID}")
    log(f"GCP Project: {GCP_PROJECT_ID}")
    log(f"BigQuery Dataset: {BQ_DATASET}")
    log(f"Period: last {num_days * 24} hours")
    log("-" * 60)

    try:
        # Fetch Clarity data
        log("Fetching Clarity data...")
        data = fetch_clarity_data(num_days=num_days)
        log(f"  Got {len(data)} metric groups")

        # Initialize BigQuery client
        log("Connecting to BigQuery...")
        client = bigquery.Client(project=GCP_PROJECT_ID)

        # Ensure dataset exists
        ensure_dataset_exists(client)

        log("-" * 60)

        # Sync each dataset
        total_rows = 0
        total_rows += sync_snapshot(client, data, num_days)
        total_rows += sync_dimension(client, data, 'Device', 'devices')
        total_rows += sync_dimension(client, data, 'Country', 'countries')
        total_rows += sync_dimension(client, data, 'Browser', 'browsers')
        total_rows += sync_dimension(client, data, 'OS', 'os')
        total_rows += sync_pages(client, data)

        log("-" * 60)
        log(f"DONE! Synced {total_rows} total rows")
        log("=" * 60)

        return {
            "status": "success",
            "rows_synced": total_rows,
            "period_hours": num_days * 24,
            "timestamp": datetime.utcnow().isoformat()
        }, 200

    except requests.exceptions.HTTPError as e:
        error_msg = f"Clarity API error: {e}"
        if e.response is not None:
            error_msg += f" - {e.response.text}"
        log(f"ERROR: {error_msg}")
        return {"status": "error", "message": error_msg}, 500

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}, 500


# For local testing
if __name__ == "__main__":
    from unittest.mock import Mock

    # Load .env for local testing
    from dotenv import load_dotenv
    load_dotenv()

    # Mock request
    mock_request = Mock()
    mock_request.get_json.return_value = None
    mock_request.args = {}

    result, status = sync_clarity(mock_request)
    print(f"\nResult: {json.dumps(result, indent=2)}")
    print(f"Status: {status}")
