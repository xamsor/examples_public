# FatGrid Product URL Mapping

Crawled: 2026-01-10
Source: https://go.fatgrid.com

---

## Public Pages (no auth required)

| URL | Title | Purpose |
|-----|-------|---------|
| `/` | Publisher Price Finder | Paste publisher list, get prices |
| `/inventory` | Marketplaces | Browse aggregated marketplace inventory |
| `/backlinks-checker` | Backlinks Profile Scanner | Analyze backlink profiles |
| `/check-my-backlinks` | Check My Backlinks | Check your own backlinks |
| `/google-search` | Google Search Scanner | Find opportunities via Google |
| `/projects` | Projects | Organize outreach work |
| `/pricing` | Pricing | View subscription plans |
| `/auth/login` | Login | User authentication |
| `/auth/register` | Register | New user signup |

## External Links

| URL | Purpose |
|-----|---------|
| `https://hub.getlinks.pro/blog/` | Blog |
| `https://free-tools.fatgrid.com/` | Free Tools |
| `https://fatgrid.com/terms-and-conditions/` | Terms |
| `https://fatgrid.com/privacy-policy/` | Privacy Policy |

---

## Current Pricing (from /pricing page)

| Plan | Price | Key Features |
|------|-------|--------------|
| **Free** | $0 | Demo Marketplace, 200 domains/check, 600 units, 1 project, 3 unlocks/day |
| **Standard** | $29/mo | Full Marketplace, 1000 domains/check, 5000 units, 3 projects |
| **Business** | $159/mo | Full Marketplace, 5000 domains/check, 50000 units, 15 projects, API |

### Detailed Feature Comparison

| Feature | Free | Standard | Business |
|---------|------|----------|----------|
| Marketplaces | Demo (blurred) | Full access | Full access |
| Price Finder | 200 domains | 1000 domains | 5000 domains |
| Units | 600 | 5000 | 50000 |
| Projects | 1 | 3 | 15 |
| Publishers/project | 100 | 3000 | 15000 |
| Competitors/project | 3 | 10 | 50 |
| Export | 100 records max | Full | Full |
| Support | Limited | General | Premium |
| Early access | No | Yes | Higher priority |
| API | No | No | Yes |

---

## Page Components (from crawl)

### Home Page (`/`)
- **Input**: Textarea for pasting publisher list with prices
- **Placeholder**: `forbes.com $200, usatoday.com $300...`
- **Purpose**: Quick price lookup across marketplaces

### Inventory/Marketplaces (`/inventory`)
- **Filters**: Price range (from/to $), DR range, Traffic range
- **Purpose**: Browse and filter aggregated inventory
- **Auth required**: Partial (demo mode for free users)

### Protected Pages (require login)
- `/backlinks-checker`
- `/check-my-backlinks`
- `/google-search`
- `/projects`

---

## API Endpoints (from ClickHouse logs)

| Endpoint | Feature | Hits (90d) |
|----------|---------|------------|
| `/api/domains/search` | Domain Search | 24,601 |
| `/api/domains/list` | Domain List Browse | ~4,200 |
| `/api/tracking/resources-modal-open` | Domain Details View | 11,374 |
| `/api/user-unlocks/unlock` | Reveal Domain Name | 1,069 |
| `/api/user-unlocks/my-unlocks` | View My Unlocks | 6,468 |
| `/api/domains/download-csv` | CSV Export | 1,538 |
| `/api/domains/google-sheet` | Google Sheet Export | 255 |
| `/api/google-search/*` | Google Search Scanner | ~14,000 |
| `/api/projects` | Projects | ~11,500 |
| `/api/favorite-domains` | Favorites | 99 |
| `/api/referring-domains/*` | Backlink Analysis | ~575 |

---

## Feature → URL → Database Mapping

| Feature | Frontend URL | API Endpoint | DB Table | Key Fields |
|---------|--------------|--------------|----------|------------|
| Marketplaces | `/inventory` | `/api/domains/list`, `/api/domains/search` | `user_activity_logs` | `url`, `query_params` |
| Domain Details | modal | `/api/tracking/resources-modal-open` | `resources_modal_opens` | `domain`, `type`, `email` |
| Domain Unlock | modal button | `/api/user-unlocks/unlock` | `user_activity_logs` | `url`, `email` |
| Price Finder | `/` | `/api/domains/search` | `user_activity_logs` | `url`, `request_body` |
| CSV Export | button | `/api/domains/download-csv` | `user_activity_logs` | `url`, `email` |
| Google Search | `/google-search` | `/api/google-search/*` | `user_activity_logs` | `url`, `email` |
| Projects | `/projects` | `/api/projects` | `user_activity_logs` | `url`, `email` |
| Backlinks | `/backlinks-checker` | `/api/referring-domains/*` | `user_activity_logs` | `url`, `email` |
