# Code Samples for Product Research

All database queries and code examples for analyzing FatGrid usage data.

**Last verified**: 2026-01-10

---

## Setup

```python
from db_api.duckdb_warehouse import Warehouse
wh = Warehouse()
```

---

## Verified Core Queries (2026-01-10)

These queries were verified against live DuckDB data.

### User Segments (90 days)

```python
wh.query("""
    SELECT
        subscription_type,
        COUNT(DISTINCT email) as unique_users,
        COUNT(*) as total_requests
    FROM ch_user_activity_logs
    WHERE date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY subscription_type
    ORDER BY unique_users DESC
""")
# Result: Free 833 (149,107 req), Standard 52 (494,032 req), Business 11 (7,757 req)
```

### Google Search Scanner: Page Views vs Actual Searches

**IMPORTANT**: `/config/*` and `/list` = page views, `/search` = actual search (consumes units)

```python
wh.query("""
    SELECT
        subscription_type,
        CASE
            WHEN url LIKE '%/google-search/config%' THEN 'Load page config'
            WHEN url LIKE '%/google-search/list%' THEN 'View results list'
            WHEN url = '/api/google-search/search' THEN 'Actual search (consumes units)'
            ELSE 'View specific result'
        END as action_type,
        COUNT(DISTINCT email) as unique_users,
        COUNT(*) as total_requests
    FROM ch_user_activity_logs
    WHERE url LIKE '%google-search%'
      AND date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY 1, 2
    ORDER BY subscription_type, action_type
""")
# Result:
# | free     | Actual search (consumes units) | 86  | 296   |
# | free     | Load page config               | 206 | 1,262 |
# | free     | View results list              | 205 | 1,512 |
# | free     | View specific result           | 85  | 5,315 |
# | standard | Actual search (consumes units) | 11  | 157   |
# | standard | Load page config               | 22  | 458   |
# | standard | View results list              | 22  | 576   |
# | standard | View specific result           | 11  | 4,645 |
```

### Domain Unlocks: Page Views vs Actual Unlocks

**IMPORTANT**: `/my-unlocks` = viewing unlock history (page view), `/unlock` = actual unlock action

```python
wh.query("""
    SELECT
        subscription_type,
        CASE
            WHEN url LIKE '%/my-unlocks%' THEN 'View unlock history'
            WHEN url LIKE '%/unlock' THEN 'Actual unlock'
        END as action_type,
        COUNT(DISTINCT email) as unique_users,
        COUNT(*) as total_requests
    FROM ch_user_activity_logs
    WHERE url LIKE '%unlock%'
      AND date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY 1, 2
    ORDER BY subscription_type, action_type
""")
# Result:
# | free     | Actual unlock       | 286 | 1,063 |
# | free     | View unlock history | 751 | 6,355 |
# | standard | Actual unlock       | 1   | 3     |
# | standard | View unlock history | 15  | 96    |
```

### Exports (CSV + Google Sheets)

```python
wh.query("""
    SELECT
        subscription_type,
        CASE
            WHEN url LIKE '%google-sheet%' THEN 'Google Sheets'
            ELSE 'CSV'
        END as export_type,
        COUNT(DISTINCT email) as unique_users,
        COUNT(*) as total_exports
    FROM ch_user_activity_logs
    WHERE (url LIKE '%download-csv%' OR url LIKE '%google-sheet%')
      AND date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY 1, 2
    ORDER BY subscription_type, export_type
""")
# Result:
# | free     | CSV           | 82  | 952 |
# | free     | Google Sheets | 25  | 109 |
# | standard | CSV           | 31  | 408 |
# | standard | Google Sheets | 12  | 183 |
# | business | CSV           | 3   | 178 |
# | business | Google Sheets | 1   | 4   |
```

### Backlinks Scanner: Page Views vs Actual Scans

**IMPORTANT**: `/list` = viewing results, `/check*` = triggering actual scan (consumes units)

```python
wh.query("""
    SELECT
        subscription_type,
        CASE
            WHEN url LIKE '%/referring-domains/list%' THEN 'View results list'
            WHEN url LIKE '%/referring-domains/check%' THEN 'Trigger scan (check/check-info)'
            WHEN url LIKE '%/check-referring-domains%' THEN 'Trigger scan (domains endpoint)'
            WHEN url LIKE '%/referring-domains/%' AND url NOT LIKE '%list%' AND url NOT LIKE '%check%' THEN 'View specific result'
        END as action_type,
        COUNT(DISTINCT email) as unique_users,
        COUNT(*) as total_requests
    FROM ch_user_activity_logs
    WHERE (url LIKE '%referring-domains%' OR url LIKE '%check-referring-domains%')
      AND date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY 1, 2
    ORDER BY subscription_type, action_type
""")
# Result:
# | free     | Trigger scan (check/check-info) | 78  | 160 |
# | free     | Trigger scan (domains endpoint) | 28  | 75  |
# | free     | View results list               | 165 | 414 |
# | free     | View specific result            | 39  | 60  |
# | standard | Trigger scan (check/check-info) | 4   | 6   |
# | standard | Trigger scan (domains endpoint) | 7   | 15  |
# | standard | View results list               | 13  | 41  |
```

### Top URLs in Activity Logs

```python
wh.query("""
    SELECT url, COUNT(*) as hits
    FROM ch_user_activity_logs
    GROUP BY url
    ORDER BY hits DESC
    LIMIT 30
""")
```

---

## Publisher Price Finder: Counting Domains per Request

The `request_body` column stores JSON like:
```json
{"search":"[{\"name\":\"forbes.com\",\"price\":\"-\"},{\"name\":\"cnn.com\",\"price\":\"-\"}]"}
```

**To count domains per request**, count occurrences of `name` in the string:

