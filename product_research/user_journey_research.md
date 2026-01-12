# User Journey Research: Feature Usage by Segment

## Data Source

**ClickHouse** `fatgrid_logs_prod_db.user_activity_logs`
- Period: 90 days
- Fields: `email`, `subscription_type`, `url`, `date`

For user counts and subscription metrics, see [business_metrics.md](business_metrics.md).

---

## Feature Usage Table (90 days, verified 2026-01-10)

| # | Feature | Endpoint | Free Users | Free % | Std Users | Std % | Biz Users | Biz % |
|---|---------|----------|------------|--------|-----------|-------|-----------|-------|
| 1 | Publisher Price Finder | `/api/domains/search` | 587 | 70% | 37 | 71% | 9 | 82% |
| 2 | Domain List Browse | `/api/domains/list*` | 506 | 61% | 48 | 92% | 10 | 91% |
| 3 | Domain Details | `/api/tracking/resources-modal-open` | 380 | 46% | 29 | 56% | 6 | 55% |
| 4 | CSV Export | `/api/domains/download-csv` | 82 | 10% | 31 | 60% | 3 | 27% |
| 5 | Google Sheet Export | `/api/domains/google-sheet` | 25 | 3% | 12 | 23% | 1 | 9% |
| 6 | Projects | `/api/projects*` | 576 | 69% | 36 | 69% | 8 | 73% |
| 7 | Favorites | `/api/favorite*` | 28 | 3% | 4 | 8% | 1 | 9% |

### Unit-Consuming Features: Page Views vs Actual Actions

**IMPORTANT**: Logs include page views AND actual actions. Only actual actions consume units.

| # | Feature | Type | Endpoint | Free Users | Free % | Std Users | Std % |
|---|---------|------|----------|------------|--------|-----------|-------|
| 1 | Domain Unlock | **Page view** | `/api/user-unlocks/my-unlocks` | 751 | 90% | 15 | 29% |
| | | **Action** | `/api/user-unlocks/unlock` | **286** | **34%** | 1 | 2% |
| 2 | Google Search | **Page view** | `/api/google-search/config/*` | 206 | 25% | 22 | 42% |
| | | **Action** | `/api/google-search/search` | **86** | **10%** | 11 | 21% |
| 3 | Backlinks Scanner | **Page view** | `/api/referring-domains/list*` | 165 | 20% | 13 | 25% |
| | | **Action** | `/api/referring-domains/check*` | **~90** | **~11%** | ~10 | ~19% |

**Key Finding**: The original "90% use unlocks" was wrong - it counted page views (`/my-unlocks`), not actual unlocks (`/unlock`).

---

## Usage Intensity Table (avg actions per user, 90 days)

| # | Feature | Free Avg | Std Avg | Biz Avg | Std/Free Ratio |
|---|---------|----------|---------|---------|----------------|
| 1 | Publisher Price Finder | 35.0 | 76.3 | 138.2 | 2.2x |
| 2 | Domain List Browse | 26.6 | 393.6 | 154.4 | 14.8x |
| 3 | Domain Details | 23.1 | 55.6 | 161.0 | 2.4x |
| 4 | Domain Unlock | 3.7 | 3.0 | 3.0 | 0.8x |
| 5 | CSV Export | 11.6 | 13.2 | 59.3 | 1.1x |
| 6 | Google Sheet Export | 4.4 | 15.2 | 4.0 | 3.5x |
| 7 | Google Search | 40.9 | 265.3 | 11.7 | 6.5x |
| 8 | Projects | 18.4 | 47.0 | 46.2 | 2.6x |
| 9 | Favorites | 5.1 | 22.0 | 1.0 | 4.3x |
| 10 | Referring Domains | 3.8 | 3.4 | 6.2 | 0.9x |

---

## Key Observations

### High Adoption Features (>50% of free users)
1. **Publisher Price Finder** (71%) - Core feature, everyone uses
2. **Projects** (69%) - Organization feature
3. **Domain List Browse** (61%) - Catalog browsing

### Medium Adoption Features (20-50% of free users)
4. **Domain Details** (46%) - Viewing domain info
5. **Domain Unlock** (34%) - Revealing contacts
6. **Google Search** (25%) - Finding opportunities
7. **Referring Domains** (22%) - Backlink analysis

### Low Adoption Features (<20% of free users)
8. **CSV Export** (10%) - Data export
9. **Favorites** (3%) - Saving domains
10. **Google Sheet Export** (3%) - GSheet integration

---

## Paywall Candidates Analysis

### Tier 1: Limit on Free (high impact)
| Feature | Free Users | If Limited | Impact |
|---------|------------|------------|--------|
| Domain Details | 380 | Cap 10/day | 380 users hit wall |
| Domain Unlock | 286 | Cap 3/month | 286 users hit wall |
| Publisher Price Finder | 587 | Cap 20/day | ~200 power users hit wall |

### Tier 2: Move to Starter (medium impact)
| Feature | Free Users | Action | Impact |
|---------|------------|--------|--------|
| CSV Export | 82 | Remove from free | 82 users need upgrade |
| Google Search | 205 | Limit 10/day | 205 users affected |

### Tier 3: Keep Free (low impact, builds habit)
| Feature | Reason |
|---------|--------|
| Domain List Browse | Core discovery, builds engagement |
| Projects | Organization, increases stickiness |
| Referring Domains | Low intensity (3.8/user), keeps users exploring |

---

## Next Steps

See [business_metrics.md](business_metrics.md) for churn analysis before implementing paywall changes.
