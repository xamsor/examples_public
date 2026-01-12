# Filters UI Design Session - 2026-01-12

## Overview

Redesigning the Marketplaces filter UI for FatGrid based on actual usage data analysis.

## Files Created

- `filters_mockup.html` - First version (violet palette, rejected)
- `filters_v2.html` - Second version (Ahrefs-inspired blue palette)
- `filters_v3.html` - Third version (current, with design improvements)

## Key Design Decisions

### Filter Priority (based on 90-day usage data)

**Popular Filters** (10 most used by paid users):
1. Price ($) - min/max inputs
2. Organic Traffic - min/max inputs
3. DR - min/max inputs
4. AS - min/max inputs
5. Link Follow - 3-position tags (dofollow/nofollow/any)
6. Keyword - text search
7. Category - multi-select dropdown
8. Languages - multi-select dropdown
9. Top Country - multi-select dropdown
10. Niches (Restricted) - multi-select dropdown

**Other Filters** (grouped by meaning):
- Traffic Metrics (sky border): Min Monthly Organic, All Channels, Country Traffic
- Link Attributes (indigo border): Sponsored, Ref Domains
- Marketplace (amber border): Sellers, Added Date, Verified
- My Data (emerald border): Favorites, Blacklist, Tags, Notes

### Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ POPULAR FILTERS ▲                                                   │
│ ┌─────────┬───────────────┬────────┬───────────┬──────────────────┐│
│ │ Price   │ Organic       │ DR     │ Link      │ Keyword          ││
│ │ Min-Max │ Traffic       │ 0-100  │ Follow    │ e.g. finance     ││
│ │         │ Min-Max       │ AS     │ do/no/any │                  ││
│ │         │               │ 0-100  │           │                  ││
│ └─────────┴───────────────┴────────┴───────────┴──────────────────┘│
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐      │
│ │ Category     │ Languages    │ Top Country  │ Niches       │      │
│ └──────────────┴──────────────┴──────────────┴──────────────┘      │
├─────────────────────────────────────────────────────────────────────┤
│ OTHER FILTERS ▼ (collapsed by default)                              │
│ ┌─────────────┬─────────────┬─────────────┬─────────────┐          │
│ │ Traffic     │ Link        │ Marketplace │ My Data     │          │
│ │ Metrics     │ Attributes  │             │             │          │
│ │ (sky)       │ (indigo)    │ (amber)     │ (emerald)   │          │
│ └─────────────┴─────────────┴─────────────┴─────────────┘          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 12,847 publishers found  [chips...] Clear Filters                   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ ☐ [Search by domain] [All | Guest Post | Link Insertion]            │
├─────────────────────────────────────────────────────────────────────┤
│ TABLE...                                                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Color Palette (Ahrefs-inspired)

- **Brand blue**: #1d4ed8 (brand-600)
- **Accent orange**: #f59e0b (accent-500)
- **Active filter tint**: bg-brand-50 + border-brand-300

### Active Filter States

- **Active filters** show blue tint (bg-brand-50) with blue border (border-brand-300)
- **Active filter chips** have white bg with slate border, label in gray, value in dark

### Component Specifications

**Input heights:**
- Popular Filters: h-9 (36px)
- Other Filters: h-8 (32px)
- DR/AS stacked: h-7 (28px) each

**3-position tags (yes/no/any):**
- Used for: Link Follow, Sponsored, Verified, Favorites, Blacklist, Notes
- Active state: bg-brand-600, white text

**Multi-select dropdowns:**
- Include search input
- Checkboxes for multi-select
- Show "+N" for additional selections

### Type Toggle

- Stays in table header (user requirement)
- Options: All | Guest Post | Link Insertion
- Important for SEO workflow

## Pending Improvements

1. DR & AS could be stacked vertically to save horizontal space (values max 100)
2. Consider responsive breakpoints for tablet/mobile
3. Counter animation when filter changes

## Data Sources

See `usage_research.md` for filter usage statistics by user tier.
See `code_samples.md` for database queries.