```python
# Count domains in each request (DuckDB string manipulation)
wh.query("""
    SELECT
        email,
        date,
        -- Each domain has one "name" field, divide by 4 (length of 'name')
        (length(request_body) - length(replace(request_body, 'name', ''))) / 4 as domain_count
    FROM ch_user_activity_logs
    WHERE url LIKE '%/api/domains/search%'
      AND subscription_type = 'free'
      AND request_body IS NOT NULL
""")
```

**Why this works**:
- `replace(request_body, 'name', '')` removes all occurrences of "name"
- The length difference equals `4 * number_of_domains`
- Divide by 4 to get domain count

**Common pitfalls**:
- Don't use `"name"` with quotes - DuckDB escaping makes this unreliable
- Don't try JSON parsing - the nested escaped JSON is complex
- Simple string counting is more reliable for this data format

### Users Affected by Limits

```python
wh.query("""
WITH request_domains AS (
    SELECT
        email,
        date,
        (length(request_body) - length(replace(request_body, 'name', ''))) / 4 as domain_count
    FROM ch_user_activity_logs
    WHERE url LIKE '%/api/domains/search%'
      AND subscription_type = 'free'
      AND request_body IS NOT NULL
      AND date >= CURRENT_DATE - INTERVAL '90 days'
),
daily_usage AS (
    SELECT
        email,
        date,
        SUM(domain_count) as domains_per_day,
        MAX(domain_count) as max_batch_size
    FROM request_domains
    GROUP BY email, date
)
-- Users exceeding 50 per check
SELECT COUNT(DISTINCT email) FROM request_domains WHERE domain_count > 50;

-- Users exceeding 200 per day
SELECT COUNT(DISTINCT email) FROM daily_usage WHERE domains_per_day > 200;
""")
```

---

## Export Source Disambiguation

**`/api/domains/download-csv` is shared** by multiple features. You MUST check what preceded the export.

```python
# Identify export source by preceding request
wh.query("""
WITH activity_ordered AS (
    SELECT
        email, date, timestamp, url,
        LAG(url) OVER (PARTITION BY email, date ORDER BY timestamp) as prev_url
    FROM ch_user_activity_logs
    WHERE subscription_type = 'free'
)
SELECT
    CASE
        WHEN prev_url LIKE '%/api/domains/search%' THEN 'Publisher Price Finder'
        WHEN prev_url LIKE '%/api/domains/list%' THEN 'Marketplaces'
        ELSE 'Other'
    END as export_source,
    COUNT(*) as exports
FROM activity_ordered
WHERE url LIKE '%/domains/download-csv%' OR url LIKE '%/domains/google-sheet%'
GROUP BY 1
""")
```

| Export Source | How to Identify | Free User Access |
|---------------|-----------------|------------------|
| **Publisher Price Finder** | Preceded by `/api/domains/search` | ✅ Allowed |
| **Marketplaces** | Preceded by `/api/domains/list` | ❌ Blocked (potential loophole) |

---

## Unlock Analysis

### Users Hitting Daily Cap

```python
wh.query("""
    SELECT date, email, COUNT(*) as unlocks
    FROM ch_user_activity_logs
    WHERE subscription_type = 'free' AND url LIKE '%/user-unlocks/unlock%'
    GROUP BY date, email
    HAVING unlocks >= 3
""")
```

---

## User & Subscription Status

### User Balance and Subscription

```python
wh.query("""
    SELECT u.email, u.balance, s.type, s.stripe_status, s.canceled_at
    FROM mongo_users u
    LEFT JOIN mongo_subscriptions s ON u.id = s.user_id
    WHERE u.balance < 100
""")
```

### Feature Usage with Subscription Context

```python
wh.query("""
    SELECT a.email, a.subscription_type, s.stripe_status,
           COUNT(*) as requests, COUNT(DISTINCT a.date) as active_days
    FROM ch_user_activity_logs a
    LEFT JOIN mongo_users u ON a.email = u.email
    LEFT JOIN mongo_subscriptions s ON u.id = s.user_id
    WHERE a.url LIKE '%/api/google-search%'
    GROUP BY a.email, a.subscription_type, s.stripe_status
""")
```

---

## Feature Usage by Subscription Type

```python
# Generic pattern for any feature
wh.query("""
    SELECT
        subscription_type,
        COUNT(DISTINCT email) as unique_users,
        COUNT(*) as total_requests
    FROM ch_user_activity_logs
    WHERE url LIKE '%/api/FEATURE_ENDPOINT%'
      AND date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY subscription_type
""")
```

---

## Export Analysis

### By Source and Format

```python
wh.query("""
SELECT
    subscription_type,
    CASE
        WHEN url LIKE '%/domains/%' THEN 'Marketplaces'
        WHEN url LIKE '%/google-search/%' THEN 'Google Search Scanner'
        WHEN url LIKE '%/project-prospects/%' THEN 'Projects'
        ELSE 'Other'
    END as source_feature,
    CASE
        WHEN url LIKE '%google-sheet%' THEN 'Google Sheet'
        ELSE 'CSV'
    END as format,
    COUNT(DISTINCT email) as unique_users,
    COUNT(*) as total_exports
FROM ch_user_activity_logs
WHERE (url LIKE '%download%' OR url LIKE '%export%' OR url LIKE '%google-sheet%')
  AND url NOT LIKE '%import%'
  AND date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY 1, 2, 3
ORDER BY subscription_type, unique_users DESC
""")
```

---

## Table Schemas

### ch_user_activity_logs
```sql
DESCRIBE ch_user_activity_logs;
-- id, user_id, email, subscription_type, method, url, user_agent,
-- ip_address, request_body, query_params, response_status,
-- response_time_ms, timestamp, date
```

### mongo_users
```sql
DESCRIBE mongo_users;
-- id, email, role, status, company_id, customer_id, is_publisher,
-- balance, created_at, updated_at, synced_at
```

