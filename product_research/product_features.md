# FatGrid Product Features

## Tools (Left Menu)

| Tool | URL | Status |
|------|-----|--------|
| Publisher Price Finder | `/` | Documented |
| Marketplaces | `/inventory` | Documented |
| Backlinks Profile Scanner | `/backlinks-checker` | Documented |
| Check My Backlinks | `/check-my-backlinks` | Documented (NEW feature) |
| Google Search Scanner | `/google-search` | Documented |
| Projects | `/projects` | Documented |
| Outreach | `/outreach` | Experimental (not available) |
| Admin Management | `/admin` | Super admin only |

---

## Concept: Internal Billing Units

**What units are**: Credits that limit access to premium features requiring external resources.

**Core vs Premium Features**:
- **Core features** (e.g., Publisher Price Finder/PPF): Basic DB reads, no unit cost
- **Premium features** (e.g., Google Search Scanner, Backlinks Profile Scanner): Require external resources (Google crawling, Semrush API), consume units

**Why units exist**:
- Premium features use external services we pay for (e.g., crawling Google results, Semrush API)
- Some features require infrastructure per-request (e.g., discovering domain contacts)
- Without limits, these could be easily abused
- Adding users = minimal DB cost, but per-action external calls = real cost

**Current state**:
- Unit costs per action are shown only when user triggers the feature
- Unit prices are NOT listed on pricing page yet
- TODO: Add unit pricing to pricing page after Starter plan features are confirmed

**Unit budgets by plan**: Free started at 120, now 600 (one-time, no refill). Standard gets 5,000/month. Business gets 50,000/month.

**Tracking unit spending**: Query `mongo_internal_payments` with `status = 'PAID'`. The `action_type` field shows what consumed units (google_search_scan, backlinks_profile_scanner, fetching_semrush_info).

---

## Tool: Publisher Price Finder (PPF)

**URL**: `/` (homepage)

**Type**: Core feature (DB read only, no units consumed)

**Use case**: "Someone offered me forbes.com for $500 - is that a fair price?"

**Input**: Textarea with format `domain.com $price` per line (price optional)

**Output**: Table showing your price vs best available price across marketplaces

**No unlock needed**: Publisher names are visible because YOU entered them (not discovering new domains)

### Publisher Price Finder Table Columns

| Column | Description |
|--------|-------------|
| **Publisher** | Domain you entered (always visible, with checkmark if found in DB) |
| **Best Price** | Lowest price across all marketplace offers |
| **User's Price** | The price you entered (what you were quoted) |
| **Price Difference** | Comparison: are you overpaying or getting a deal? |
| **Offers** | Button to see all marketplace sellers (same modal as Marketplaces) |
| **Type** | Guest Post or Link Insertion |
| **Categories** | Website categories |
| **Title** | (and other standard columns from Marketplaces) |

**Row actions**: Same as Marketplaces (favorite, block, copy, etc.)

### Limits by Plan

| Plan | Domains per check |
|------|-------------------|
| Free | 200 |
| Standard | 1,000 |
| Business | 5,000 |

---

## Tool: Marketplaces

**URL**: `/inventory`

**What it is**: Aggregated inventory from multiple major link-building marketplaces.

**Stats**: 329,384 publishers in database

**Unique value**:
- Navigate combined inventory of all marketplaces
- See best prices per publisher across marketplaces
- Understand which marketplaces sell each publisher
- Single interface for multi-marketplace discovery

**Why paywall exists**: Agreements with publishers prevent public sharing of domain names.

**Free vs Paid Experience**:
- **Paid users**: See full domain name in Publisher column (e.g., "google.com", "reddit.com")
- **Free users**: See "Unlock" button instead of domain name
- Click Unlock → reveals domain name (consumes 1 of 3 daily unlocks)

### Marketplaces Table Columns

