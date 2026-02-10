# Template Context Variable Reference

> **Auto-generated**: 
> **Repository**: /home/austin/projects/runescape/osrs_hiscore_pull/

This document catalogs all context variables available when writing custom Jinja2 templates for council scaffolding and generation.

---

## 1. CLAUDE.md Context (from `generate_claude_md`)

Used when rendering `CLAUDE.md.j2` templates (the main council coordination document).

### Core Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `atlas` | dict | Atlas agent configuration with defaults applied | `{"name": "atlas", "title": "Coordinator", ...}` |
| `agents` | list[dict] | All agents with defaults applied | `[{agent1}, {agent2}, ...]` |
| `preserved_manual_content` | str | Content between `MANUAL_OVERRIDES` markers | `"<!-- custom content -->"` |
| `timestamp` | str | Generation timestamp in UTC | `"2026-02-02 19:00 UTC"` |
| `key_directories` | list[dict] | Repository key directories | `[{"path": "agents/", "description": "..."}]` |
| `recent_projects` | list[dict] | Recent Scribe projects from database | `[{"name": "...", "last_modified": "...", "entries": 42}]` |
| `repo_root` | str | Absolute path to repository root | `"/home/user/projects/council_mcp"` |

### Atlas Agent Fields

The `atlas` variable is a dictionary containing:

- `name` — str, agent slug (e.g., `"atlas"`)
- `display_name` — str, human-readable name
- `title` — str, role title
- `description` — str, agent description
- `model` — str, LLM model identifier (`"opus"`, `"sonnet"`, `"haiku"`)
- `council_role` — str, governance role (`"coordinator"`, `"specialist"`, `"auditor"`, `"omniscient"`)
- `domains` — list[str], expertise domains
- `identity_prompt` — str, "who you are" prompt section
- `expertise_prompt` — str, "what you're good at" prompt section
- `behavioral_guidelines` — str, "how you should act" prompt section
- `disallowed_tools` — list[str], tools this agent cannot use
- `tools` — list[str], tools explicitly allowed (optional)
- `skills` — list[str], Claude Code skills to enable
- `custom_sections` — list[dict], additional prompt sections with `{"title": "...", "content": "..."}`
- `communication_style` — str, optional communication guidelines
- `tool_guidance` — str, optional tool-specific instructions
- `permission_mode` — str, optional permission mode override
- `color` — str, optional UI color code
- `memory_config` — dict, optional memory settings with `{"visibility": "private"|"council"|"shared", "default_strength": 0.5}`

### Agents List

Each agent in the `agents` list has the same structure as `atlas` above.

### Recent Projects

Each project in `recent_projects` contains:

- `name` — str, project name
- `last_modified` — str, ISO timestamp
- `entries` — int, total log entries
- `status` — str, project lifecycle status (optional)

### Key Directories

Each directory in `key_directories` contains:

- `path` — str, relative directory path
- `description` — str, purpose description

---

## 2. Agent Template Context (from `render_agent`)

Used when rendering `council_member.md.j2` templates (individual agent prompt files).

### Variables

| Variable | Type | Description |
|----------|------|-------------|
| `agent` | dict | Single agent configuration with defaults applied |

### Agent Fields