### mongo_subscriptions
```sql
DESCRIBE mongo_subscriptions;
-- id, subscription_id, user_id, company_id, type, amount, currency,
-- interval, stripe_status, price_id, start_date, current_period_start,
-- current_period_end, cancel_at_period_end, canceled_at, ended_at,
-- created_at, updated_at, synced_at
```

### mongo_internal_payments
```sql
DESCRIBE mongo_internal_payments;
-- id, user_id, company_id, amount, action_type, status,
-- created_at, updated_at, synced_at
```

### mongo_projects
```sql
DESCRIBE mongo_projects;
-- id, user_id, company_id, name, domain, created_at, updated_at, synced_at
```

### mongo_project_prospects
```sql
DESCRIBE mongo_project_prospects;
-- id, project_id, user_id, company_id, domain, status, live_link,
-- order_price, placed_via, created_at, updated_at, synced_at
```

### mongo_project_completed_orders
```sql
DESCRIBE mongo_project_completed_orders;
-- id, project_id, user_id, domain, live_link, placed_via,
-- created_at, updated_at, synced_at
```

---

## Projects Analysis

### Projects Overview
```python
wh.query("""
    SELECT
        COUNT(DISTINCT p.id) as total_projects,
        COUNT(DISTINCT p.user_id) as unique_users,
        COUNT(DISTINCT pp.id) as total_prospects,
        COUNT(DISTINCT pco.id) as completed_orders
    FROM mongo_projects p
    LEFT JOIN mongo_project_prospects pp ON p.id = pp.project_id
    LEFT JOIN mongo_project_completed_orders pco ON p.id = pco.project_id
""")
```

### Prospect Status Funnel
```python
wh.query("""
    SELECT
        status,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM mongo_project_prospects), 1) as pct
    FROM mongo_project_prospects
    GROUP BY status
    ORDER BY count DESC
""")
# Result: backlog 86.4%, done 7.1%, outreach 4.3%, ok_to_proceed 1.5%, etc.
```

### Users Active in Projects (last 7 days)
```python
wh.query("""
    SELECT
        a.email,
        s.type as subscription,
        COUNT(*) as project_actions,
        COUNT(DISTINCT a.date) as active_days
    FROM ch_user_activity_logs a
    LEFT JOIN mongo_users u ON a.email = u.email
    LEFT JOIN mongo_subscriptions s ON u.id = s.user_id AND s.stripe_status = 'active'
    WHERE a.url LIKE '%project%'
      AND a.url NOT LIKE '/api/projects?%'  -- Exclude just listing projects
      AND a.url != '/api/projects'
      AND a.date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY a.email, s.type
    ORDER BY project_actions DESC
    LIMIT 10
""")
```

### Projects with Prospect Counts
```python
wh.query("""
    SELECT
        p.name,
        p.domain,
        COUNT(pp.id) as prospects,
        COUNT(CASE WHEN pp.status = 'done' THEN 1 END) as done
    FROM mongo_projects p
    LEFT JOIN mongo_project_prospects pp ON p.id = pp.project_id
    GROUP BY p.id, p.name, p.domain
    ORDER BY prospects DESC
    LIMIT 10
""")
```

### Top Users by Project Activity
```python
wh.query("""
    SELECT
        u.email,
        s.type as subscription,
        COUNT(DISTINCT p.id) as projects,
        COUNT(pp.id) as prospects,
        COUNT(CASE WHEN pp.status = 'done' THEN 1 END) as done,
        COUNT(DISTINCT pco.id) as completed_orders
    FROM mongo_users u
    JOIN mongo_projects p ON u.id = p.user_id
    LEFT JOIN mongo_project_prospects pp ON p.id = pp.project_id
    LEFT JOIN mongo_project_completed_orders pco ON p.id = pco.project_id
    LEFT JOIN mongo_subscriptions s ON u.id = s.user_id AND s.stripe_status = 'active'
    GROUP BY u.email, s.type
    ORDER BY prospects DESC
    LIMIT 10
""")
```

### Empty Projects (created but no prospects added)
```python
wh.query("""
    SELECT
        u.email,
        p.name,
        p.created_at::date as created
    FROM mongo_users u
    JOIN mongo_projects p ON u.id = p.user_id
    LEFT JOIN mongo_project_prospects pp ON p.id = pp.project_id
    WHERE pp.id IS NULL
    ORDER BY p.created_at DESC
""")
```

### Project Activity Endpoints (from activity logs)
```python
wh.query("""
    SELECT
        CASE
            WHEN url LIKE '%/project-prospects%' THEN 'Manage prospects'
            WHEN url LIKE '%/projects/%/status%' THEN 'Update status config'
            WHEN url LIKE '%/projects/%/participants%' THEN 'Manage participants'
            WHEN url LIKE '%/project-competitor%' THEN 'Competitor analysis'
            WHEN url = '/api/projects' OR url LIKE '/api/projects?%' THEN 'List projects'
            WHEN url LIKE '/api/projects/%' THEN 'View/edit project'
            ELSE 'Other'
        END as action_type,
        COUNT(*) as count,
        COUNT(DISTINCT email) as users
    FROM ch_user_activity_logs
    WHERE url LIKE '%project%'
      AND date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY 1
    ORDER BY count DESC
""")
```

---

## Internal Billing Units Analysis

Internal billing units are tracked in `mongo_internal_payments`. Each transaction has a status: RESERVED (pending), PAID (deducted), or REFUND.

**Core vs Premium Features**:
- **Core features** (e.g., PPF): DB reads only, no units consumed
- **Premium features**: Require external resources, consume units:
  - `google_search_scan` - Google Search Scanner (crawling Google)
  - `backlinks_profile_scanner` - Backlinks Profile Scanner (Semrush API)
  - `fetching_semrush_info` - Semrush data fetching

