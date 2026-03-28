# Phase 4: Automation and Distribution - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Make fnsvr run unattended (launchd scheduling) and installable in one command (PyPI + Homebrew). This is the "install once, forget it exists" phase.

</domain>

<decisions>
## Implementation Decisions

### launchd Scheduling
- Two plists: com.fnsvr.scan.plist (every 4 hours, RunAtLoad) and com.fnsvr.digest.plist (Monday 8am)
- Plists generated dynamically with absolute binary paths (not static templates) -- launchd runs without user's shell PATH
- CLI commands: `fnsvr schedule install` and `fnsvr schedule uninstall` handle launchctl load/unload
- Plists written to ~/Library/LaunchAgents/
- Must detect correct fnsvr executable path at install time (which fnsvr or sys.executable based)
- Logs go to ~/.fnsvr/data/logs/

### PyPI Distribution
- pyproject.toml already configured with entry point fnsvr = "fnsvr.cli:main"
- Package in src/fnsvr/ layout
- config.example.yaml must be included as package data
- Build with setuptools, publish to PyPI

### Homebrew
- Create a Homebrew tap (homebrew-fnsvr) with a formula
- Formula installs via pip into an isolated virtualenv in the Cellar
- User runs `brew tap madho/fnsvr && brew install fnsvr`
- Formula must handle Python dependency isolation

### Claude's Discretion
- launchd plist XML generation details
- Homebrew formula Ruby syntax
- PyPI metadata completeness
- Whether to include a `fnsvr schedule status` command

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- src/fnsvr/cli.py -- Click CLI group to add schedule command
- pyproject.toml -- already configured for packaging
- src/fnsvr/config.py -- get_config_dir() for plist paths

### Integration Points
- schedule commands added to cli.py Click group
- Plists reference the fnsvr executable path

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- infrastructure phase.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
