# DuckDB Sync Guide

Sync all data sources to local `warehouse.duckdb`.

## Quick Full Sync

```bash
# Run all core syncs (ClickHouse + MongoDB + ClickUp)
python3 db_api/clickhouse_to_duckdb.py && python3 db_api/sync_mongo.py && python3 db_api/sync_clickup.py
```

## Full Sync (All Sources)

```bash
# 1. ClickHouse → DuckDB (activity logs, modal opens, not-found domains)
python3 db_api/clickhouse_to_duckdb.py

# 2. MongoDB → DuckDB (users, subscriptions, payments, orders, projects, etc.)
python3 db_api/sync_mongo.py

# 3. ClickUp → DuckDB (order tasks, comments, attachments)
python3 db_api/sync_clickup.py

# 4. Google Search Console → DuckDB (last 30 days)
python3 db_api/sync_gsc.py --days 30

# 5. Google Analytics 4 → DuckDB (last 30 days)
python3 db_api/sync_ga4.py --days 30

# 6. Clarity (from BigQuery) → DuckDB
python3 db_api/sync_bigquery.py --source clarity
```

## One-Liner (All Sources)

```bash
python3 db_api/clickhouse_to_duckdb.py && \
python3 db_api/sync_mongo.py && \
python3 db_api/sync_clickup.py && \
python3 db_api/sync_gsc.py --days 30 && \
python3 db_api/sync_ga4.py --days 30 && \
python3 db_api/sync_bigquery.py --source clarity
```

---

## Sync Details

| Script | Tables | Strategy | Notes |
|--------|--------|----------|-------|
| `clickhouse_to_duckdb.py` | `ch_user_activity_logs`, `ch_resources_modal_opens`, `ch_not_found_domains` | REPLACE | Full refresh, drops and recreates |
| `sync_mongo.py` | `mongo_users`, `mongo_subscriptions`, `mongo_payments`, `mongo_companies`, `mongo_orders`, `mongo_user_unlocks`, `mongo_internal_payments`, `mongo_projects`, `mongo_project_prospects`, `mongo_project_completed_orders` | REPLACE | Full refresh, drops and recreates |
| `sync_clickup.py` | `clickup_orders`, `clickup_order_comments`, `clickup_order_attachments` | REPLACE | Full refresh, drops and recreates |
| `sync_gsc.py` | `gsc_daily`, `gsc_queries`, `gsc_pages`, `gsc_countries` | UPSERT | Incremental by date, use `--days N` |
| `sync_ga4.py` | `ga4_daily`, `ga4_pages`, `ga4_countries`, `ga4_sources` | UPSERT | Incremental by date, use `--days N` |
| `sync_bigquery.py` | `bq_clarity_pages`, `bq_clarity_countries`, etc. | REPLACE | Full refresh from BigQuery |

---

## When to Sync

- **Before analysis**: Always sync if you need fresh data
- **Daily recommended**: Run full sync once per day for up-to-date metrics
- **After bulk operations**: Sync after major data changes in source systems

## Large Tables (Not Synced)

These ClickHouse tables are too large to sync locally. Query directly:

| Table | Size | Rows |
|-------|------|------|
| `domain_history` | 7.6 GB | 166M |
| `price_history` | 253 MB | 35M |

```bash
python3 db_api/clickhouse_client.py "SELECT * FROM domain_history WHERE domain = 'example.com'"
```

---

## Verify Sync

```bash
# Show all tables and row counts
python3 db_api/duckdb_warehouse.py
```