To see how users spend units, join with `mongo_users` and filter by `status = 'PAID'`. The `amount` field shows units spent, and `action_type` shows what premium feature consumed them.

To calculate a user's starting balance: `current_balance + total_spent = implied_starting_balance`. Free users started with 120 units (old) or 600 units (new) - one-time allocation, no refill. Standard gets 5000/month, Business gets 50000/month (refilled monthly).

---

## Orders Analysis

Orders are backlink purchases tracked in **two systems**: MongoDB (payment) and ClickUp (fulfillment).

### Table Schemas

#### mongo_orders
```sql
DESCRIBE mongo_orders;
-- id, order_id, user_id, company_id, domain, price, status, payment_status,
-- buyer_email, seller_email, stripe_payment_id, doc_url, created_at, updated_at, synced_at
```

#### clickup_orders
```sql
DESCRIBE clickup_orders;
-- task_id, name, order_number, order_type, domain, amount_usd, customer_email,
-- status, status_type, date_created, date_updated, date_done, creator_id,
-- creator_name, creator_email, assignee_names, assignee_emails, description,
-- url, attachment_count, synced_at
```

### Unified Order View (Join Both Sources)

```python
wh.query("""
    SELECT
        m.order_id,
        m.domain as publisher,
        m.buyer_email,
        m.price,
        m.status as mongo_status,
        m.payment_status,
        c.status as clickup_status,
        c.date_done as completed_at
    FROM mongo_orders m
    JOIN clickup_orders c ON m.order_id = c.order_number
    ORDER BY m.order_id DESC
""")
```

### Coverage Check (MongoDB vs ClickUp)

```python
wh.query("""
    SELECT
        'MongoDB only' as source,
        COUNT(*) as orders
    FROM mongo_orders m
    LEFT JOIN clickup_orders c ON m.order_id = c.order_number
    WHERE c.order_number IS NULL

    UNION ALL

    SELECT
        'ClickUp only' as source,
        COUNT(*) as orders
    FROM clickup_orders c
    LEFT JOIN mongo_orders m ON c.order_number = m.order_id
    WHERE m.order_id IS NULL

    UNION ALL

    SELECT
        'Both sources' as source,
        COUNT(*) as orders
    FROM mongo_orders m
    JOIN clickup_orders c ON m.order_id = c.order_number
""")
-- Result (2026-01-11): MongoDB only: 138, ClickUp only: 5, Both: 84
```

### MongoDB-Only Orders Analysis

```python
# Why are 138 orders only in MongoDB?
wh.query("""
    SELECT
        m.status,
        m.payment_status,
        COUNT(*) as count
    FROM mongo_orders m
    LEFT JOIN clickup_orders c ON m.order_id = c.order_number
    WHERE c.order_number IS NULL
    GROUP BY m.status, m.payment_status
    ORDER BY count DESC
""")
-- Result: created/created: 131 (abandoned carts), order_submitted/failed: 4, order_submitted/succeeded: 3
```

### Orders by Buyer

```python
wh.query("""
    SELECT
        buyer_email,
        COUNT(*) as total_orders,
        COUNT(CASE WHEN status != 'created' THEN 1 END) as submitted_orders,
        COUNT(CASE WHEN payment_status = 'paid' OR payment_status = 'published' THEN 1 END) as paid_orders,
        SUM(CASE WHEN payment_status IN ('paid', 'published') THEN price ELSE 0 END) as total_revenue
    FROM mongo_orders
    GROUP BY buyer_email
    ORDER BY total_revenue DESC
""")
```

### Order Fulfillment Funnel

```python
wh.query("""
    SELECT
        status,
        COUNT(*) as orders,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM clickup_orders), 1) as pct
    FROM clickup_orders
    GROUP BY status
    ORDER BY
        CASE status
            WHEN 'new orders' THEN 1
            WHEN 'outreach' THEN 2
            WHEN 'review + capture' THEN 3
            WHEN 'sent to seller/marketplace' THEN 4
            WHEN 'edits' THEN 5
            WHEN 'stuck/delay' THEN 6
            WHEN 'completed' THEN 7
            WHEN 'cancelled' THEN 8
        END
""")
```

### Specific Order Lookup

```python
# Get all data for a specific order
order_id = 122
wh.query(f"""
    SELECT
        m.*,
        c.status as clickup_status,
        c.date_done,
        c.assignee_names
    FROM mongo_orders m
    LEFT JOIN clickup_orders c ON m.order_id = c.order_number
    WHERE m.order_id = {order_id}
""")
```

### Orders for Specific User

```python
email = 'daria@xamsor.com'
wh.query(f"""
    SELECT
        m.order_id,
        m.domain,
        m.price,
        m.payment_status,
        c.status as fulfillment,
        m.created_at::DATE as order_date
    FROM mongo_orders m
    LEFT JOIN clickup_orders c ON m.order_id = c.order_number
    WHERE m.buyer_email = '{email}'
    ORDER BY m.order_id DESC
""")
```

---

## Marketplaces Filter Usage Analysis

Filter usage is tracked in `ch_user_activity_logs` via the `query_params` JSON field for `/api/domains/list` requests.

**Last verified**: 2026-01-12

### IMPORTANT: Correct Method for Filter Analysis

**ALWAYS use JSON extraction from `query_params` column, NOT URL string parsing.**

- ✅ CORRECT: `json_extract_string(params, '$.categories')`
- ❌ WRONG: `url LIKE '%categories=%'` (overcounts due to partial matches)

### How Filters Are Stored

The `query_params` column contains JSON like:
```json
{"page":"1","limit":"100","sort":"-totalTraffic","type":"guest_post","minDr":"30","categories":"Finance","languages":"en"}
```