| Column | Description | Data Source |
|--------|-------------|-------------|
| **Publisher** | Website URL selling links. **Paid**: shows domain. **Free**: "Unlock" button | Aggregated from marketplaces |
| **Best Price** | Lowest price across all marketplace offers for this publisher | Calculated |
| **Offers** | Button showing count of marketplace offers. Click to see all sellers | Aggregated |
| **Type** | Guest Post (new content) or Link Insertion (link in existing content) | Marketplace data |
| **Categories** | Website topic categories (Health, Marketing, Business, etc.) | Crawled/classified |
| **Title** | Crawled title from website's actual pages | Crawler |
| **Language** | Detected language of website content | Crawler |
| **Tags** | User-defined tags. Private to each user | User input |
| **Notes** | User-defined notes. Private to each user | User input |
| **Matching Score** | 0-100% semantic relevance to keyword filter. 100% = exact phrase on site | Calculated |
| **AS** | Authority Score from Semrush | Semrush API |
| **DR** | Domain Rating from Ahrefs | Ahrefs API |
| **Top Country by Organic Traffic** | Country with most organic search visitors | SEO data |
| **Organic Traffic (Top Country)** | Organic search traffic from top country only | SEO data |
| **All Channels Traffic (Top Country)** | All traffic types from top country | SEO data |
| **Ref Domains** | Number of referring domains (backlinks). More = better quality | SEO data |
| **Organic Traffic (Total)** | Total organic search traffic from all countries | SEO data |
| **Min Monthly Organic Traffic** | Lowest monthly organic traffic in recent months | SEO data |
| **All Channels Traffic (Total)** | Total traffic from all sources (organic, paid, direct, etc.) | SEO data |
| **Link Follow** | dofollow, nofollow, or both (different prices) | Marketplace data |
| **Sponsored** | Whether site adds sponsored attribute to links/articles | Marketplace data |
| **Restricted Niches** | Special pricing for restricted topics (Casino, CBD, Crypto, etc.) | Marketplace data |
| **Ref to** | Shows if publisher already links to any of user's projects/clients | Cross-reference |
| **Projects** | Which user projects include this publisher as potential source | User data |
| **Competitors** | Number of competitors tracking this publisher | User data |
| **Creation Date** | When publisher first appeared in FatGrid database | System |

### Row Actions (icons under Publisher)
- Favorite (heart)
- Block (slash)
- Copy (clipboard)
- External link (open site)
- Hide (eye)
- Info (i)
- Add to project (+)
- Flag (report)

### Marketplaces Filters

Filters allow users to narrow down the 329k+ publishers. Tracked via `query_params` in `ch_user_activity_logs`.

**Data source**: `/api/domains/list` requests with `query_params` JSON field.

#### Filter Usage (90 days: 34,932 requests, 539 users)

**BASIC FILTERS (Row 1)**
| UI Filter | API Param | Requests | % Req | Users | % Users |
|-----------|-----------|----------|-------|-------|---------|
| Best Price (from) | minPrice | 3,947 | 11.3% | 109 | 20.2% |
| Best Price (to $) | maxPrice | 6,206 | 17.8% | 146 | 27.1% |
| AS (from) | minAs | 3,857 | 11.0% | 77 | 14.3% |
| AS (to) | maxAs | 2,204 | 6.3% | 55 | 10.2% |
| DR (from) | minDr | 9,702 | 27.8% | 170 | 31.5% |
| DR (to) | maxDr | 5,503 | 15.8% | 96 | 17.8% |
| Organic Traffic (Total) (from) | minTotalOrganicTraffic | 6,443 | 18.4% | 165 | 30.6% |
| Organic Traffic (Total) (to) | maxTotalOrganicTraffic | 2,480 | 7.1% | 75 | 13.9% |
| All Channels Traffic (Total) (from) | minTotalTraffic | 638 | 1.8% | 20 | 3.7% |
| All Channels Traffic (Total) (to) | maxTotalTraffic | 218 | 0.6% | 7 | 1.3% |

