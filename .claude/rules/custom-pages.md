# Custom Pages

**Each council can add custom web pages via `.council/web/pages/` templates, with optional per-council database schemas.**

## Directory Structure

```
.council/
├── web/
│   ├── pages/                      # Jinja2 templates (*.html.j2)
│   │   ├── monitoring.html.j2      # → /pages/monitoring
│   │   ├── docs.html.j2            # → /pages/docs
│   │   └── monitoring/             # Nested sub-pages (one level deep)
│   │       └── alerts.html.j2      # → /pages/monitoring/alerts
│   └── static/                     # Per-council static assets
│       ├── css/                    # → /council-static/css/...
│       ├── js/                     # → /council-static/js/...
│       └── img/                    # → /council-static/img/...
└── db/
    └── migrations/                 # Per-council SQL migrations
        ├── 001_create_status.sql   # → council_<slug>.status_entries
        └── 002_add_index.sql       # Applied via `council db migrate`
```

## Template Format

Templates use Jinja2 with YAML frontmatter for navigation metadata:

```jinja2
---
nav_label: My Page        nav_order: 10             nav_group: Monitoring     nav_group_order: 1        nav_group_icon: monitor   nav_parent: monitoring    sidebar: true             sidebar_items:              - label: Getting Started
    href: "#getting-started"
  - label: API Reference
    href: "#api-reference"
    children:
      - label: Authentication
        href: "#auth"
---
{% extends "base.html" %}

{% block title %}My Page - Council MCP{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="/council-static/css/my-page.css">
{% endblock %}

{% block content %}
<div class="my-page">
    <h1>{{ page_name }}</h1>
    <p>Council: {{ active_council_info.name if active_council_info else 'N/A' }}</p>
</div>
{% endblock %}

{% block extra_js %}
<script src="/council-static/js/my-page.js"></script>
{% endblock %}```

**Key blocks** (from `base.html`):
- `title` — Browser tab title
- `extra_css` — Page-specific stylesheets
- `content` — Main page content
- `extra_js` — Page-specific JavaScript

### Sidebar Pages

Pages with `sidebar: true` can extend `base_sidebar.html` instead of `base.html`:

```jinja2
---
nav_label: Documentation
sidebar: true
sidebar_items:
  - label: Overview
    href: "#overview"
  - label: API
    href: "#api"
---
{% extends "base_sidebar.html" %}

{% block title %}Docs{% endblock %}

{% block page_content %}
<h1 id="overview">Overview</h1>
<p>Content here...</p>
<h1 id="api">API</h1>
<p>API docs...</p>
{% endblock %}```

The sidebar renders automatically from `sidebar_items` frontmatter. Override `sidebar_nav` block for custom sidebar content.

## Template Context

All custom pages receive the standard nav context via `_get_nav_context(request)`:

| Variable | Type | Description |
|----------|------|-------------|
| `request` | Request | FastAPI request object |
| `page_name` | str | Current page name (e.g., "monitoring") |
| `councils` | list[dict] | All councils with `is_active` flag |
| `custom_pages` | list[dict] | All valid custom pages with nav metadata |
| `custom_page_groups` | list[dict] | Pages grouped by `nav_group` for dropdown rendering |
| `custom_page_tree` | list[dict] | Pages in parent-child tree structure |
| `active_council_info` | dict | `{id, name, display_name, repo_path}` of active council |
| `nav_group_label` | str | Dropdown label (smart title-cased council name) |
| `hidden_nav_items` | list[str] | Nav items to hide |
| `has_sidebar` | bool | Whether this page uses sidebar layout |
| `sidebar_items` | list[dict] | Sidebar nav items from frontmatter |

## Nav Label Resolution

The custom pages dropdown label is resolved in priority order:
1. `council.web.nav_group_label` config override
2. `council.display_name` from council.yaml
3. Smart title-case of council name (acronym-aware: "council_mcp" → "Council MCP")
4. "More" (fallback)