### Full Filter Usage by Free vs Paid Users (90 days)

**This is the canonical query for filter usage analysis:**

```python
from db_api.duckdb_warehouse import Warehouse
wh = Warehouse()

query = '''
WITH filter_requests AS (
    SELECT
        query_params::JSON as params,
        email,
        CASE WHEN subscription_type = 'free' THEN 'free' ELSE 'paid' END as user_type
    FROM ch_user_activity_logs
    WHERE url LIKE '/api/domains/list?%'
      AND query_params IS NOT NULL
      AND length(query_params) > 10
      AND date >= CURRENT_DATE - INTERVAL '90 days'
)
SELECT
    user_type,
    COUNT(*) as total_req,
    COUNT(DISTINCT email) as total_users,

    -- Category (non-empty check required)
    COUNT(CASE WHEN json_extract_string(params, '$.categories') IS NOT NULL
               AND json_extract_string(params, '$.categories') != '' THEN 1 END) as cat_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.categories') IS NOT NULL
                        AND json_extract_string(params, '$.categories') != '' THEN email END) as cat_users,

    -- DR (minDr or maxDr)
    COUNT(CASE WHEN json_extract_string(params, '$.minDr') IS NOT NULL
               OR json_extract_string(params, '$.maxDr') IS NOT NULL THEN 1 END) as dr_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.minDr') IS NOT NULL
                        OR json_extract_string(params, '$.maxDr') IS NOT NULL THEN email END) as dr_users,

    -- Languages
    COUNT(CASE WHEN json_extract_string(params, '$.languages') IS NOT NULL THEN 1 END) as lang_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.languages') IS NOT NULL THEN email END) as lang_users,

    -- Top Country (databases param)
    COUNT(CASE WHEN json_extract_string(params, '$.databases') IS NOT NULL THEN 1 END) as country_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.databases') IS NOT NULL THEN email END) as country_users,

    -- Organic Traffic Total
    COUNT(CASE WHEN json_extract_string(params, '$.minTotalOrganicTraffic') IS NOT NULL
               OR json_extract_string(params, '$.maxTotalOrganicTraffic') IS NOT NULL THEN 1 END) as orgtraffic_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.minTotalOrganicTraffic') IS NOT NULL
                        OR json_extract_string(params, '$.maxTotalOrganicTraffic') IS NOT NULL THEN email END) as orgtraffic_users,

    -- Price
    COUNT(CASE WHEN json_extract_string(params, '$.minPrice') IS NOT NULL
               OR json_extract_string(params, '$.maxPrice') IS NOT NULL THEN 1 END) as price_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.minPrice') IS NOT NULL
                        OR json_extract_string(params, '$.maxPrice') IS NOT NULL THEN email END) as price_users,

    -- Link Follow
    COUNT(CASE WHEN json_extract_string(params, '$.linkFollow') IS NOT NULL THEN 1 END) as linkfollow_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.linkFollow') IS NOT NULL THEN email END) as linkfollow_users,

    -- Keyword
    COUNT(CASE WHEN json_extract_string(params, '$.keyword') IS NOT NULL THEN 1 END) as keyword_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.keyword') IS NOT NULL THEN email END) as keyword_users,

    -- Min Monthly Organic Traffic
    COUNT(CASE WHEN json_extract_string(params, '$.minMonthlyOrganicTraffic') IS NOT NULL
               OR json_extract_string(params, '$.maxMonthlyOrganicTraffic') IS NOT NULL THEN 1 END) as monthlyorg_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.minMonthlyOrganicTraffic') IS NOT NULL
                        OR json_extract_string(params, '$.maxMonthlyOrganicTraffic') IS NOT NULL THEN email END) as monthlyorg_users,

    -- AS
    COUNT(CASE WHEN json_extract_string(params, '$.minAs') IS NOT NULL
               OR json_extract_string(params, '$.maxAs') IS NOT NULL THEN 1 END) as as_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.minAs') IS NOT NULL
                        OR json_extract_string(params, '$.maxAs') IS NOT NULL THEN email END) as as_users,

    -- Sponsored
    COUNT(CASE WHEN json_extract_string(params, '$.sponsored') IS NOT NULL THEN 1 END) as sponsored_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.sponsored') IS NOT NULL THEN email END) as sponsored_users,

    -- Restricted Niches
    COUNT(CASE WHEN json_extract_string(params, '$.niches') IS NOT NULL THEN 1 END) as niches_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.niches') IS NOT NULL THEN email END) as niches_users,

    -- Organic Traffic Top Country
    COUNT(CASE WHEN json_extract_string(params, '$.minOrganicTraffic') IS NOT NULL
               OR json_extract_string(params, '$.maxOrganicTraffic') IS NOT NULL THEN 1 END) as orgtopcountry_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.minOrganicTraffic') IS NOT NULL
                        OR json_extract_string(params, '$.maxOrganicTraffic') IS NOT NULL THEN email END) as orgtopcountry_users,

    -- All Channels Traffic Total
    COUNT(CASE WHEN json_extract_string(params, '$.minTotalTraffic') IS NOT NULL
               OR json_extract_string(params, '$.maxTotalTraffic') IS NOT NULL THEN 1 END) as totaltraffic_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.minTotalTraffic') IS NOT NULL
                        OR json_extract_string(params, '$.maxTotalTraffic') IS NOT NULL THEN email END) as totaltraffic_users,

    -- Sellers
    COUNT(CASE WHEN json_extract_string(params, '$.resources') IS NOT NULL THEN 1 END) as sellers_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.resources') IS NOT NULL THEN email END) as sellers_users,

    -- Favorites
    COUNT(CASE WHEN json_extract_string(params, '$.favorites') IS NOT NULL THEN 1 END) as fav_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.favorites') IS NOT NULL THEN email END) as fav_users,

    -- Creation Date
    COUNT(CASE WHEN json_extract_string(params, '$.createdAtFrom') IS NOT NULL
               OR json_extract_string(params, '$.createdAtTo') IS NOT NULL THEN 1 END) as createdat_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.createdAtFrom') IS NOT NULL
                        OR json_extract_string(params, '$.createdAtTo') IS NOT NULL THEN email END) as createdat_users,

    -- Ref Domains
    COUNT(CASE WHEN json_extract_string(params, '$.minRefDomains') IS NOT NULL
               OR json_extract_string(params, '$.maxRefDomains') IS NOT NULL THEN 1 END) as refdom_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.minRefDomains') IS NOT NULL
                        OR json_extract_string(params, '$.maxRefDomains') IS NOT NULL THEN email END) as refdom_users,

    -- Tags
    COUNT(CASE WHEN json_extract_string(params, '$.tags') IS NOT NULL THEN 1 END) as tags_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.tags') IS NOT NULL THEN email END) as tags_users,

    -- All Channels Traffic Top Country
    COUNT(CASE WHEN json_extract_string(params, '$.minAllChannelsTrafficTopCountry') IS NOT NULL
               OR json_extract_string(params, '$.maxAllChannelsTrafficTopCountry') IS NOT NULL THEN 1 END) as allchannelstop_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.minAllChannelsTrafficTopCountry') IS NOT NULL
                        OR json_extract_string(params, '$.maxAllChannelsTrafficTopCountry') IS NOT NULL THEN email END) as allchannelstop_users,

    -- Notes
    COUNT(CASE WHEN json_extract_string(params, '$.notes') IS NOT NULL THEN 1 END) as notes_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.notes') IS NOT NULL THEN email END) as notes_users,

    -- Blacklist
    COUNT(CASE WHEN json_extract_string(params, '$.blacklist') IS NOT NULL THEN 1 END) as blacklist_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.blacklist') IS NOT NULL THEN email END) as blacklist_users,

    -- Verified
    COUNT(CASE WHEN json_extract_string(params, '$.verified') IS NOT NULL THEN 1 END) as verified_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.verified') IS NOT NULL THEN email END) as verified_users,

    -- Country Traffic Present
    COUNT(CASE WHEN json_extract_string(params, '$.countryTrafficPresent') IS NOT NULL THEN 1 END) as countrypresent_req,
    COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.countryTrafficPresent') IS NOT NULL THEN email END) as countrypresent_users

FROM filter_requests
GROUP BY user_type
'''

result = wh.query(query).fetchdf()
print(result.T)
```

