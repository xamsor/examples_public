# Pricing Tier Research: Starter Plan ($5)

## Goal

Establish a new "Starter" pricing tier at $5 to bridge free → paid conversion.

**Note**: Given current churn rates (~17% monthly), this initiative is ON HOLD. See [business_metrics.md](business_metrics.md) for churn analysis.

---

## Data Sources

**Primary: DuckDB** (`warehouse.duckdb`) - all queries should use this first.

| DuckDB Table | Source | Purpose |
|--------------|--------|---------|
| `ch_user_activity_logs` | ClickHouse | Feature usage, searches, filters |
| `ch_resources_modal_opens` | ClickHouse | Domain detail views |
| `mongo_users` | MongoDB | User accounts, balances |
| `mongo_subscriptions` | MongoDB | Subscription status, churn dates |
| `mongo_payments` | MongoDB | Stripe payment history |
| `mongo_user_unlocks` | MongoDB | Unlock history |
| `mongo_internal_payments` | MongoDB | Internal billing units spending |

**Sync before analysis:**
```bash
python3 db_api/clickhouse_to_duckdb.py  # ClickHouse → DuckDB
python3 db_api/sync_mongo.py            # MongoDB → DuckDB
```

---

## Feature Usage (90 days, verified 2026-01-10)

For current user counts and revenue metrics, see [business_metrics.md](business_metrics.md).

### Core Features

| Feature | Free Users | Free Requests | Standard Users | Standard Requests |
|---------|------------|---------------|----------------|-------------------|
| Publisher Price Finder | 587 | 27,345 | 37 | 2,823 |
| CSV Exports | 82 | 952 | 31 | 408 |
| Google Sheets Exports | 25 | 109 | 12 | 183 |

### Unit-Consuming Features: Page Views vs Actual Actions

**IMPORTANT**: Activity logs include both page views and actual actions. Only actual actions consume units.

| Feature | Action Type | Free Users | Free Requests | Std Users | Std Requests |
|---------|-------------|------------|---------------|-----------|--------------|
| **Domain Unlocks** | View unlock history | 751 | 6,355 | 15 | 96 |
| | **Actual unlock** | **286** | **1,063** | 1 | 3 |
| **Google Search** | Load page/config | 206 | 1,262 | 22 | 458 |
| | View results list | 205 | 1,512 | 22 | 576 |
| | View specific result | 85 | 5,315 | 11 | 4,645 |
| | **Actual search** | **86** | **296** | **11** | **157** |
| **Backlinks Scanner** | View results list | 165 | 414 | 13 | 41 |
| | View specific result | 39 | 60 | 1 | 1 |
| | **Trigger scan** | **~90** | **235** | **~10** | **21** |

---

## Publisher Price Finder Deep Dive

### Overall Usage (90 days)

| Tier | Users | Requests | Domains Analyzed | Domains/User |
|------|-------|----------|------------------|--------------|
| Free | 587 | 20,542 | 966,343 | 1,646 |
| Standard | 37 | 2,823 | 297,686 | 8,046 |
| Business | 9 | 1,244 | 3,926 | 436 |

**Standard users analyze 4.9x more domains per user than free.**

### Batch Sizes (domains per request)

| Batch Size | Free Requests | Free % | Standard Requests | Standard % |
|------------|---------------|--------|-------------------|------------|
| 1 domain | 11,770 | 57% | 1,538 | 54% |
| 2-5 domains | 871 | 4% | 195 | 7% |
| 6-10 domains | 662 | 3% | 57 | 2% |
| 11-20 domains | 719 | 4% | 89 | 3% |
| 21-50 domains | 1,236 | 6% | 119 | 4% |
| 51-100 domains | 1,296 | 6% | 339 | 12% |
| 101-200 domains | 3,439 | 17% | 128 | 5% |
| 200+ domains | 549 | 3% | 358 | 13% |

### Daily Domains Analyzed

| Domains/Day | Free Users | Standard Users |
|-------------|------------|----------------|
| 1-10 | 481 | 32 |
| 11-50 | 189 | 23 |
| 51-100 | 77 | 11 |
| 101-200 | 86 | 5 |
| 201-500 | 64 | 13 |
| 501-1000 | 50 | 7 |
| 1000+ | 51 | 8 |

**51 free users analyze 1000+ domains/day** - prime conversion candidates.

### Monthly Activity (days active in 90-day period)