The `agent` variable contains all fields documented in [Atlas Agent Fields](#atlas-agent-fields) above.

### Common Template Patterns

```jinja2
{# Access agent identity #}
You are **{{ agent.get('display_name', agent.name | title) }}**, {{ agent.title }}.

{# Check optional fields #}
{% if agent.get('communication_style') -%}
{{ agent.communication_style }}
{% else -%}
[default communication style]
{% endif %}

{# Iterate custom sections #}
{%- if agent.get('custom_sections') %}
{% for section in agent.custom_sections %}
## {{ section.title }}
{{ section.content }}
{% endfor %}
{%- endif %}

{# Render tools/skills #}
{% if agent.get('tools') -%}
tools: {{ agent.tools | join(', ') }}
{% endif -%}

{# Memory config #}
{% if agent.get('memory_config') -%}
memory_visibility: {{ agent.memory_config.get('visibility', 'private') }}
{% endif -%}
```

---

## 3. Rule Template Context (from `generate_rules`)

Used when rendering `.claude/rules/*.j2` templates (project-specific rules).

### Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `timestamp` | str | Generation timestamp | `"2026-02-02 19:00 UTC"` |
| `repo_root` | str | Absolute repository root | `"/home/user/projects/council_mcp"` |

### Example Usage

```jinja2
# Generated: {{ timestamp }}
# Repository: {{ repo_root }}

When deploying subagents:
- Repo Root: `{{ repo_root }}`
```

---

## 4. Scaffold Template Context (from `init_cmd.scaffold_council`)

Used when rendering initial `.council/` scaffolding templates.

### Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `council_name` | str | Council name (defaults to repo name) | `"my_council"` |
| `parent_council` | str | Parent council name (optional) | `"main_council"` or empty |
| `minimal` | bool | Minimal roster flag (atlas only) | `true` or `false` |
| `repo_root` | str | Repository root with trailing slash | `"/home/user/projects/council_mcp/"` |

### Templates Using This Context

- `council.yaml.j2` — Council configuration file
- `roster.yaml.j2` — Agent roster definition
- `README.md.j2` — Council documentation

### Example Usage

```jinja2
# {{ council_name }} Council

Repository: {{ repo_root }}

{% if parent_council -%}
Parent Council: {{ parent_council }}
{% endif %}

{% if minimal -%}
This is a minimal council (atlas-only).
{% endif %}
```

---

## Field Type Reference

### Model Values

Valid `model` field values:

- `opus` — Claude Opus (expensive, deep reasoning)
- `sonnet` — Claude Sonnet (balanced)
- `haiku` — Claude Haiku (fast, cheap)

### Council Role Values

Valid `council_role` field values:

- `coordinator` — Orchestration and delegation (e.g., Atlas)
- `specialist` — Domain-specific work (e.g., Forge, Lens, Mantis)
- `auditor` — Quality gates and review (e.g., Arbiter)
- `omniscient` — Unrestricted access (e.g., Carl)

### Memory Visibility Values

Valid `memory_config.visibility` values:

- `private` — Only accessible to this agent
- `council` — Accessible to all council members
- `shared` — Domain knowledge, accessible across councils
- `public` — Publicly accessible

---

## Advanced: Custom Context Variables

To add custom context variables:

1. **Edit generation function** in `src/council_mcp/agents/generate.py`
2. **Add variable to `.render()` call**:
   ```python
   content = template.render(
       # existing vars...
       my_custom_var="value",
   )
   ```
3. **Use in template**: `{{ my_custom_var }}`

---

## Tips for Template Authors

### Safe Field Access

Always use `.get()` for optional fields:

```jinja2
{# Bad - crashes if field missing #}
{{ agent.communication_style }}

{# Good - provides fallback #}
{{ agent.get('communication_style', 'default value') }}
```

### Conditional Blocks

Use `-` to strip whitespace:

```jinja2
{# Adds blank lines #}
{% if condition %}
content
{% endif %}

{# No blank lines #}
{% if condition -%}
content
{% endif %}
```

### List Formatting

```jinja2
{# Join with commas #}
{{ agent.domains | join(', ') }}

{# Join with JSON formatting #}
[{{ agent.skills | map('tojson') | join(', ') }}]
```

### Escaping

```jinja2
{# Escape quotes in strings #}
description: "{{ agent.description | replace('"', '\\"') }}"
```

---

## Related Documentation

- `README.md` — High-level .council/ overview
- `roster.yaml` — Agent schema with inline comments
- `src/council_mcp/agents/generate.py` — Generation implementation
- `src/council_mcp/cli/init_cmd.py` — Scaffolding implementation

---

**Questions?** This reference is generated from source code. If context variables are missing or incorrect, check the `template.render()` calls in the source files listed above.