### Results (as of 2026-01-12)

| Filter | Free Req | Free Users | Free % | Paid Req | Paid Users | Paid % | Diff | Req total | Users total |
|--------|----------|------------|--------|----------|------------|--------|------|-----------|-------------|
| Category | 4,455 | 196 | 39% | 14,055 | 39 | 71% | +32% | 18,510 | 235 |
| DR | 4,340 | 141 | 28% | 5,568 | 35 | 64% | +36% | 9,908 | 176 |
| Languages | 3,695 | 198 | 39% | 5,035 | 42 | 76% | +37% | 8,730 | 240 |
| Top Country by Organic Traffic | 1,324 | 74 | 15% | 3,890 | 36 | 65% | +50% | 5,214 | 110 |
| Organic Traffic (Total) | 3,547 | 137 | 27% | 3,009 | 42 | 76% | +49% | 6,556 | 179 |
| Best Price | 4,642 | 124 | 24% | 2,054 | 35 | 64% | +40% | 6,696 | 159 |
| Link Follow | 640 | 51 | 10% | 1,227 | 24 | 44% | +34% | 1,867 | 75 |
| Keyword Match | 1,464 | 62 | 12% | 832 | 29 | 53% | +41% | 2,296 | 91 |
| Min Monthly Organic Traffic | 1,299 | 63 | 12% | 712 | 15 | 27% | +15% | 2,011 | 78 |
| AS | 3,212 | 67 | 13% | 669 | 12 | 22% | +9% | 3,881 | 79 |
| Sponsored | 264 | 24 | 5% | 661 | 14 | 25% | +20% | 925 | 38 |
| Restricted Niches | 906 | 58 | 11% | 580 | 22 | 40% | +29% | 1,486 | 80 |
| Organic Traffic (Top Country) | 266 | 16 | 3% | 333 | 15 | 27% | +24% | 599 | 31 |
| All Channels Traffic (Total) | 349 | 14 | 3% | 306 | 7 | 13% | +10% | 655 | 21 |
| Sellers | 126 | 14 | 3% | 288 | 11 | 20% | +17% | 414 | 25 |
| Favorites | 16 | 3 | 1% | 68 | 1 | 2% | +1% | 84 | 4 |
| Creation Date | 81 | 2 | 0% | 13 | 2 | 4% | +4% | 94 | 4 |
| Ref Domains | 72 | 2 | 0% | 0 | 0 | 0% | +0% | 72 | 2 |
| Tags | 12 | 1 | 0% | 0 | 0 | 0% | +0% | 12 | 1 |
| All Channels Traffic (Top Country) | 0 | 0 | 0% | 0 | 0 | 0% | +0% | 0 | 0 |
| Notes | 0 | 0 | 0% | 0 | 0 | 0% | +0% | 0 | 0 |
| Blacklist | 0 | 0 | 0% | 0 | 0 | 0% | +0% | 0 | 0 |
| Verified | 0 | 0 | 0% | 0 | 0 | 0% | +0% | 0 | 0 |
| Country Traffic Present | 0 | 0 | 0% | 0 | 0 | 0% | +0% | 0 | 0 |

**Totals**: Free 13,630 requests / 507 users, Paid 21,302 requests / 55 users

### Individual Filter Usage (legacy query)

