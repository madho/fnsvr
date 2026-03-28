# Phase 5: Landing Page - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a single self-contained index.html file for fnsvr.com. Terminal-native editorial minimalist aesthetic. Under 30KB. No JS frameworks, no analytics, no tracking.

</domain>

<decisions>
## Implementation Decisions

### Design Direction
- Dark background (terminal lives here)
- Monospace for code and product name
- Clean sharp serif or geometric sans for body text (use system fonts to avoid external requests)
- Warm amber/orange accent for detection categories -- signals "attention, not alarm"
- Off-white or warm gray text, not pure white
- Single column, vertically stacked, generous whitespace
- Minimal motion (subtle fade-in on scroll at most)
- No illustrations, no icons, no stock photos

### Page Structure (in order)
1. **Hero** -- headline naming the problem, subhead describing what fnsvr is, CTA to GitHub
2. **The Problem** -- 2-3 sentences about buried financial emails across multiple inboxes
3. **What fnsvr Does** -- 5-item feature grid (tax docs, signatures, equity, brokerage, bank/wires)
4. **How It Works** -- 3 steps: Install, Scan, Review
5. **Design Principles** -- 4 trust-building statements (local-first, read-only, config-driven, open source)
6. **Quick Start** -- terminal code block with install commands
7. **Footer** -- GitHub link, MIT License, "Built by madho", no newsletter/email capture

### Voice and Tone
- Direct, confident, no fluff
- Talks to reader like a peer, not a customer
- No "supercharge", no "powered by AI", no "never miss another email"
- Plain statements of fact about what the tool does and doesn't do

### Technical
- Single HTML file with inline CSS
- Vanilla JS only (typing effect for terminal block at most)
- No analytics, no tracking, no cookies
- Load in under 1 second on any connection
- Under 30KB total
- Deployable to GitHub Pages or Vercel as-is

### Reference Aesthetic
- httpie.io (developer tool, clean, confident)
- charm.sh (terminal aesthetics elevated)
- Linear's early site (restrained, fast, opinionated)

### What to Avoid
- Fintech blue, purple gradients
- Dashboard preview mockups
- Testimonial carousels, pricing tables, "Trusted by" logos
- Cookie banners (there are no cookies)
- Any JS framework heavier than vanilla

### Claude's Discretion
- Exact headline copy (within the "names the problem" constraint)
- CSS animation details
- Color hex values (within dark/amber/warm-gray direction)
- Font stack specifics (system fonts, monospace for code)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Docs/config.example.yaml -- detection category names and patterns for the feature grid
- Docs/VISION.md -- design principles text
- Docs/README.md -- quick start commands

### Integration Points
- index.html is standalone, no dependencies on any src/ code

</code_context>

<specifics>
## Specific Ideas

The user provided a detailed website spec with:
- Composite persona description (3 real people)
- Specific headline directions: "Your K1 is buried in your third inbox. fnsvr finds it."
- Specific voice guidance: "let the reader decide if it's for them. They will."
- Reference to httpie.io, charm.sh, early Linear aesthetic

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
