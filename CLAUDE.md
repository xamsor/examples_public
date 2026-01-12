# Business Logic Workspace

Local tools for data analysis, meeting transcripts, and cross-source analytics.

## IMPORTANT: Rules for Claude

1. **Always read before writing**: Before modifying any file, ALWAYS read it first using the Read tool. Never assume file contents.

2. **DuckDB first**: Always query `warehouse.duckdb` first. It contains synced data from:
   - ClickHouse: `ch_user_activity_logs`, `ch_resources_modal_opens`, `ch_not_found_domains`
   - MongoDB: `mongo_users`, `mongo_subscriptions`, `mongo_payments`, `mongo_companies`, `mongo_orders`, `mongo_user_unlocks`
   - Analytics: `ga4_*`, `gsc_*`, `bq_clarity_*` tables

   **Only query remote sources directly for**:
   - ClickHouse large tables: `domain_history` (7.6GB), `price_history` (253MB)
   - Real-time data when DuckDB is stale (sync first if needed)

3. **Sync before analysis**: If user asks for most recent data, run sync first:
   ```bash
   python3 db_api/clickhouse_to_duckdb.py  # ClickHouse → DuckDB (3 small tables)
   python3 db_api/sync_mongo.py            # MongoDB → DuckDB (all collections)
   python3 db_api/sync_clickup.py          # ClickUp Orders → DuckDB
   ```

4. **Never assume database schemas**: Before writing queries:
   - Use `DESCRIBE table_name` in DuckDB
   - Never guess column names or table structures

5. **Use python3**: Always use `python3` command, not `python`.

## Folder Structure

```
business_logic/
├── .env                          # API keys (gitignored)
├── warehouse.duckdb              # Local DuckDB database
├── db_api/                       # API & database clients
│   ├── clickhouse_client.py      # ClickHouse database client
│   ├── clickup_client.py         # ClickUp API client
│   ├── duckdb_warehouse.py       # Local DuckDB warehouse wrapper
│   ├── mongo_export.py           # MongoDB export to CSV/JSON
│   └── mongo_test.py             # MongoDB connection test
├── cloud_functions/              # GCP Cloud Functions
│   └── clarity_sync/             # Clarity → BigQuery (daily cron)
├── fathom_data/                  # Fathom meeting transcripts & RAG
│   └── fathom_sync.md            # Full documentation
└── qdrant_data/                  # Vector embeddings for RAG
```

## fathom_data/ - Meeting Transcript RAG

Syncs Fathom meeting transcripts, embeds them into Qdrant, and provides semantic search + Q&A.

See [fathom_data/fathom_sync.md](fathom_data/fathom_sync.md) for full documentation.

Quick commands:
```bash
python fathom_data/fathom_sync.py sync-embed  # Sync & embed new transcripts
python fathom_data/fathom_sync.py ask         # Interactive Q&A
python fathom_data/fathom_sync.py status      # Show sync status
```

## db_api/ - Database & API Clients

| File | Purpose |
|------|---------|
| `duckdb_warehouse.py` | **PRIMARY** - Local DuckDB warehouse for all analytics |
| `clickhouse_to_duckdb.py` | Sync ClickHouse → DuckDB |
| `sync_mongo.py` | Sync MongoDB → DuckDB |
| `sync_clickup.py` | Sync ClickUp Orders → DuckDB |
| `clickhouse_client.py` | Direct ClickHouse queries (large tables only) |
| `clickup_client.py` | ClickUp API client |

### DuckDB Local Warehouse (PRIMARY)

**All queries should use DuckDB first.** Contains synced data from ClickHouse + MongoDB.

```bash
python3 db_api/duckdb_warehouse.py  # Show all tables
```

```python
from db_api.duckdb_warehouse import Warehouse
wh = Warehouse()
wh.query("SELECT * FROM mongo_users LIMIT 10")
wh.query("SELECT * FROM ch_user_activity_logs WHERE date >= '2025-01-01'")
```

**DuckDB Tables:**
| Prefix | Source | Tables |
|--------|--------|--------|
| `ch_` | ClickHouse | `ch_user_activity_logs`, `ch_resources_modal_opens`, `ch_not_found_domains` |
| `mongo_` | MongoDB | `mongo_users`, `mongo_subscriptions`, `mongo_payments`, `mongo_companies`, `mongo_orders`, `mongo_user_unlocks`, `mongo_internal_payments`, `mongo_projects`, `mongo_project_prospects`, `mongo_project_completed_orders` |
| `clickup_` | ClickUp | `clickup_orders`, `clickup_order_comments`, `clickup_order_attachments` |
| `ga4_` | Google Analytics | `ga4_daily`, `ga4_pages`, `ga4_countries`, `ga4_sources` |