**BASIC FILTERS (Row 2)**
| UI Filter | API Param | Requests | % Req | Users | % Users |
|-----------|-----------|----------|-------|-------|---------|
| Min Monthly Organic Traffic (from) | minMonthlyOrganicTraffic | 1,993 | 5.7% | 76 | 14.1% |
| Min Monthly Organic Traffic (to) | maxMonthlyOrganicTraffic | 827 | 2.4% | 38 | 7.1% |
| Category | categories | 18,510 | 53.0% | 227 | 42.1% |
| Restricted Niches | niches | 1,486 | 4.3% | 75 | 13.9% |
| Keyword Match | keyword | 2,296 | 6.6% | 89 | 16.5% |
| Languages | languages | 8,730 | 25.0% | 229 | 42.5% |

**OTHER FILTERS (Row 1)**
| UI Filter | API Param | Requests | % Req | Users | % Users |
|-----------|-----------|----------|-------|-------|---------|
| Sellers | resources | 414 | 1.2% | 25 | 4.6% |
| Link Follow | linkFollow | 1,867 | 5.3% | 71 | 13.2% |
| Sponsored | sponsored | 925 | 2.6% | 36 | 6.7% |
| Top Country by Organic Traffic | databases | 5,214 | 14.9% | 105 | 19.5% |

**OTHER FILTERS (Row 2)**
| UI Filter | API Param | Requests | % Req | Users | % Users |
|-----------|-----------|----------|-------|-------|---------|
| Ref Domains (from) | minRefDomains | 72 | 0.2% | 2 | 0.4% |
| Ref Domains (to) | maxRefDomains | 0 | 0.0% | 0 | 0.0% |
| Organic Traffic (Top Country) (from) | minOrganicTraffic | 596 | 1.7% | 30 | 5.6% |
| Organic Traffic (Top Country) (to) | maxOrganicTraffic | 94 | 0.3% | 4 | 0.7% |
| All Channels Traffic (Top Country) (from) | minAllChannelsTrafficTopCountry | 0 | 0.0% | 0 | 0.0% |
| All Channels Traffic (Top Country) (to) | maxAllChannelsTrafficTopCountry | 0 | 0.0% | 0 | 0.0% |
| Creation Date (Start) | createdAtFrom | 94 | 0.3% | 4 | 0.7% |
| Creation Date (End) | createdAtTo | 94 | 0.3% | 4 | 0.7% |

**OTHER FILTERS (Row 3)**
| UI Filter | API Param | Requests | % Req | Users | % Users |
|-----------|-----------|----------|-------|-------|---------|
| Tags | tags | 12 | 0.0% | 1 | 0.2% |
| Notes | notes | 0 | 0.0% | 0 | 0.0% |
| Favorites | favorites | 84 | 0.2% | 4 | 0.7% |
| Blacklist | blacklist | 0 | 0.0% | 0 | 0.0% |

**OTHER FILTERS (Row 4)**
| UI Filter | API Param | Requests | % Req | Users | % Users |
|-----------|-----------|----------|-------|-------|---------|
| Verified | verified | 0 | 0.0% | 0 | 0.0% |
| Country Traffic Present | countryTrafficPresent | 0 | 0.0% | 0 | 0.0% |

**BOTTOM TABS**
| UI Filter | API Param | Requests | % Req | Users | % Users |
|-----------|-----------|----------|-------|-------|---------|
| Type (All/Guest Post/Link Insertion) | type | 30,280 | 86.7% | 539 | 100.0% |

#### Key Findings

**High usage (>15% users)** - keep prominent:
- Type tabs (100%), Category (42%), Languages (43%), DR (32%), Organic Traffic Total (31%), Price (27%), Top Country (20%), Keyword Match (17%)

**Medium usage (5-15% users)** - can collapse:
- AS (14%), Min Monthly Organic (14%), Restricted Niches (14%), Link Follow (13%), Organic Traffic Total max (14%)

**Zero/near-zero usage** - candidates for removal:
- Notes, Blacklist, Verified, Country Traffic Present, All Channels Traffic (Top Country), maxRefDomains

See [code_samples.md](code_samples.md) for filter analysis queries.

### Component: Offers Modal

**Triggered by**: Clicking "X Offers" button in Offers column

**Shows**: All marketplace sellers for this specific publisher

