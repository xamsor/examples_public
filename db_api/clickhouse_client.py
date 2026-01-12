#!/usr/bin/env python3
"""
ClickHouse client for querying fatgrid_logs_prod_db

Database: fatgrid_logs_prod_db
Host: 5.161.52.116:8123 (HTTP interface)
User: readonly_user

Usage:
    python clickhouse_client.py                    # List tables
    python clickhouse_client.py "SELECT * FROM logs LIMIT 10"
    python clickhouse_client.py tables             # List all tables with row counts
    python clickhouse_client.py describe <table>   # Show table schema
"""

import os
import sys
import json
import csv
from io import StringIO
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

# ClickHouse configuration
CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', '5.161.52.116')
CLICKHOUSE_PORT = os.getenv('CLICKHOUSE_PORT', '8123')
CLICKHOUSE_DB = os.getenv('CLICKHOUSE_DB', 'fatgrid_logs_prod_db')
CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'readonly_user')
CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', 'NLhNJWBR2zRw')


class ClickHouseClient:
    def __init__(self, host=None, port=None, database=None, user=None, password=None):
        self.host = host or CLICKHOUSE_HOST
        self.port = port or CLICKHOUSE_PORT
        self.database = database or CLICKHOUSE_DB
        self.user = user or CLICKHOUSE_USER
        self.password = password or CLICKHOUSE_PASSWORD
        self.base_url = f"http://{self.host}:{self.port}"

    def query(self, sql, format='JSONEachRow'):
        """Execute a query and return results"""
        params = {
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'query': sql,
            'default_format': format
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            if format == 'JSONEachRow':
                lines = response.text.strip().split('\n')
                return [json.loads(line) for line in lines if line]
            elif format == 'TabSeparated':
                return response.text
            else:
                return response.text

        except requests.exceptions.RequestException as e:
            print(f"Query failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return None

    def list_tables(self):
        """List all tables in the database"""
        sql = "SHOW TABLES"
        result = self.query(sql, format='TabSeparated')
        if result:
            tables = [t.strip() for t in result.strip().split('\n') if t.strip()]
            return tables
        return []

    def describe_table(self, table_name):
        """Get table schema"""
        sql = f"DESCRIBE TABLE {table_name}"
        return self.query(sql)

    def table_stats(self):
        """Get row counts for all tables"""
        tables = self.list_tables()
        stats = []
        for table in tables:
            count_result = self.query(f"SELECT count() as cnt FROM {table}")
            if count_result:
                count = count_result[0].get('cnt', 0)
                stats.append({'table': table, 'rows': count})
        return stats

    def export_to_csv(self, sql, filename):
        """Export query results to CSV"""
        results = self.query(sql)
        if not results:
            print("No results to export")
            return False

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)

        print(f"Exported to {filename}")
        return True

    def export_to_json(self, sql, filename):
        """Export query results to JSON"""
        results = self.query(sql)
        if not results:
            print("No results to export")
            return False

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        print(f"Exported to {filename}")
        return True


def main():
    client = ClickHouseClient()

    if len(sys.argv) < 2:
        # Default: list tables with stats
        print(f"ClickHouse Database: {CLICKHOUSE_DB}")
        print(f"Host: {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}")
        print(f"User: {CLICKHOUSE_USER}")
        print("-" * 50)

        print("\nTables:")
        stats = client.table_stats()
        for s in stats:
            print(f"  {s['table']:<40} {s['rows']:>15,} rows")
        return

    cmd = sys.argv[1]

    if cmd == 'tables':
        # List tables with row counts
        stats = client.table_stats()
        print(f"\nTables in {CLICKHOUSE_DB}:")
        for s in stats:
            print(f"  {s['table']:<40} {s['rows']:>15,} rows")

    elif cmd == 'describe' and len(sys.argv) > 2:
        # Describe table schema
        table = sys.argv[2]
        schema = client.describe_table(table)
        if schema:
            print(f"\nSchema for {table}:")
            print("-" * 60)
            for col in schema:
                print(f"  {col.get('name', ''):<30} {col.get('type', '')}")

    elif cmd.upper().startswith('SELECT'):
        # Execute custom query
        results = client.query(cmd)
        if results:
            print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        else:
            print("No results")

    else:
        # Treat as SQL query
        results = client.query(cmd)
        if results:
            print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        else:
            print("No results or invalid command")
            print("\nUsage:")
            print("  python clickhouse_client.py                     # List tables")
            print("  python clickhouse_client.py tables              # Tables with row counts")
            print("  python clickhouse_client.py describe <table>    # Table schema")
            print('  python clickhouse_client.py "SELECT * FROM x"   # Run query')


if __name__ == "__main__":
    main()
