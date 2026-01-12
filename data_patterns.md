# Data Patterns & Lookup Reference

Quick reference for analyzing user behavior and product usage.

## ClickHouse Tables (fatgrid_logs_prod_db)

### 1. Filter Usage (user_activity_logs)
Track which filters users apply when searching domains.

```sql
-- Get all filter usage from domain list API
SELECT email, url
FROM user_activity_logs
WHERE url LIKE '/api/domains/list%'

-- URL params to UI filter mapping:
-- minPrice, maxPrice        → Best Price
-- minDr, maxDr              → DR
-- minAs, maxAs              → AS
-- minTotalOrganicTraffic, maxTotalOrganicTraffic → Organic Traffic (Total)
-- minMonthlyOrganicTraffic  → Min Monthly Organic Traffic
-- categories, niches        → Category
-- languages                 → Languages
-- keyword, search           → Keyword Match
-- databases                 → Top Country by Organic Traffic
-- linkFollow                → Link Follow
-- sponsored                 → Sponsored
-- resources                 → Sellers
-- containsDatabase          → Country Traffic Present
-- type                      → Link Type (default: guest_post)
-- favorites                 → Favorites
-- blocks                    → Blacklist
-- tags                      → Tags
-- withNote                  → Notes
-- isVerifiedByPlatform      → Verified
-- createdAtFrom, createdAtTo → Creation Date
-- projects                  → Projects
```

### 2. Sensitive Scope / Domain Details (resources_modal_opens)
Track when users open the domain detail popup (Sensitive Scope).

```sql
-- Total usage
SELECT count() as opens, count(DISTINCT email) as users
FROM resources_modal_opens
WHERE email IS NOT NULL

-- Top users by opens
SELECT email, count() as opens
FROM resources_modal_opens
WHERE email IS NOT NULL
GROUP BY email
ORDER BY opens DESC

-- Columns: id, user_id, email, domain, type (guest_post/link_insertion), timestamp, date
```

### 3. Domain History (domain_history)
Track domain metric changes over time.

```sql
DESCRIBE domain_history
```

### 4. Price History (price_history)
Track price changes for domains.

```sql
DESCRIBE price_history
```

### 5. Not Found Domains (not_found_domains)
Domains that users searched but weren't in database.

```sql
DESCRIBE not_found_domains
```

## DuckDB Local (warehouse.duckdb)

### Paid Users Identification
Join MongoDB synced tables to find paid users:

```sql
-- Users with payments
SELECT DISTINCT email FROM mongo_payments WHERE status = 'completed'
UNION
SELECT DISTINCT email FROM mongo_orders WHERE status IN ('completed', 'paid')
UNION
SELECT u.email FROM mongo_subscriptions s
JOIN mongo_users u ON s.userId = u._id
WHERE s.status = 'active'
```

### MongoDB Synced Tables
- `mongo_users` - User accounts
- `mongo_payments` - Payment records
- `mongo_orders` - Order history
- `mongo_subscriptions` - Active subscriptions

## Adoption Score Formula

```
ADOPTION SCORE = (User % × 0.6) + (Request % × 0.4)
```

- **User %**: What percentage of users used this feature
- **Request %**: What percentage of total requests used this feature
- Weights breadth (60%) over depth (40%)

### Priority Thresholds
| Score | Priority |
|-------|----------|
| ≥20 | MUST HAVE |
| 10-20 | KEEP |
| 3-10 | SECONDARY |
| 1-3 | HIDE |
| <1 | REMOVE |

## DuckDB Synced Tables (ch_*)

Synced from ClickHouse via `python3 db_api/clickhouse_to_duckdb.py`:

| Table | DuckDB | Notes |
|-------|--------|-------|
| ch_user_activity_logs | ✅ | Filter usage, API calls |
| ch_resources_modal_opens | ✅ | Sensitive Scope tracking |
| ch_not_found_domains | ✅ | Domains users searched but not found |
| domain_history | ❌ Skip | 166M rows - query in ClickHouse |
| price_history | ❌ Skip | 34M rows - query in ClickHouse |

```bash
# Sync small tables (run periodically)
python3 db_api/clickhouse_to_duckdb.py user_activity_logs
python3 db_api/clickhouse_to_duckdb.py resources_modal_opens
python3 db_api/clickhouse_to_duckdb.py not_found_domains

# Check sync status
python3 db_api/clickhouse_to_duckdb.py status
```

## Quick Commands

```bash
# List ClickHouse tables
python3 db_api/clickhouse_client.py "SHOW TABLES"

# Describe table
python3 db_api/clickhouse_client.py "DESCRIBE table_name"

# Run query
python3 db_api/clickhouse_client.py "SELECT ..."

# DuckDB (use read_only if DBeaver is open)
python3 -c "import duckdb; print(duckdb.connect('warehouse.duckdb', read_only=True).execute('SELECT ...').fetchall())"
```