| Column | Description |
|--------|-------------|
| Seller | Marketplace name (adsy.com, prnews.io, etc.) with warning icons |
| Price | Price from this specific marketplace |
| Type | Article, Contributor Post, etc. |
| Rating | Seller rating (if available) |
| Action | "Go" button (redirect to marketplace) or "Buy" (direct purchase) |
| Updated at | When this offer was last verified |
| Restricted Niches | Special pricing for restricted topics at this seller |

**Example** (msn.com): 6 offers from $299 (adsy.com) to $867 (bazoom.com)

---

## Component: Domain Details (Modal)

**Triggered from**: Publisher Price Finder, Marketplaces (any domain row)

**What it shows**:
- All domain metrics (DR, traffic, price, etc.)
- Marketplace availability
- Price comparison across marketplaces

**For Free users**: Domain name is blurred/hidden

**Database tracking**:
- Endpoint: `/api/tracking/resources-modal-open`
- Table: `resources_modal_opens`

---

## Component: Domain Unlock

**Triggered from**:
- Marketplaces table → Publisher column (where domain name would be)
- Publisher Price Finder results

**What it does**: Reveals the hidden domain name for Free users.

**UI**: Button in place of domain name. After clicking, domain name appears.

**Limits**:
| Plan | Unlocks |
|------|---------|
| Free | 3/day |
| Starter ($5) | TBD (more than free) |
| Standard+ | Unlimited (no unlock needed, sees all domains) |

**Database tracking**:
- Endpoint: `/api/user-unlocks/unlock`
- Table: `user_activity_logs`

---

## Tool: Backlinks Profile Scanner

**URL**: `/backlinks-checker`

**Type**: Premium feature (consumes units - requires Semrush API)

**Use case**: "Which of my competitor's backlinks can I buy?"

**How it works**:
1. Enter any domain (your site or competitor)
2. Pulls referring domains from Semrush API
3. Matches against FatGrid database
4. Shows which backlink sources are available for purchase with prices

**Value**: Instantly see buyable opportunities from competitor backlink analysis

**Consumes units**: Yes (Semrush API call)

**Output**: Can add matching publishers to Projects

---

## Tool: Check My Backlinks

**URL**: `/check-my-backlinks`

**Status**: NEW (added 1 day ago, minimal usage data)

**Use case**: "Are my purchased backlinks still live and unchanged?"

**Problem it solves**: After buying links, publishers may:
- Remove the content
- Change the link URL
- Switch dofollow → nofollow
- Modify anchor text
- Remove the link entirely

**How it works**:
1. Enter list of pages where you placed links
2. Scans pages manually or on schedule
3. Alerts if anything changed

**Output**: Monitoring dashboard showing link health status

---

## Tool: Google Search Scanner

**URL**: `/google-search`

**Type**: Premium feature (consumes units - requires Google crawling)

**Use case**: "Who ranks for my target keyword and can I buy links from them?"

**How it works**:
1. Enter keyword, target market (country), language
2. Performs real Google search
3. Returns ranking websites
4. Matches against FatGrid database for pricing

**Value**:
- **Link insertion**: Find sites already ranking, reach out to add your link to existing content
- **Discovery**: Find publishers relevant to your niche
- **Pricing**: See immediately if ranking sites sell guest posts/link insertions

**Consumes units**: Yes (Google crawling)

**Output**: Can add publishers to Projects

---

## Tool: Projects

**URL**: `/projects`

**Use case**: "Organize all my link building work by client/website"

**What it is**: Folders to organize publishers across multiple clients/websites. Users create a project (folder), save publishers there as "prospects", and track the status of each backlink order.

**Features**:
- Create project per client/website
- Add publishers from ANY tool:
  - Publisher Price Finder
  - Marketplaces
  - Backlinks Profile Scanner
  - Google Search Scanner
- Track: planned backlinks, delivered backlinks, outreach status
- Add same publisher to multiple projects
- Workflow statuses: backlog → outreach → responded → ok_to_proceed → publication_in_progress → invoice_requested → paid → done
- Track competitors and their backlink sources

