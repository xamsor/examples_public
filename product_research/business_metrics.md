# FatGrid Business Metrics

**Last updated**: 2026-01-11

All metrics from DuckDB warehouse. Run `python3 db_api/sync_mongo.py` before querying for fresh data.

---

## Revenue

| Metric | Value |
|--------|-------|
| **MRR** | $2,374 |
| Standard (38 users x $29) | $1,102 |
| Business (8 users x $159) | $1,272 |
| Revenue at risk (pending cancel) | $87 (3 Standard) |

Additional revenue stream: ~$1,000/mo profit from direct link sales on platform.

---

## User Base

### Accounts

| Metric | Value |
|--------|-------|
| Total accounts | 1,750 |
| Active (90 days) | 860 |
| WAU (average) | ~170 |
| WAU peak | 243 (Dec 1, 2025) |

### Subscription Breakdown (90-day active)

| Tier | Users | % of Active | Avg Requests/User |
|------|-------|-------------|-------------------|
| Free | 833 | 93% | 179 |
| Standard | 52 | 6% | 9,501 |
| Business | 11 | 1% | 705 |

---

## Churn

### Monthly Logo Churn Rate

| Month | Active at Start | Churned | Churn Rate |
|-------|-----------------|---------|------------|
| Jan 2026 | 47 | 2 | 4.3% (partial) |
| Dec 2025 | 48 | 7 | 14.6% |
| Nov 2025 | 47 | 11 | 23.4% |
| Oct 2025 | 43 | 9 | 20.9% |
| Sep 2025 | 37 | 5 | 13.5% |
| Aug 2025 | 29 | 6 | 20.7% |
| Jul 2025 | 22 | 3 | 13.6% |

**Average monthly churn: ~17%** (benchmark: good B2B SaaS is 3-5%)

### Subscription Lifetime

| Plan | Median Lifetime | Avg Lifetime | Estimated LTV |
|------|-----------------|--------------|---------------|
| Standard | 31 days | 43 days | $41 |
| Business | 61 days | 65 days | $345 |

### Churn Timing (Churned Subscriptions)

| Lifetime | Standard | Business |
|----------|----------|----------|
| 0-30 days | 15 (37%) | 3 (33%) |
| 31-60 days | 19 (46%) | 1 (11%) |
| 61-90 days | 3 (7%) | 3 (33%) |
| 91-180 days | 4 (10%) | 2 (22%) |

**83% of Standard churn happens in first 60 days.**

### Active Customer Tenure

| Plan | Active Count | Avg Days | Median Days |
|------|--------------|----------|-------------|
| Business | 8 | 178 | 207 |
| Standard | 38 | 117 | 110 |

### Monthly Net Change

| Month | Standard New | Standard Churned | Net |
|-------|--------------|------------------|-----|
| Jan 2026 | 2 | 2 | 0 |
| Dec 2025 | 6 | 6 | 0 |
| Nov 2025 | 10 | 8 | +2 |
| Oct 2025 | 12 | 8 | +4 |

**Pattern**: Net growth near zero since Nov 2025 - treadmill effect.

---

## Subscription History

| Metric | Value |
|--------|-------|
| Total ever subscribed | 97 |
| Currently active | 46 |
| Total churned | 50 |
| All-time churn rate | 51.5% |

---

## Customer Segments

### Business Tier ($159/mo)

**Who they are** (from founder knowledge):
- Marketplaces monitoring competitors and enforcing exclusivity agreements
- Large SEO/link-building agencies integrating via API

**Why they retain better**: Their use case (competitive intelligence, data integration) doesn't depend on price accuracy the same way Standard users do.

### Standard Tier ($29/mo)

**Primary use case**: Find and buy cheaper links via price comparison.

**Churn driver (ASSUMPTION)**: Data accuracy issues - stale marketplace prices lead to failed purchases and lost trust. Needs validation via churned user interviews.

---

## Acquisition

| Channel | Notes |
|---------|-------|
| LinkedIn | Primary channel, founder's personal brand |
| SEO | Recently started, early results |
| Word of mouth | Some, not tracked |
| Paid marketing | Not tested |

**CAC**: Effectively $0 (founder time only).

---

## Market Size

| Segment | Total Market | FatGrid Share |
|---------|--------------|---------------|
| Marketplaces | ~20 worldwide | ~8 (40%) |
| Agencies | Large | Unknown |

Marketplace segment is nearly saturated. Agency segment is growth opportunity.

---

## Competitor Acquisition Opportunity

Competitor offering to sell for $50k:
- ~15k monthly visitors
- Free product, no revenue
- Data quality issues (some data 1+ year old)
- User-submitted offers without validation

---

## Key Insights

1. **Churn is the critical problem** - 17% monthly churn makes growth impossible
2. **Business tier retains 2x longer** than Standard
3. **Business customers have different use case** - less sensitive to price accuracy
4. **Standard users churn in first 60 days** - early experience is critical
5. **Net growth is zero** - new subs replacing churned subs

---

## Assumptions Requiring Validation

| Assumption | Status | How to Validate |
|------------|--------|-----------------|
| Data accuracy causes Standard churn | UNVALIDATED | Interview 5 churned users |
| Business customers stay for competitive intel | PARTIALLY VALIDATED | From founder knowledge |
| Price staleness is the main accuracy issue | UNVALIDATED | Interview churned users |

---

## Queries

All metrics from `warehouse.duckdb`. See [code_samples.md](code_samples.md) for query patterns.

```bash
python3 db_api/sync_mongo.py  # Refresh MongoDB data before querying
```
