# Clarity Sync Cloud Function

Automatically syncs Microsoft Clarity analytics data to BigQuery on a daily schedule.

## Architecture

```
Clarity API ──► Cloud Function ──► BigQuery (clarity dataset)
                     ↑
              Cloud Scheduler
              (daily 6 AM UTC)
```

## BigQuery Tables

| Table | Description |
|-------|-------------|
| `clarity.snapshots` | Daily metrics: sessions, users, engagement, clicks |
| `clarity.devices` | Device type breakdown (Desktop, Mobile, Tablet) |
| `clarity.countries` | Country breakdown |
| `clarity.browsers` | Browser breakdown |
| `clarity.os` | Operating system breakdown |
| `clarity.pages` | Popular pages with visit counts |

## Deployment

### Prerequisites

1. **gcloud CLI** installed and authenticated:
   ```bash
   gcloud auth login
   gcloud config set project getlinkspro-453615
   ```

2. **Set Clarity token** (from your .env file):
   ```bash
   export CLARITY_API_TOKEN='your-token-here'
   export CLARITY_PROJECT_ID='pf8kyjwawu'
   ```

### Deploy

```bash
cd cloud_functions/clarity_sync
./deploy.sh
```

This will:
1. Enable required GCP APIs
2. Create BigQuery dataset `clarity`
3. Deploy the Cloud Function
4. Create Cloud Scheduler job (daily at 6 AM UTC)

## Manual Trigger

```bash
# Test the function
curl -X POST https://us-central1-getlinkspro-453615.cloudfunctions.net/clarity-sync

# With custom days (1-3)
curl -X POST https://us-central1-getlinkspro-453615.cloudfunctions.net/clarity-sync \
  -H "Content-Type: application/json" \
  -d '{"days": 1}'
```

## View Logs

```bash
gcloud functions logs read clarity-sync --region=us-central1 --gen2
```

## Query Data

```sql
-- Latest snapshot
SELECT * FROM `getlinkspro-453615.clarity.snapshots`
ORDER BY snapshot_time DESC LIMIT 1;

-- Sessions trend over time
SELECT
  DATE(snapshot_time) as date,
  total_sessions,
  distinct_users,
  rage_click_pct
FROM `getlinkspro-453615.clarity.snapshots`
ORDER BY snapshot_time;

-- Top countries
SELECT name, SUM(sessions) as total_sessions
FROM `getlinkspro-453615.clarity.countries`
GROUP BY name
ORDER BY total_sessions DESC
LIMIT 10;

-- Top pages
SELECT url, SUM(visits) as total_visits
FROM `getlinkspro-453615.clarity.pages`
GROUP BY url
ORDER BY total_visits DESC
LIMIT 20;
```

## Cost

- Cloud Function: Free tier (2M invocations/month)
- Cloud Scheduler: Free tier (3 jobs free)
- BigQuery: Free tier (10GB storage, 1TB queries/month)

**Estimated cost: $0/month** for this volume.

## Troubleshooting

### Function not triggering
```bash
# Check scheduler job status
gcloud scheduler jobs describe clarity-daily-sync --location=us-central1

# Run job manually
gcloud scheduler jobs run clarity-daily-sync --location=us-central1
```

### API errors
Check that CLARITY_API_TOKEN is valid and not expired. Tokens are long-lived but can be regenerated in Clarity settings.

### BigQuery permission errors
The Cloud Function uses the default compute service account. Ensure it has BigQuery Data Editor role:
```bash
gcloud projects add-iam-policy-binding getlinkspro-453615 \
  --member="serviceAccount:getlinkspro-453615@appspot.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"
```