**Limits by plan**:
| Plan | Projects | Publishers/project | Competitors/project |
|------|----------|-------------------|---------------------|
| Free | 1 | 100 | 3 |
| Standard | 3 | 3,000 | 10 |
| Business | 15 | 15,000 | 50 |

### Projects Data Storage

**MongoDB collections** (synced to DuckDB):

| Collection | DuckDB Table | Description |
|------------|--------------|-------------|
| `projects` | `mongo_projects` | Project folders |
| `projectProspects` | `mongo_project_prospects` | Publishers saved to projects |
| `projectCompletedOrders` | `mongo_project_completed_orders` | Backlinks purchased via projects |
| `projectCompetitors` | *(not synced)* | Competitor domains tracked |
| `projectCompetitorDomains` | *(not synced, 217k rows)* | Backlinks from competitor analysis |

### Projects Usage Stats (as of 2026-01-11)

| Metric | Value |
|--------|-------|
| Total projects | 48 |
| Users with projects | 30 |
| Empty projects (no prospects) | 22 (46%) |
| Publishers saved (prospects) | 1,971 |
| Completed orders tracked | 125 |

**Prospect Status Funnel:**
- 86.4% in "backlog" (not contacted)
- 4.3% in "outreach"
- 7.1% marked as "done"

**Key Finding**: One power user (daria@xamsor.com) accounts for 87% of completed orders - likely internal team.

---

## Tool: Outreach

**URL**: `/outreach` (in left menu)

**Status**: EXPERIMENTAL - Not available to users yet

---

## Tool: Admin Management

**URL**: `/admin`

**Status**: Super admin only - not relevant for pricing research

---

## Component Relationships (Many-to-Many)

```
Publisher Price Finder ─────┐
                            │
Marketplaces ───────────────┼──► Add to Projects ──► Track/Manage
                            │
Backlinks Profile Scanner ──┤
                            │
Google Search Scanner ──────┘

All tools ──► Offers Modal (see marketplace prices)
All tools ──► Row actions (favorite, block, etc.)

Marketplaces only ──► Domain Unlock (free users)
```

---

## Database Mapping

| Component | API Endpoint | DB Table | Notes |
|-----------|--------------|----------|-------|
| Publisher Price Finder | `/api/domains/search` | `ch_user_activity_logs` | request_body has domain list |
| Marketplaces Browse | `/api/domains/list` | `ch_user_activity_logs` | query_params has filters |
| Domain Details | `/api/tracking/resources-modal-open` | `ch_resources_modal_opens` | domain, type, email |
| Domain Unlock | `/api/user-unlocks/unlock` | `ch_user_activity_logs` | |
| My Unlocks | `/api/user-unlocks/my-unlocks` | `ch_user_activity_logs` | |
| CSV Export | `/api/domains/download-csv` | `ch_user_activity_logs` | shared by multiple tools |
| Google Sheet | `/api/domains/google-sheet` | `ch_user_activity_logs` | shared by multiple tools |
| Google Search | `/api/google-search/*` | `ch_user_activity_logs` | premium, consumes units |
| Projects | `/api/projects*` | `ch_user_activity_logs` + `mongo_projects` | activity logs + actual data |
| Project Prospects | `/api/project-prospects*` | `ch_user_activity_logs` + `mongo_project_prospects` | activity logs + actual data |
| Favorites | `/api/favorite-domains` | `ch_user_activity_logs` | |
| Referring Domains | `/api/referring-domains/*` | `ch_user_activity_logs` | |
| Orders (payment) | `/api/orders/*` | `mongo_orders` | payment/transaction data |
| Orders (fulfillment) | ClickUp API | `clickup_orders` | workflow status |

---

## Orders Data Model

Orders are backlink purchases where users buy guest posts or link insertions from publishers listed on FatGrid.

### Two Data Sources

| Source | DuckDB Table | Purpose | Join Key |
|--------|--------------|---------|----------|
| **MongoDB** | `mongo_orders` | Payment/transaction data | `order_id` |
| **ClickUp** | `clickup_orders` | Fulfillment workflow tracking | `order_number` |

