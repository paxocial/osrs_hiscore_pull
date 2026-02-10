# Template Customization

**The Council template system allows full customization without editing package code.**

## Quick Start

1. **Add a custom agent**: Edit `.council/roster.yaml`, run `council update`
2. **Preview changes**: Always use `council update --dry-run` before committing
3. **Override templates**: Place same-named file in `.council/templates/` to override package defaults

## Adding Custom Agents

Edit `.council/roster.yaml`:

```yaml
agents:
  - slug: myagent
    name: MyAgent
    role: specialist      # specialist|auditor|omniscient
    model: sonnet         # haiku|sonnet|opus|openai
    title: My Agent Title
    description: What this agent does
    domains: custom,testing,analysis
    expertise: |
      You excel at:
      - Thing one
      - Thing two
    behavioral_guidelines: |
      - Always do X
      - Never do Y
```

**Required fields**: `slug`, `name`, `role`, `model`, `title`, `description`, `domains`

**Valid enums**:
- `role`: `specialist`, `auditor`, `omniscient`
- `model`: `haiku`, `sonnet`, `opus`, `openai`

Run `council update` to regenerate agent cards and CLAUDE.md.

## Template Overrides

Override any package template by creating the same-named file in `.council/templates/`:

```
.council/templates/
├── claude/
│   ├── CLAUDE.md.j2           # Override main CLAUDE.md
│   ├── agent/
│   │   └── council_member.md.j2   # Override agent cards
│   └── rules/
│       └── _rule_session.j2       # Override session rule
└── scaffold/
    └── README.md.j2           # Override README scaffold
```

The template engine uses a **multi-path loader** that checks `.council/templates/` first, then falls back to package defaults.

## Include/Partial Overrides

Override individual sections by creating custom partials:

```
.council/templates/claude/includes/_council_tools.j2
```

This lets you customize just the Council Tools section without replacing the entire CLAUDE.md template.

## Custom Sections (Per-Agent Content)

Inject custom content into specific agents using `custom_sections` in roster.yaml:

```yaml
agents:
  - slug: atlas
    # ... other fields ...
    custom_sections:
      additional_expertise: |
        ## Custom Expertise
        - Advanced pattern X
        - Special workflow Y
```

The custom sections appear in the generated agent card after the standard sections.

## Template Variables

All templates have access to these context variables:

**CLAUDE.md context**:
- `{{ repo_root }}` — Repository root path
- `{{ agents }}` — List of all agents
- `{{ recent_projects }}` — Recent Scribe projects
- `{{ key_directories }}` — Key repo directories
- `{{ rules }}` — Rule file list

**Agent card context**:
- `{{ agent.slug }}`, `{{ agent.name }}`, `{{ agent.title }}`
- `{{ agent.role }}`, `{{ agent.model }}`, `{{ agent.domains }}`
- `{{ agent.description }}`, `{{ agent.expertise }}`
- `{{ agent.behavioral_guidelines }}`
- `{{ agent.custom_sections }}` — Dict of custom content

**Rule context**:
- `{{ repo_root }}` — Repository root path

**Scaffold context**:
- `{{ repo_root }}` — Repository root path
- Various scaffold-specific variables

**IMPORTANT**: Always use `{{ repo_root }}` instead of hardcoding paths. This ensures templates work across different repositories.
## Validation

The system validates roster.yaml before generation:

```bash
council update --dry-run
```

**Common validation errors**:
- Missing required fields (`name`, `domains`, `model`, `role`)
- Duplicate agent slugs
- Invalid enum values (model/role)
- Empty required fields

Fix validation errors before running `council update`.

## Documentation Reference

Generated documentation is scaffolded into `.council/` on `council init`:

- `.council/README.md` — Explains .council/ purpose, directory structure, customization workflow
- `.council/TEMPLATE_REFERENCE.md` — Complete template variable catalog with types and examples
- `.council/roster.yaml` — Schema reference with inline comments

## Manual Overrides in CLAUDE.md

CLAUDE.md supports manual overrides that survive regeneration:

```markdown
<!-- MANUAL_OVERRIDES_START -->
Your custom content here
<!-- MANUAL_OVERRIDES_END -->
```

Content between these markers is preserved when regenerating CLAUDE.md.

## Best Practices

1. **Always preview**: Use `--dry-run` to see what will change before applying
2. **Validate early**: `council update --dry-run` catches errors before they break generation
3. **Use variables**: Reference `/home/austin/projects/runescape/osrs_hiscore_pull` instead of hardcoding paths
4. **Override minimally**: Only override the specific templates/sections you need to change
5. **Document custom agents**: Add clear descriptions and behavioral guidelines
6. **Test after changes**: Run `pytest tests/test_council_update.py -v` after roster changes

## Example Workflow

```bash
# 1. Edit roster
vim .council/roster.yaml

# 2. Preview changes
council update --dry-run

# 3. Review the diff output
# (Shows what files will change with unified diff format)

# 4. Apply if looks good
council update

# 5. Verify tests still pass
pytest tests/test_council_update.py -v
```