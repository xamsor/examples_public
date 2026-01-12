#!/usr/bin/env python3
"""
ClickHouse → DuckDB incremental sync

Syncs all ClickHouse tables to local DuckDB warehouse with:
- Incremental updates (only new data)
- Progress reporting with ETA
- Speed measurement

Usage:
    python clickhouse_to_duckdb.py           # Sync all tables
    python clickhouse_to_duckdb.py status    # Show sync status
    python clickhouse_to_duckdb.py table_name  # Sync specific table
"""

import os
import sys
import time
import json

import duckdb
import requests
from dotenv import load_dotenv

load_dotenv()

# ClickHouse config
CH_HOST = os.getenv('CLICKHOUSE_HOST', '5.161.52.116')
CH_PORT = os.getenv('CLICKHOUSE_PORT', '8123')
CH_DB = os.getenv('CLICKHOUSE_DB', 'fatgrid_logs_prod_db')
CH_USER = os.getenv('CLICKHOUSE_USER', 'readonly_user')
CH_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', 'NLhNJWBR2zRw')

# DuckDB config
DUCKDB_PATH = os.path.join(os.path.dirname(__file__), '..', 'warehouse.duckdb')

# Table configs: table_name -> (timestamp_column, batch_size, sync_by_day)
# Only sync manageable tables (<50MB). Large tables query directly from ClickHouse:
#   - domain_history: 7.66 GB, 166M rows - query ClickHouse directly
#   - price_history: 253 MB, 35M rows - query ClickHouse directly
TABLES = {
    'user_activity_logs': ('timestamp', 50000, False),      # 29 MB, 662K rows
    'resources_modal_opens': ('timestamp', 50000, False),   # 1 MB, 37K rows
    'not_found_domains': ('created_at', 50000, False),      # 5 MB, 412K rows
}


def ch_query(sql, timeout=300):
    """Execute ClickHouse query"""
    params = {
        'database': CH_DB,
        'user': CH_USER,
        'password': CH_PASSWORD,
        'query': sql,
        'default_format': 'JSONEachRow'
    }
    resp = requests.get(f"http://{CH_HOST}:{CH_PORT}", params=params, timeout=timeout)
    resp.raise_for_status()
    lines = resp.text.strip().split('\n')
    return [json.loads(line) for line in lines if line]


def ch_query_batch(sql, limit, offset, timeout=120):
    """Query ClickHouse with LIMIT/OFFSET for reliability"""
    paginated_sql = f"{sql} LIMIT {limit} OFFSET {offset}"
    params = {
        'database': CH_DB,
        'user': CH_USER,
        'password': CH_PASSWORD,
        'query': paginated_sql,
        'default_format': 'JSONEachRow'
    }
    for attempt in range(3):
        try:
            resp = requests.get(f"http://{CH_HOST}:{CH_PORT}", params=params, timeout=timeout)
            resp.raise_for_status()
            lines = resp.text.strip().split('\n')
            return [json.loads(line) for line in lines if line]
        except Exception as e:
            if attempt == 2:
                raise
            print(f"\n  Retry {attempt+1}/3: {e}")
            time.sleep(2)
    return []


def get_ch_table_info(table):
    """Get ClickHouse table row count and date range"""
    ts_col = TABLES[table][0]
    result = ch_query(f"SELECT count() as cnt, min({ts_col}) as min_ts, max({ts_col}) as max_ts FROM {table}")
    if result:
        return result[0]
    return None


def get_duckdb_max_timestamp(conn, table, ts_col):
    """Get max timestamp from DuckDB table"""
    try:
        result = conn.execute(f"SELECT max({ts_col}) FROM ch_{table}").fetchone()
        if result and result[0]:
            return result[0]
    except:
        pass
    return None


def get_ch_schema(table):
    """Get ClickHouse table schema"""
    return ch_query(f"DESCRIBE {table}")


def create_duckdb_table(conn, table):
    """Create DuckDB table from ClickHouse schema"""
    # Map ClickHouse types to DuckDB
    type_map = {
        'UInt8': 'UTINYINT',
        'UInt16': 'USMALLINT',
        'UInt32': 'UINTEGER',
        'UInt64': 'UBIGINT',
        'Int8': 'TINYINT',
        'Int16': 'SMALLINT',
        'Int32': 'INTEGER',
        'Int64': 'BIGINT',
        'Float32': 'FLOAT',
        'Float64': 'DOUBLE',
        'String': 'VARCHAR',
        'DateTime': 'TIMESTAMP',
        'Date': 'DATE',
        'UUID': 'VARCHAR',
    }

    schema = get_ch_schema(table)
    columns = []
    for col in schema:
        name = col['name']
        ch_type = col['type']

        # Handle Nullable types
        if ch_type.startswith('Nullable('):
            ch_type = ch_type[9:-1]  # Extract inner type

        duck_type = type_map.get(ch_type, 'VARCHAR')
        columns.append(f'"{name}" {duck_type}')

    ddl = f"CREATE TABLE IF NOT EXISTS ch_{table} ({', '.join(columns)})"
    conn.execute(ddl)