### Coverage (as of 2026-01-11)

| Metric | Count |
|--------|-------|
| Total MongoDB orders | 222 |
| Total ClickUp tasks | 89 |
| Orders in both sources | 84 |
| MongoDB only (abandoned/early stage) | 138 |
| ClickUp only (manual requests) | 5 |

### MongoDB Order Fields (`mongo_orders`)

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | INTEGER | Sequential order number (1-222) |
| `domain` | VARCHAR | Publisher domain (e.g., "forbes.com") |
| `buyer_email` | VARCHAR | Customer email |
| `seller_email` | VARCHAR | Publisher/seller email |
| `price` | DOUBLE | Order amount in USD |
| `status` | VARCHAR | Order status (see lifecycle below) |
| `payment_status` | VARCHAR | Stripe payment status |
| `stripe_payment_id` | VARCHAR | Stripe payment intent ID |
| `doc_url` | VARCHAR | Google Doc URL for content |
| `created_at` | TIMESTAMP | Order creation time |

### ClickUp Order Fields (`clickup_orders`)

| Field | Type | Description |
|-------|------|-------------|
| `order_number` | INTEGER | Parsed from task name, matches `order_id` |
| `name` | VARCHAR | Full task name with order details |
| `domain` | VARCHAR | Publisher domain (parsed from name) |
| `amount_usd` | DECIMAL | Price (parsed from name) |
| `customer_email` | VARCHAR | Customer email (parsed from name) |
| `status` | VARCHAR | ClickUp workflow status |
| `status_type` | VARCHAR | ClickUp status type (open/closed) |
| `date_created` | TIMESTAMP | Task creation time |
| `date_done` | TIMESTAMP | Completion time (if completed) |

### Order Lifecycle

**MongoDB statuses** (payment flow):
```
created → order_submitted → requires_capture → accepted_by_seller → paid → published
```

**ClickUp statuses** (fulfillment flow):
```
new orders → outreach → review + capture → sent to seller/marketplace → completed
                     ↘ stuck/delay → edits → completed
                                          ↘ cancelled
```

### Why 138 Orders Are MongoDB-Only

| MongoDB Status | Count | Explanation |
|----------------|-------|-------------|
| `created` / `created` | 131 | Abandoned carts - user started but never completed checkout |
| `order_submitted` / `failed` | 4 | Payment failed |
| `order_submitted` / `succeeded` | 3 | Payment succeeded but ClickUp task not yet created |

### Key Queries

**Unified order view (both sources)**:
```sql
SELECT m.order_id, m.domain, m.buyer_email, m.price,
       m.payment_status, c.status as fulfillment_status
FROM mongo_orders m
JOIN clickup_orders c ON m.order_id = c.order_number
ORDER BY m.order_id DESC
```

**Orders by user**:
```sql
SELECT buyer_email, COUNT(*) as orders, SUM(price) as total_spent
FROM mongo_orders
WHERE status != 'created'  -- exclude abandoned carts
GROUP BY buyer_email
ORDER BY total_spent DESC
```

---

## IMPORTANT: Export Endpoint Ambiguity

**`/api/domains/download-csv` and `/api/domains/google-sheet` are shared endpoints** used by multiple features:

| Source Feature | How to Identify | Free User Access |
|----------------|-----------------|------------------|
| **Publisher Price Finder** | Preceded by `/api/domains/search` | ✅ Allowed (you entered the domains) |
| **Marketplaces** | Preceded by `/api/domains/list` | ❌ Blocked (UI prevents, but check for loopholes) |

**When analyzing export logs**, you MUST check what endpoint preceded the export using `LAG(url)`.

See [code_samples.md](code_samples.md) for the query to disambiguate export sources.

**90-day breakdown** (free users):
- 65% exports from Publisher Price Finder (legitimate)
- 4% exports from Marketplaces (potential loophole)
- 31% other/unclear context

---

See [product_url_mapping.md](product_url_mapping.md) for full URL crawl results.
