"""
Local DuckDB data warehouse for cross-source analytics.

Sources:
- MongoDB (Publishers, GetLinks Pro)
- ClickHouse (FatGrid logs)
- Google Search Console (direct API)
- Google Analytics (direct API)
- Google BigQuery (Clarity, GSC SERP features, future GA4 events)

Usage:
    from duckdb_warehouse import Warehouse

    wh = Warehouse()
    wh.query("SELECT * FROM mongo_sites LIMIT 10")
    wh.load_parquet("exports/ga_data.parquet", "google_analytics")
"""

import duckdb
from pathlib import Path
from typing import Optional
import json


class Warehouse:
    """Local DuckDB warehouse for behavioral analytics."""

    def __init__(self, db_path: str = "warehouse.duckdb"):
        self.db_path = Path(db_path)
        self.conn = duckdb.connect(str(self.db_path))
        self._setup()

    def _setup(self):
        """Initialize warehouse with useful extensions."""
        # Enable useful extensions
        self.conn.execute("INSTALL httpfs; LOAD httpfs;")
        self.conn.execute("INSTALL json; LOAD json;")
        print(f"Warehouse ready: {self.db_path} ({self._get_size()})")

    def _get_size(self) -> str:
        """Get database file size."""
        if self.db_path.exists():
            size = self.db_path.stat().st_size
            if size < 1024:
                return f"{size}B"
            elif size < 1024**2:
                return f"{size/1024:.1f}KB"
            elif size < 1024**3:
                return f"{size/1024**2:.1f}MB"
            else:
                return f"{size/1024**3:.2f}GB"
        return "0B"

    def query(self, sql: str):
        """Run a query and return results as a relation."""
        return self.conn.sql(sql)

    def execute(self, sql: str):
        """Execute a statement (no results)."""
        self.conn.execute(sql)

    def load_parquet(self, path: str, table_name: str, replace: bool = True):
        """Load a Parquet file into a table."""
        mode = "OR REPLACE" if replace else ""
        self.conn.execute(f"CREATE {mode} TABLE {table_name} AS SELECT * FROM '{path}'")
        count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"Loaded {count:,} rows into {table_name}")

    def load_csv(self, path: str, table_name: str, replace: bool = True, **options):
        """Load a CSV file into a table."""
        mode = "OR REPLACE" if replace else ""
        opts = ", ".join(f"{k}={repr(v)}" for k, v in options.items())
        read_opts = f", {opts}" if opts else ""
        self.conn.execute(f"CREATE {mode} TABLE {table_name} AS SELECT * FROM read_csv('{path}'{read_opts})")
        count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"Loaded {count:,} rows into {table_name}")

    def load_json(self, path: str, table_name: str, replace: bool = True):
        """Load a JSON/JSONL file into a table."""
        mode = "OR REPLACE" if replace else ""
        self.conn.execute(f"CREATE {mode} TABLE {table_name} AS SELECT * FROM read_json_auto('{path}')")
        count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"Loaded {count:,} rows into {table_name}")

    def load_dataframe(self, df, table_name: str, replace: bool = True):
        """Load a pandas DataFrame into a table."""
        mode = "OR REPLACE" if replace else ""
        self.conn.execute(f"CREATE {mode} TABLE {table_name} AS SELECT * FROM df")
        count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"Loaded {count:,} rows into {table_name}")

    def tables(self) -> list:
        """List all tables in the warehouse."""
        result = self.conn.execute("""
            SELECT table_name,
                   estimated_size as size_bytes,
                   column_count
            FROM duckdb_tables()
            ORDER BY table_name
        """).fetchall()
        return result

    def describe(self, table_name: str):
        """Show table schema."""
        return self.conn.sql(f"DESCRIBE {table_name}")

    def export_parquet(self, table_or_query: str, path: str):
        """Export a table or query result to Parquet."""
        if " " in table_or_query:  # It's a query
            self.conn.execute(f"COPY ({table_or_query}) TO '{path}' (FORMAT PARQUET)")
        else:  # It's a table name
            self.conn.execute(f"COPY {table_or_query} TO '{path}' (FORMAT PARQUET)")
        print(f"Exported to {path}")

    def close(self):
        """Close the connection."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Quick test
if __name__ == "__main__":
    wh = Warehouse()

    # Show available tables
    tables = wh.tables()
    if tables:
        print("\nTables:")
        for name, size, cols in tables:
            print(f"  {name}: {cols} columns, {size or 'unknown'} bytes")
    else:
        print("\nNo tables yet. Load data with:")
        print("  wh.load_csv('file.csv', 'table_name')")
        print("  wh.load_parquet('file.parquet', 'table_name')")
        print("  wh.load_json('file.json', 'table_name')")

    wh.close()