def format_time(seconds):
    """Format seconds to human readable"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def format_number(n):
    """Format number with K/M suffix"""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def sync_table(conn, table, full_sync=False):
    """Sync a single table from ClickHouse to DuckDB"""
    ts_col, _, sync_by_day = TABLES[table]

    # Use day-by-day sync for large tables
    if sync_by_day:
        return sync_table_by_day(conn, table, ts_col)
    else:
        return sync_table_offset(conn, table, full_sync)


def sync_table_by_day(conn, table, ts_col):
    """Sync large table day by day to avoid OFFSET on huge datasets"""
    # Get date range
    ch_info = get_ch_table_info(table)
    if not ch_info:
        print(f"  ✗ Failed to get info for {table}")
        return False

    print(f"\n{'='*60}")
    print(f"TABLE: {table} (syncing by day)")
    print(f"  ClickHouse: {format_number(ch_info['cnt'])} rows ({ch_info['min_ts']} → {ch_info['max_ts']})")

    # Get list of dates to sync
    max_ts = get_duckdb_max_timestamp(conn, table, ts_col)

    if max_ts:
        print(f"  DuckDB max: {max_ts}")
        date_filter = f"WHERE toDate({ts_col}) >= toDate('{max_ts}')"
    else:
        print(f"  DuckDB: empty (full sync)")
        conn.execute(f"DROP TABLE IF EXISTS ch_{table}")
        create_duckdb_table(conn, table)
        date_filter = ""

    # Get dates and row counts
    dates_result = ch_query(f"""
        SELECT toDate({ts_col}) as d, count() as cnt
        FROM {table} {date_filter}
        GROUP BY d ORDER BY d
    """)

    if not dates_result:
        print("  ✓ Already up to date")
        return True

    total_rows = sum(d['cnt'] for d in dates_result)
    total_days = len(dates_result)
    print(f"  Days to sync: {total_days}, Rows: {format_number(total_rows)}")
    print()

    start_time = time.time()
    rows_synced = 0
    days_done = 0

    for day_info in dates_result:
        day = day_info['d']
        day_rows = day_info['cnt']

        # For the first day (if incremental), filter by exact timestamp
        if max_ts and day == str(max_ts)[:10]:
            query = f"SELECT * FROM {table} WHERE {ts_col} > '{max_ts}'"
        else:
            query = f"SELECT * FROM {table} WHERE toDate({ts_col}) = '{day}'"

        # Fetch day's data
        day_data = ch_query(query, timeout=600)

        if day_data:
            conn.executemany(
                f"INSERT INTO ch_{table} VALUES ({','.join(['?']*len(day_data[0]))})",
                [tuple(r.values()) for r in day_data]
            )
            rows_synced += len(day_data)

        days_done += 1

        # Progress
        elapsed = time.time() - start_time
        speed = rows_synced / elapsed if elapsed > 0 else 0
        pct = rows_synced / total_rows * 100 if total_rows > 0 else 100
        eta = (total_rows - rows_synced) / speed if speed > 0 else 0

        print(f"  [{pct:5.1f}%] Day {days_done}/{total_days} ({day}) | {format_number(rows_synced)}/{format_number(total_rows)} | {format_number(speed)}/s | ETA: {format_time(eta)}", flush=True)

    elapsed = time.time() - start_time
    speed = rows_synced / elapsed if elapsed > 0 else 0
    print(f"  ✓ Done: {format_number(rows_synced)} rows in {format_time(elapsed)} ({format_number(speed)}/s)")

    return True


def sync_table_offset(conn, table, full_sync=False):
    """Sync table using OFFSET pagination (for smaller tables)"""
    ts_col, batch_size, _ = TABLES[table]

    # Get ClickHouse stats
    ch_info = get_ch_table_info(table)
    if not ch_info:
        print(f"  ✗ Failed to get info for {table}")
        return False

    total_rows = ch_info['cnt']
    print(f"\n{'='*60}")
    print(f"TABLE: {table}")
    print(f"  ClickHouse: {format_number(total_rows)} rows ({ch_info['min_ts']} → {ch_info['max_ts']})")

    # Get DuckDB max timestamp for incremental sync
    max_ts = None
    if not full_sync:
        max_ts = get_duckdb_max_timestamp(conn, table, ts_col)

    if max_ts:
        # Incremental sync
        count_result = ch_query(f"SELECT count() as cnt FROM {table} WHERE {ts_col} > '{max_ts}'")
        rows_to_sync = count_result[0]['cnt'] if count_result else 0
        print(f"  DuckDB max: {max_ts}")
        print(f"  New rows: {format_number(rows_to_sync)}")

        if rows_to_sync == 0:
            print(f"  ✓ Already up to date")
            return True

        query = f"SELECT * FROM {table} WHERE {ts_col} > '{max_ts}' ORDER BY {ts_col}"
    else:
        # Full sync
        rows_to_sync = total_rows
        print(f"  DuckDB: empty (full sync)")
        query = f"SELECT * FROM {table} ORDER BY {ts_col}"

        # Drop and recreate table
        conn.execute(f"DROP TABLE IF EXISTS ch_{table}")

    # Sync with progress
    print(f"  Syncing {format_number(rows_to_sync)} rows...")
    print()

    start_time = time.time()
    last_print_time = 0
    rows_synced = 0
    offset = 0
    table_created = max_ts is not None  # Table exists if we have max_ts

    # Create table before starting
    if not table_created:
        create_duckdb_table(conn, table)
        table_created = True

    while offset < rows_to_sync:
        # Fetch batch
        batch = ch_query_batch(query, batch_size, offset)

        if not batch:
            break

        # Insert batch
        conn.executemany(
            f"INSERT INTO ch_{table} VALUES ({','.join(['?']*len(batch[0]))})",
            [tuple(r.values()) for r in batch]
        )
        rows_synced += len(batch)
        offset += len(batch)

        # Progress - print every 10 seconds
        elapsed = time.time() - start_time
        speed = rows_synced / elapsed if elapsed > 0 else 0
        pct = rows_synced / rows_to_sync * 100
        eta = (rows_to_sync - rows_synced) / speed if speed > 0 else 0

        if elapsed - last_print_time >= 10 or rows_synced == len(batch):
            print(f"  [{pct:5.1f}%] {format_number(rows_synced)}/{format_number(rows_to_sync)} | {format_number(speed)}/s | ETA: {format_time(eta)}", flush=True)
            last_print_time = elapsed

        # Stop if we got fewer rows than requested (end of data)
        if len(batch) < batch_size:
            break

    elapsed = time.time() - start_time
    speed = rows_synced / elapsed if elapsed > 0 else 0

    print(f"\r  ✓ Done: {format_number(rows_synced)} rows in {format_time(elapsed)} ({format_number(speed)}/s)         ")

    return True


def show_status(conn):
    """Show sync status for all tables"""
    print(f"\n{'='*70}")
    print("SYNC STATUS")
    print(f"{'='*70}")
    print(f"{'Table':<25} {'ClickHouse':>12} {'DuckDB':>12} {'Behind':>12}")
    print('-'*70)

    for table, (ts_col, _, _) in TABLES.items():
        ch_info = get_ch_table_info(table)
        ch_rows = ch_info['cnt'] if ch_info else 0

        try:
            duck_result = conn.execute(f"SELECT count(*) FROM ch_{table}").fetchone()
            duck_rows = duck_result[0] if duck_result else 0
        except:
            duck_rows = 0

        behind = ch_rows - duck_rows
        behind_str = format_number(behind) if behind > 0 else "✓"

        print(f"{table:<25} {format_number(ch_rows):>12} {format_number(duck_rows):>12} {behind_str:>12}")

    print(f"{'='*70}")


def main():
    # Connect to DuckDB
    conn = duckdb.connect(DUCKDB_PATH)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == 'status':
            show_status(conn)
            return

        if cmd in TABLES:
            # Sync specific table
            sync_table(conn, cmd)
            conn.close()
            return

        print(f"Unknown command: {cmd}")
        print(f"Available tables: {', '.join(TABLES.keys())}")
        return

    # Sync all tables
    print(f"\nClickHouse → DuckDB Sync")
    print(f"Source: {CH_HOST}:{CH_PORT}/{CH_DB}")
    print(f"Target: {DUCKDB_PATH}")

    total_start = time.time()

    for table in TABLES:
        sync_table(conn, table)

    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"TOTAL TIME: {format_time(total_elapsed)}")

    # Show final status
    show_status(conn)

    conn.close()


if __name__ == "__main__":
    main()
