# BigQuery Data Pipeline Setup

## Goal
Automatic data collection from GA4, GSC, and Clarity into BigQuery (runs 24/7), then sync to local DuckDB on demand.

```
GA4 ──────► BigQuery ──────► DuckDB (local)
GSC ──────►    ↑              ↑
Clarity ───►   │              │
        (auto daily)    (on-demand sync)
```

## Current Status (Jan 9, 2026)

### ✅ Working
| Source | Dataset | Tables | Status |
|--------|---------|--------|--------|
| GSC | `searchconsole_fatgrid` | 3 tables, 1,127 rows | ✅ Active |
| Clarity | `clarity` | 6 tables, 109 rows | ✅ Active (Cloud Function) |
| GA4 | `fatgrid_analytics` | 0 tables | ⏳ Waiting (24-48h) |

### Service Account
- Email: `fatgrid-analytics@getlinkspro-453615.iam.gserviceaccount.com`
- File: `db_api/getlinkspro-453615-b3d009f51fb5.json`
- Roles: BigQuery Job User, BigQuery Data Viewer

### Sync Script
Created `db_api/sync_bigquery.py` - syncs BigQuery → DuckDB

**Usage:**
```bash
python3 db_api/sync_bigquery.py              # Sync all data
python3 db_api/sync_bigquery.py --days 30    # Last 30 days
python3 db_api/sync_bigquery.py --source gsc # Only GSC
```

**Last sync:** Jan 9, 2026
- GSC: 770 rows (site + URL impressions)
- Clarity: 72 rows (6 tables)
- GA4: Pending

## Clarity → BigQuery (Solved)
Deployed Cloud Function that syncs Clarity data daily to BigQuery.

- **Dataset**: `clarity`
- **Schedule**: Daily at 6 AM UTC
- **Tables**: `snapshots`, `devices`, `countries`, `browsers`, `os`, `pages`
- **Function URL**: https://us-central1-getlinkspro-453615.cloudfunctions.net/clarity-sync

See [cloud_functions/clarity_sync/README.md](cloud_functions/clarity_sync/README.md) for details.

## Cost Estimate
- BigQuery storage: Free up to 10GB
- BigQuery queries: Free up to 1TB/month
- GA4 streaming export: ~$0.05/GB
- Estimated for fatgrid.com traffic: **$0-5/month**

## Next Session: Start Here

1. **Check GA4 export status**
   Run: `python3 db_api/sync_bigquery.py`
   If GA4 tables exist, they'll sync automatically.

2. **If GA4 still pending**
   Wait another day. Google says 24-48h, sometimes longer for first export.

3. **Once GA4 active**
   - Run full historical sync: `python3 db_api/sync_bigquery.py --days 365`
   - Analyze user journeys before registration (session paths, traffic sources)
   - Cross-reference with MongoDB subscriptions to find conversion patterns

## Planned: User Journey Analysis

Once GA4 is active, analyze:
- Traffic source → pages visited → signup conversion
- Time from first visit to registration
- Most effective acquisition channels
- User behavior patterns before subscribing

Query example:
```sql
-- Users who signed up (events with /auth/google-success page)
SELECT user_pseudo_id, event_timestamp, traffic_source.source
FROM `getlinkspro-453615.fatgrid_analytics.events_*`
WHERE (SELECT value.string_value FROM UNNEST(event_params)
       WHERE key = 'page_location') LIKE '%/auth/google-success%'
```