```python
wh.query("""
    WITH filter_requests AS (
        SELECT
            query_params::JSON as params,
            email
        FROM ch_user_activity_logs
        WHERE url LIKE '/api/domains/list?%'
          AND query_params IS NOT NULL
          AND length(query_params) > 10
          AND date >= CURRENT_DATE - INTERVAL '90 days'
    ),
    totals AS (
        SELECT COUNT(*) as total_requests, COUNT(DISTINCT email) as total_users FROM filter_requests
    )
    SELECT
        'minDr' as filter_name,
        COUNT(CASE WHEN json_extract_string(params, '$.minDr') IS NOT NULL THEN 1 END) as requests,
        COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.minDr') IS NOT NULL THEN email END) as users,
        ROUND(COUNT(CASE WHEN json_extract_string(params, '$.minDr') IS NOT NULL THEN 1 END) * 100.0 / (SELECT total_requests FROM totals), 1) as pct_requests,
        ROUND(COUNT(DISTINCT CASE WHEN json_extract_string(params, '$.minDr') IS NOT NULL THEN email END) * 100.0 / (SELECT total_users FROM totals), 1) as pct_users
    FROM filter_requests
""")
```

### All Filters Usage Query

```python
wh.query("""
    WITH filter_requests AS (
        SELECT
            query_params::JSON as params,
            email
        FROM ch_user_activity_logs
        WHERE url LIKE '%/api/domains/list%'
          AND query_params IS NOT NULL
          AND length(query_params) > 10
          AND date >= CURRENT_DATE - INTERVAL '90 days'
    )
    SELECT
        COUNT(CASE WHEN json_extract_string(params, '$.type') IS NOT NULL THEN 1 END) as type_filter,
        COUNT(CASE WHEN json_extract_string(params, '$.categories') IS NOT NULL AND json_extract_string(params, '$.categories') != '' THEN 1 END) as categories,
        COUNT(CASE WHEN json_extract_string(params, '$.languages') IS NOT NULL THEN 1 END) as languages,
        COUNT(CASE WHEN json_extract_string(params, '$.minDr') IS NOT NULL THEN 1 END) as minDr,
        COUNT(CASE WHEN json_extract_string(params, '$.maxDr') IS NOT NULL THEN 1 END) as maxDr,
        COUNT(CASE WHEN json_extract_string(params, '$.minAs') IS NOT NULL THEN 1 END) as minAs,
        COUNT(CASE WHEN json_extract_string(params, '$.maxAs') IS NOT NULL THEN 1 END) as maxAs,
        COUNT(CASE WHEN json_extract_string(params, '$.minPrice') IS NOT NULL THEN 1 END) as minPrice,
        COUNT(CASE WHEN json_extract_string(params, '$.maxPrice') IS NOT NULL THEN 1 END) as maxPrice,
        COUNT(CASE WHEN json_extract_string(params, '$.minTotalOrganicTraffic') IS NOT NULL THEN 1 END) as minTotalOrganicTraffic,
        COUNT(CASE WHEN json_extract_string(params, '$.maxTotalOrganicTraffic') IS NOT NULL THEN 1 END) as maxTotalOrganicTraffic,
        COUNT(CASE WHEN json_extract_string(params, '$.minTotalTraffic') IS NOT NULL THEN 1 END) as minTotalTraffic,
        COUNT(CASE WHEN json_extract_string(params, '$.maxTotalTraffic') IS NOT NULL THEN 1 END) as maxTotalTraffic,
        COUNT(CASE WHEN json_extract_string(params, '$.minMonthlyOrganicTraffic') IS NOT NULL THEN 1 END) as minMonthlyOrganicTraffic,
        COUNT(CASE WHEN json_extract_string(params, '$.maxMonthlyOrganicTraffic') IS NOT NULL THEN 1 END) as maxMonthlyOrganicTraffic,
        COUNT(CASE WHEN json_extract_string(params, '$.keyword') IS NOT NULL THEN 1 END) as keyword,
        COUNT(CASE WHEN json_extract_string(params, '$.niches') IS NOT NULL THEN 1 END) as niches,
        COUNT(CASE WHEN json_extract_string(params, '$.databases') IS NOT NULL THEN 1 END) as topCountry,
        COUNT(CASE WHEN json_extract_string(params, '$.resources') IS NOT NULL THEN 1 END) as sellers,
        COUNT(CASE WHEN json_extract_string(params, '$.linkFollow') IS NOT NULL THEN 1 END) as linkFollow,
        COUNT(CASE WHEN json_extract_string(params, '$.sponsored') IS NOT NULL THEN 1 END) as sponsored,
        COUNT(CASE WHEN json_extract_string(params, '$.minRefDomains') IS NOT NULL THEN 1 END) as minRefDomains,
        COUNT(CASE WHEN json_extract_string(params, '$.minOrganicTraffic') IS NOT NULL THEN 1 END) as minOrganicTrafficTopCountry,
        COUNT(CASE WHEN json_extract_string(params, '$.maxOrganicTraffic') IS NOT NULL THEN 1 END) as maxOrganicTrafficTopCountry,
        COUNT(CASE WHEN json_extract_string(params, '$.createdAtFrom') IS NOT NULL THEN 1 END) as creationDate,
        COUNT(CASE WHEN json_extract_string(params, '$.tags') IS NOT NULL THEN 1 END) as tags,
        COUNT(CASE WHEN json_extract_string(params, '$.notes') IS NOT NULL THEN 1 END) as notes,
        COUNT(CASE WHEN json_extract_string(params, '$.favorites') IS NOT NULL THEN 1 END) as favorites,
        COUNT(CASE WHEN json_extract_string(params, '$.blacklist') IS NOT NULL THEN 1 END) as blacklist,
        COUNT(CASE WHEN json_extract_string(params, '$.verified') IS NOT NULL THEN 1 END) as verified,
        COUNT(CASE WHEN json_extract_string(params, '$.countryTrafficPresent') IS NOT NULL THEN 1 END) as countryTrafficPresent
    FROM filter_requests
""")
```