Acronyms recognized by `_smart_title_case()` are configurable via `council.web.nav_acronyms`.

## Grouped Navigation

Pages with `nav_group` frontmatter are grouped under labeled sections in the dropdown:

```yaml
---
nav_label: CPU Metrics
nav_group: Monitoring
nav_group_order: 1
---
```

- Groups appear as labeled sections with dividers between them
- Pages without `nav_group` fall into an ungrouped bucket
- Groups sorted by `nav_group_order`, pages within groups by `nav_order`

## Nested Sub-Pages

Sub-pages are created via **directory structure** or **frontmatter**:

**Directory-based** (preferred):
```
.council/web/pages/
├── monitoring.html.j2              # Parent: /pages/monitoring
└── monitoring/
    └── alerts.html.j2              # Child: /pages/monitoring/alerts
```

**Frontmatter-based**:
```yaml
---
nav_label: Alerts
nav_parent: monitoring
---
```

- Only one level deep is supported (security limit)
- Child pages render indented in both desktop and mobile nav
- Path traversal (`..`) is rejected

## Multi-Tab Council Isolation

Each browser tab independently selects a council:

- **sessionStorage** (`activeCouncilId`): Per-tab council selection
- **X-Council-Id header**: Sent on all API requests via `API.getAuthHeaders()`
- **localStorage** (`selectedCouncil`): Cross-tab default for new tabs
- **Cookie** (`active_council_id`): Backward compat for SSR page loads

Resolution order in `_get_active_council_id(request)`:
1. `X-Council-Id` header (per-tab, from sessionStorage)
2. `active_council_id` cookie (backward compat)
3. First registered council (fallback)

## Discovery Pipeline

1. **`ProjectTemplateLoader.discover_pages(repo_path)`** — Scans `.council/web/pages/*.html.j2` + one level of subdirectories
2. **`FrontmatterStrippingLoader`** — Custom Jinja2 loader that strips `---` YAML before rendering
3. **`_parse_frontmatter()`** — Extracts all frontmatter fields (nav, group, sidebar, parent)
4. **`_validate_template_syntax()`** — SandboxedEnvironment syntax check
5. **Max 20 pages** per council (security limit in `MAX_CUSTOM_PAGES`)
6. **30-second TTL cache** — Auto-refreshes, empty directories not cached

## Request Flow

```
GET /pages/{page_name:path}
  → _get_active_council_id(request)     # Header → cookie → first council
  → get_council_by_id_sync(council_id)  # DB: council registry → repo_path
  → template_loader.get_valid_pages()   # Filesystem: discover .html.j2 files
  → project_templates.TemplateResponse  # Render with FrontmatterStrippingLoader

GET /council-static/{file_path}
  → Serves from {repo_path}/.council/web/static/{file_path}
  → Path traversal protection via .resolve() + relative_to()
```

## Navigation Integration

Custom pages appear **automatically** in both desktop and mobile navigation:

- **Desktop**: Dropdown menu with smart title-cased council name (e.g., "Council MCP")
- **Mobile**: Hamburger menu section with council name as subheader
- **Grouped**: Pages with `nav_group` render under labeled sections with dividers
- **Nested**: Child pages render indented under their parent
- **Active state**: Highlighted when `request.url.path == page.path`

## Database Extension System

Each council gets its own **isolated Postgres schema**: `council_<slug>` (e.g., `council_rom_lab`).

### How It Works

1. **Schema isolation**: `sanitize_schema_name(slug)` converts slugs to safe schema names (lowercase, hyphens → underscores, validated against `[a-z0-9_]`)
2. **Migration discovery**: `discover_migrations()` scans `.council/db/migrations/*.sql` sorted by filename
3. **Migration application**: Each SQL file is wrapped with `SET search_path TO <schema>, public` so unqualified table names go to the council's schema
4. **History tracking**: Applied migrations recorded in `<schema>._migration_history` table (filename, checksum, applied_at)
5. **Checksum verification**: Detects if migration files changed after being applied