| Days Active | Free Users | Standard Users |
|-------------|------------|----------------|
| 1 day | 260 (44%) | 5 (14%) |
| 2-3 days | 148 (25%) | 7 (19%) |
| 4-7 days | 84 (14%) | 9 (24%) |
| 8-14 days | 50 (9%) | 7 (19%) |
| 15-30 days | 34 (6%) | 4 (11%) |
| 30+ days | 11 (2%) | 5 (14%) |

**44% of free users use tool once and leave.**

---

## Unlock Demand Analysis

### Users Hitting 3 Unlocks/Day Cap (90 days)

| Metric | Value |
|--------|-------|
| Unique users who hit cap | 183 |
| Total days cap was hit | 286 |
| % of unlock sessions hitting cap | 64% |

### Domain Views vs Unlocks (Frustration Analysis)

| Frustration Level | Users | Avg Views/User |
|-------------------|-------|----------------|
| Very frustrated (20+ views/unlock) | 11 | 134 |
| Frustrated (10-19 views/unlock) | 7 | 40 |
| Moderate (5-9 views/unlock) | 20 | 28 |
| Low frustration (1-4 views/unlock) | 86 | 7 |

**38 users have 5+ views per unlock** - frustrated browsers.

### Return Frequency of Heavy Unlockers

| Days Active | Users | Total Unlocks |
|-------------|-------|---------------|
| 1 day | 218 | 494 |
| 2 days | 39 | 188 |
| 3+ days | 29 | 381 |

**68 users (24%) returned 2+ days to unlock more.**

---

## Export Usage (90 days)

### Export Source Disambiguation

**IMPORTANT**: `/api/domains/download-csv` is shared by multiple features.

| Export Source | Free Users | Exports | % of Total |
|---------------|------------|---------|------------|
| Publisher Price Finder | ~70 | 678 | 65% |
| Marketplaces | ~10 | 38 | 4% |
| Other/unclear | ~25 | 327 | 31% |

Most free user exports (65%) are from Publisher Price Finder (legitimate).

### Export Volume

| Tier | Users | Total Exports | Exports/User |
|------|-------|---------------|--------------|
| Free | 82 | 952 | 11.6 |
| Standard | 31 | 408 | 13.2 |
| Business | 3 | 178 | 59.3 |

---

## Projects Usage (90 days)

| Tier | Users | Total Actions | Actions/User |
|------|-------|---------------|--------------|
| Free | 576 | 14,417 | 25.0 |
| Standard | 36 | 2,126 | 59.1 |
| Business | 8 | 370 | 46.2 |

High adoption across all tiers. Free tier already limited to 1 project, 100 publishers.

---

## Free vs Standard Gap

| Metric | Free | Standard | Gap |
|--------|------|----------|-----|
| Domains/user (90d) | 1,646 | 8,046 | 4.9x |
| Days active (90d avg) | 2.8 | 9.5 | 3.4x |
| 200+ domain batches | 3% | 13% | 4.3x |
| Google Sheets/user | 4.0 | 14.6 | 3.7x |
| Project actions/user | 25 | 59 | 2.4x |

---

## Proposed Starter Tier ($5/month) - ON HOLD

### Complete Pricing Comparison

| Feature | New Free | Starter ($5) | Standard ($29) |
|---------|----------|--------------|----------------|
| **Publisher Price Finder** | | | |
| └ Domains/check | 50 | 200 | 1,000 |
| **Marketplaces** | | | |
| └ Domain unlocks | 40/month | 400/month | Unlimited |
| └ See all domain names | No | No | Yes |
| **Exports** | | | |
| └ CSV Export | No | Yes | Yes |
| └ Google Sheets | No | No | Yes |
| **Google Search Scanner** | | | |
| └ Daily searches | 5/day | 30/day | Unlimited |
| **Projects** | | | |
| └ Number of projects | 1 | 2 | 3 |
| └ Publishers/project | 100 | 500 | 3,000 |
| **Units** | | | |
| └ Monthly budget | 120 | 1,200 | 5,000 |

### Why ON HOLD

With 17% monthly churn and $41 Standard LTV, a $5 plan would likely have:
- Higher churn than Standard
- LTV of ~$7-15
- Added complexity for minimal revenue

**Recommendation**: Fix churn first, then revisit Starter tier.

---

## Power Users for Conversion Targeting

| Email | Unlocks | Exports | Google Searches | Backlink Scans |
|-------|---------|---------|-----------------|----------------|
| info@extremelybacklinks.com | 23 | 93 | 29 | 21 |
| prenclavsmareks@gmail.com | 12 | 3 | 55 | 5 |
| zaribhi9@gmail.com | 23 | 0 | 30 | 2 |

---

## Query Examples

See [code_samples.md](code_samples.md) for all database queries.