### Order Data: Two Sources

Orders (backlink purchases) are tracked in **two systems** with different purposes:

| Source | Table | Purpose | Coverage |
|--------|-------|---------|----------|
| **MongoDB** | `mongo_orders` | Payment/transaction data | All 222 orders (including 131 abandoned carts) |
| **ClickUp** | `clickup_orders` | Fulfillment workflow | 89 orders in active fulfillment |

**Key insight**: Only 84 orders exist in both sources. The gap is:
- 138 MongoDB-only orders are mostly `created` status (abandoned carts, never reached fulfillment)
- 5 ClickUp-only entries are manual user requests (not platform orders)

**To join both sources**:
```sql
SELECT m.order_id, m.domain, m.buyer_email, m.price,
       m.payment_status, c.status as fulfillment_status
FROM mongo_orders m
JOIN clickup_orders c ON m.order_id = c.order_number
ORDER BY m.order_id DESC
```

**Order lifecycle**:
- MongoDB: `created` → `order_submitted` → `requires_capture` → `accepted_by_seller` → `paid` → `published`
- ClickUp: `new orders` → `outreach` → `review + capture` → `sent to seller/marketplace` → `completed`
| `gsc_` | Search Console | `gsc_daily`, `gsc_queries`, `gsc_pages`, `gsc_countries` |
| `bq_clarity_` | Clarity/BigQuery | `bq_clarity_pages`, `bq_clarity_countries`, etc. |

### ClickHouse (Remote) - Large Tables Only

Only use for tables too large to sync:
- `domain_history` (7.6 GB, 166M rows)
- `price_history` (253 MB, 35M rows)

```bash
python3 db_api/clickhouse_client.py "SELECT * FROM domain_history WHERE domain = 'example.com'"
```

## Remote Database Access

### ClickHouse
- **Host**: 5.161.52.116:8123 (HTTP)
- **Database**: `fatgrid_logs_prod_db`
- **User**: `readonly_user`

### MongoDB

#### Publishers DB
- **Host**: 116.203.48.70:27017
- **Database**: `publishers`
- **User**: `pub_w`

#### GetLinks Pro Prod
- **Host**: 5.161.52.116:27018
- **Database**: `getlinks_pro_prod`
- **User**: `read_user`

### PostgreSQL (Crawler)
- **Host**: 5.78.129.138:5432
- **Database**: `fg_crawler`
- **User**: `max_viewer`

## Environment Variables (.env)

```
# Fathom
FATHOM_API_KEY=...
FATHOM_WEBHOOK_SECRET=...

# OpenAI (for RAG embeddings)
OPENAI_API_KEY=...

# ClickUp
CLICKUP_API_KEY=...

# MongoDB
MONGO_URI=mongodb://...           # GetLinks Pro Prod
MONGO_PUBLISHERS_URI=mongodb://...

# ClickHouse
CLICKHOUSE_HOST=5.161.52.116
CLICKHOUSE_PORT=8123
CLICKHOUSE_DB=fatgrid_logs_prod_db
CLICKHOUSE_USER=readonly_user
CLICKHOUSE_PASSWORD=...

# PostgreSQL
OLEG_POSTGRES_URI=postgresql://...

# Microsoft Clarity
CLARITY_PROJECT_ID=pf8kyjwawu
CLARITY_API_TOKEN=...
```

## Data Collection Strategy

GSC and GA4 use direct API sync (rich pre-aggregated dimensions). Clarity syncs from BigQuery (automated via Cloud Function). Use `bq_clarity_*` tables for Clarity data.

```bash
python3 db_api/sync_gsc.py --days 30    # GSC
python3 db_api/sync_ga4.py --days 30    # GA4
python3 db_api/sync_bigquery.py --source clarity  # Clarity (if needed)
```

## BigQuery Pipelines

Analytics data flows automatically to BigQuery. See [bigquery.md](bigquery.md) for setup details.

| Source | Dataset | Schedule |
|--------|---------|----------|
| GA4 | `fatgrid_analytics` | Daily + streaming (native) |
| GSC | `searchconsole_fatgrid` | Daily (native) |
| Clarity | `clarity` | Daily 6 AM UTC (Cloud Function) |

Cloud Function URL: https://us-central1-getlinkspro-453615.cloudfunctions.net/clarity-sync