### CLI Commands

```bash
council db status              # Show pending/applied/mismatch counts
council db status --json       # Machine-readable output
council db migrate             # Apply pending migrations
council db migrate --dry-run   # Preview without applying
```

### Migration File Format

Place SQL files in `.council/db/migrations/` with sequential naming:

```sql
-- .council/db/migrations/001_create_status_entries.sql
CREATE TABLE IF NOT EXISTS status_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unknown',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_status_entries_status ON status_entries(status);
```

No need for `SET search_path` — the migration runner handles that automatically.

### Querying Council Tables

```python
from agentkit.storage.models import db

schema = "council_my_council"  # council_<slug>

with db.connection() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}, public")
        cur.execute("SELECT * FROM status_entries WHERE status = 'active'")
        rows = cur.fetchall()
```

## Config (council.yaml)

```yaml
council:
  display_name: "My Council"       # Override nav label (smart title-case fallback)
  web:
    custom_pages_enabled: true       # Master toggle for page discovery
    hidden_pages: []                 # Page names to exclude from nav (e.g., ["debug"])
    hidden_nav_items: []             # Standard nav items to hide
    nav_group_label: null            # Override dropdown label (default: smart council name)
    custom_static_enabled: true      # Toggle /council-static/ serving
    nav_acronyms:                    # Known acronyms for smart title-casing
      - "MCP"
      - "SDK"
      - "API"
      - "UI"
      # ... (default list includes MCP, SDK, API, UI, CLI, LLM, AI, DB, WS, HTTP, URL, ID)
```

## Key Files

| File | Purpose |
|------|---------|
| `web/template_loader.py` | `ProjectTemplateLoader`, `FrontmatterStrippingLoader`, page discovery |
| `web/routes/pages.py` | `/pages/{name:path}` route, `/council-static/` route |
| `web/shared.py` | `_smart_title_case()`, `_group_custom_pages()`, `_build_page_tree()`, `_get_nav_context()` |
| `web/templates/base.html` | Base template (standard layout) |
| `web/templates/base_sidebar.html` | Base template with sidebar layout |
| `web/templates/partials/_nav_desktop.html` | Desktop nav (grouped dropdown) |
| `web/templates/partials/_nav_mobile.html` | Mobile nav (grouped drawer) |
| `web/static/css/components/_page-sidebar.css` | Sidebar component styles |
| `web/static/css/layout.css` | Group labels, nested item indentation |
| `db/council_migrations.py` | Schema isolation, migration discovery/application |
| `cli/db_cmd.py` | `council db status`, `council db migrate` CLI commands |

## Security

- **SandboxedEnvironment** — Project templates run in Jinja2 sandbox
- **Path traversal protection** — Static file paths resolved and validated; `..` rejected in page routes
- **Max pages limit** — 20 custom pages per council (including nested)
- **One-level nesting limit** — Subdirectory scan is one level deep only
- **Schema isolation** — Each council's DB tables in separate Postgres schema
- **Safe schema names** — Validated against `[a-z0-9_]` pattern
- **Config toggles** — `custom_pages_enabled` and `custom_static_enabled` can disable entirely
- **Per-tab isolation** — X-Council-Id header prevents cross-tab data leakage

## Checklist for Adding a Custom Page

1. Create `.council/web/pages/my-page.html.j2` with frontmatter
2. Add CSS in `.council/web/static/css/my-page.css` (optional)
3. Add JS in `.council/web/static/js/my-page.js` (optional)
4. Add SQL in `.council/db/migrations/001_create_table.sql` (optional)
5. Run `council db migrate` to apply DB schema (if step 4)
6. Wait 30s for cache refresh, or call `POST /api/system/clear-cache`
7. Navigate to `/pages/my-page` — appears in nav automatically