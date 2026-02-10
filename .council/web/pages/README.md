# Custom Pages

Place custom page templates here as `*.html.j2` files.
They will appear in the "More" navigation dropdown.

## Template Format

Each template should extend `base.html` and can include optional
YAML frontmatter for navigation metadata:

```
---
nav_label: My Custom Page
nav_order: 10
---
{% extends "base.html" %}
{% block title %}My Custom Page{% endblock %}
{% block content %}
<h1>My Custom Page</h1>
{% endblock %}
```

## Frontmatter Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `nav_label` | string | Title-cased filename | Display name in navigation |
| `nav_order` | int | 100 | Sort order (lower = earlier) |

## URL Routing

Pages are served at `/pages/{page_name}` where `page_name`
is the filename without `.html.j2` extension.

Example: `monitoring.html.j2` -> `/pages/monitoring`
