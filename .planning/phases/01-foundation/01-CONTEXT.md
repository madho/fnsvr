# Phase 1: Foundation - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the three core modules (config.py, storage.py, detector.py) with unit tests. These are pure infrastructure -- no Gmail API, no user-facing output. The modules must be fully testable in isolation and ready to receive real email data in Phase 2.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion -- pure infrastructure phase. Follow the TECH_SPEC.md module contracts precisely. Key notes from research:
- Use plain substring matching (case-insensitive `in` operator) rather than re.escape() regex for pattern matching -- simpler, faster, matches config-file users' mental model
- SQLite WAL mode with foreign_keys=ON
- Config validation should fail fast with clear error messages
- detector.py must be pure functions with zero side effects (no I/O, no DB, no filesystem)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Docs/config.example.yaml -- comprehensive reference config with ~70 patterns across 5 categories
- Docs/pyproject.toml -- package configuration ready to use
- Docs/TECH_SPEC.md -- detailed module contracts with function signatures and SQL schema

### Established Patterns
- No existing code yet (greenfield). Patterns established by spec docs.

### Integration Points
- config.py provides config dict consumed by all other modules
- storage.py provides sqlite3.Connection consumed by scanner, digest, reviewer, stats
- detector.py provides CompiledCategory list consumed by scanner

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- infrastructure phase. Follow TECH_SPEC.md contracts.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>