### Filter Usage by Subscription Type

```python
wh.query("""
    WITH filter_requests AS (
        SELECT
            query_params::JSON as params,
            email,
            subscription_type
        FROM ch_user_activity_logs
        WHERE url LIKE '%/api/domains/list%'
          AND query_params IS NOT NULL
          AND length(query_params) > 10
          AND date >= CURRENT_DATE - INTERVAL '90 days'
    )
    SELECT
        subscription_type,
        COUNT(*) as total_requests,
        COUNT(DISTINCT email) as users,
        COUNT(CASE WHEN json_extract_string(params, '$.categories') IS NOT NULL AND json_extract_string(params, '$.categories') != '' THEN 1 END) as categories,
        COUNT(CASE WHEN json_extract_string(params, '$.languages') IS NOT NULL THEN 1 END) as languages,
        COUNT(CASE WHEN json_extract_string(params, '$.minDr') IS NOT NULL THEN 1 END) as minDr,
        COUNT(CASE WHEN json_extract_string(params, '$.maxPrice') IS NOT NULL THEN 1 END) as maxPrice,
        COUNT(CASE WHEN json_extract_string(params, '$.databases') IS NOT NULL THEN 1 END) as topCountry
    FROM filter_requests
    GROUP BY subscription_type
    ORDER BY total_requests DESC
""")
# Result: standard 19,756 req (48 users), free 13,630 req (507 users), business 1,546 req (10 users)
```

### Filter API Parameter Mapping

| UI Filter | API Parameter |
|-----------|---------------|
| Type tabs | `type` |
| Best Price | `minPrice`, `maxPrice` |
| AS | `minAs`, `maxAs` |
| DR | `minDr`, `maxDr` |
| Organic Traffic (Total) | `minTotalOrganicTraffic`, `maxTotalOrganicTraffic` |
| All Channels Traffic (Total) | `minTotalTraffic`, `maxTotalTraffic` |
| Min Monthly Organic Traffic | `minMonthlyOrganicTraffic`, `maxMonthlyOrganicTraffic` |
| Category | `categories` |
| Restricted Niches | `niches` |
| Keyword Match | `keyword` |
| Languages | `languages` |
| Sellers | `resources` |
| Link Follow | `linkFollow` |
| Sponsored | `sponsored` |
| Top Country by Organic Traffic | `databases` |
| Ref Domains | `minRefDomains`, `maxRefDomains` |
| Organic Traffic (Top Country) | `minOrganicTraffic`, `maxOrganicTraffic` |
| All Channels Traffic (Top Country) | `minAllChannelsTrafficTopCountry`, `maxAllChannelsTrafficTopCountry` |
| Creation Date | `createdAtFrom`, `createdAtTo` |
| Tags | `tags` |
| Notes | `notes` |
| Favorites | `favorites` |
| Blacklist | `blacklist` |
| Verified | `verified` |
| Country Traffic Present | `countryTrafficPresent` |

### Current Metrics (as of 2026-01-12)

| Filter | Requests | % Requests | Users | % Users |
|--------|----------|------------|-------|---------|
| type | 30,280 | 86.7% | 539 | 100.0% |
| categories | 18,510 | 53.0% | 227 | 42.1% |
| minDr | 9,702 | 27.8% | 170 | 31.5% |
| languages | 8,730 | 25.0% | 229 | 42.5% |
| minTotalOrganicTraffic | 6,443 | 18.4% | 165 | 30.6% |
| maxPrice | 6,206 | 17.8% | 146 | 27.1% |
| maxDr | 5,503 | 15.8% | 96 | 17.8% |
| databases (Top Country) | 5,214 | 14.9% | 105 | 19.5% |
| minPrice | 3,947 | 11.3% | 109 | 20.2% |
| minAs | 3,857 | 11.0% | 77 | 14.3% |
| maxTotalOrganicTraffic | 2,480 | 7.1% | 75 | 13.9% |
| keyword | 2,296 | 6.6% | 89 | 16.5% |
| maxAs | 2,204 | 6.3% | 55 | 10.2% |
| minMonthlyOrganicTraffic | 1,993 | 5.7% | 76 | 14.1% |
| linkFollow | 1,867 | 5.3% | 71 | 13.2% |
| niches | 1,486 | 4.3% | 75 | 13.9% |
| sponsored | 925 | 2.6% | 36 | 6.7% |
| maxMonthlyOrganicTraffic | 827 | 2.4% | 38 | 7.1% |
| minTotalTraffic | 638 | 1.8% | 20 | 3.7% |
| minOrganicTraffic | 596 | 1.7% | 30 | 5.6% |
| resources (Sellers) | 414 | 1.2% | 25 | 4.6% |
| maxTotalTraffic | 218 | 0.6% | 7 | 1.3% |
| createdAtFrom | 94 | 0.3% | 4 | 0.7% |
| maxOrganicTraffic | 94 | 0.3% | 4 | 0.7% |
| favorites | 84 | 0.2% | 4 | 0.7% |
| minRefDomains | 72 | 0.2% | 2 | 0.4% |
| tags | 12 | 0.0% | 1 | 0.2% |
| notes | 0 | 0.0% | 0 | 0.0% |
| blacklist | 0 | 0.0% | 0 | 0.0% |
| verified | 0 | 0.0% | 0 | 0.0% |
| maxRefDomains | 0 | 0.0% | 0 | 0.0% |
| countryTrafficPresent | 0 | 0.0% | 0 | 0.0% |
| allChannelsTrafficTopCountry | 0 | 0.0% | 0 | 0.0% |
