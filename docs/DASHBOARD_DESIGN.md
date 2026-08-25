# Factory dashboard interface contract

Project: Pi Graph Factory local operations dashboard
Artifact/register: product UI; local desktop browser operator surface
Audience and usage context: A solo developer supervising autonomous software-factory runs on their own machine, usually while one run is active or immediately after a failure.
Design argument / generative thesis / taste read: For a developer supervising autonomous work, this dashboard is a quiet Scandinavian workshop ledger: current state is calm and spacious enough to scan, agent activity becomes a contribution-style temporal field, and the complete trace stays one action away. It answers “what is happening, who is active, what is blocked, what did it consume, and where is the proof?” without translating a terminal aesthetic into the browser. It prioritizes trustworthy operational density over decorative analytics.
Approved references + qualities to borrow: `./VISION.md` for the local-ledger boundary; `./FEATURE_MAP.md` for the durable backend contract; `./README.md` for inspect semantics; `./scripts/factory.py` for canonical state, events, usage, agents, lanes, and artifact paths; `/Users/aliabassi/.pi-x/agent/TASTE.md` for the explicit Scandinavian dashboard override and agent-by-time heatmap. Use exact factory vocabulary, a neutral white foundation, readable sentence-case sans-serif hierarchy, useful whitespace, and contribution-map temporal scanning.
Anti-references + failures to avoid: `/Users/aliabassi/Desktop/Taste Library/rejected/pi-graph-factory-terminal-newsprint-dashboard.png` is the rejected v1 artifact: tiny uppercase mono labels, warm beige/rust styling, dense rules, and a generic bar plot made the browser dashboard feel ugly and terminal-newsprint-like. Also avoid generic SaaS admin templates, vanity KPI grids, chat framing, fake live status, hidden or truncated failures, ornamental dots, nested cards, gradients, glass, and a second telemetry database.
Source list / artifact manifest: `./VISION.md`, `./FEATURE_MAP.md`, `./README.md`, `./scripts/factory.py`, `./docs/DASHBOARD_DESIGN.md`, `./evidence/dashboard/`, `/Users/aliabassi/.pi-x/agent/TASTE.md`, `/Users/aliabassi/Desktop/Taste Library/rejected/pi-graph-factory-terminal-newsprint-dashboard.png`
Direction decision (use / avoid / prove): use: neutral white chrome, one readable system sans, sentence-case labels, generous but operational spacing, few earned boundaries, semantic state color, a compact run rail, one evidence workspace, native HTML controls, and a GitHub-style agent-by-time activity heatmap switchable between hour and day; avoid: terminal/newsprint styling, beige or tinted gray chrome, rust editorial accents, tiny uppercase metadata, divider grids, KPI-card wallpaper, icon-only controls, decorative motion, silent truncation, and invented data; prove: a user can identify the active or failed run, compare every agent's hour/day activity, read blockers, inspect the full event trace, switch runs, and recover from stale artifacts at both viewports with keyboard alone.
Fixed constraints: Localhost only; read-only; run directories remain authoritative; Python standard library and browser-native HTML/CSS/JavaScript; no account, cloud service, database, bundler, framework, or provider API; paths must never be served outside explicitly supplied roots.
Non-goals: Triggering, resuming, repairing, approving, merging, or deploying runs; editing state; hosted access; authentication; team collaboration; cross-machine sync; exact provider billing when receipts report unknown usage.
Shared type / spacing / color / shape / imagery / motion rules: One platform system sans at 16px body size; 500–600 headings; mono only for IDs, commands, paths, timestamps, and exact metrics; 4/8/16/24/32/48 spacing rhythm; white canvas and alpha-black neutral hierarchy; neutral chart chrome with one restrained forest-green intensity scale for activity, red blocker, green pass, amber unknown, and blue focus; borders only where proximity cannot carry grouping; consistent 8-pixel radius; no imagery or shadow; only short opacity/color feedback and none under reduced motion.
Shared interaction and feedback rules: Every control has visible hover, active, focus-visible, disabled, loading, success, and error treatment where applicable; selection is encoded by text, border, and color; refresh preserves selection when possible and reports its timestamp; run and artifact links are keyboard reachable; long logs and errors wrap or scroll without losing content; server errors explain recovery.
Default viewport: 1440 by 900 CSS pixels
Minimum viewport: 768 by 600 CSS pixels
Handoff path: `./docs/DASHBOARD_DESIGN.md`
Evidence directory: `./evidence/dashboard/`
Locked checks version / date: dashboard-v2 / 2026-08-25
Required reviewer assignments: Independent browser QA agent for the operations surface; root agent as final approver after deterministic and rendered checks.

## Direction selection

Three structural theses were considered before implementation:

1. Timeline-first flight recorder: strongest audit trail, but weak for switching among projects and runs.
2. Status-first control room: fastest health scan, but easily decays into shallow KPI cards.
3. Project ledger: a compact project/run rail controls one evidence workspace, with current status followed by the chronological trace.
4. Scandinavian activity ledger: preserve the project ledger's truthful structure, remove the terminal/newsprint expression, and make an agent-by-time contribution map the dominant operational visual.

The Scandinavian activity-ledger thesis is selected after Ali explicitly rejected the rendered project-ledger expression as ugly and requested a simple Scandinavian design plus GitHub-style activity by hour/day. It preserves the truthful run rail and evidence hierarchy, but replaces the bar-chart/terminal-newsprint presentation with neutral white chapters and an agent-by-time intensity map. It still sacrifices simultaneous side-by-side run comparison; that is not required for this local surface.

## Surface: Operations ledger at `/`

- **Register and usage moment:** Dense, calm, local engineering workbench opened during a run, after a blocker, or when auditing a completed run.
- **Primary user job:** Select any discovered run and determine its current state, latest meaningful activity, blocker, usage, and evidence trail.
- **Observable successful outcome:** Within one first paint and one selection action, the user can name the selected project/run and phase, locate any blocker, read token totals and hourly distribution, inspect events, and reach the underlying artifacts.
- **Entry / exit:** Enter by launching the localhost server with one or more allowed roots; exit by closing the browser or stopping the server. Selecting a run changes the URL hash so refresh restores context.
- **Critical information, ordered:** Data freshness and discovery errors; projects and runs; selected run phase and operation; blockers and active agents; agent-by-time activity heatmap with exact token totals and uncertainty; implementation lanes; chronological events; plans, contexts, receipts, logs, evidence, and intelligence artifacts.
- **Primary actions:** Select a project/run; refresh from disk; filter the event timeline; expand complete event data; open a permitted text or media artifact.
- **Secondary actions:** Copy a run path or next command; collapse artifact groups; follow keyboard focus through the ledger.
- **Composition and hierarchy:** A quiet white top bar and narrow neutral run rail establish place without terminal chrome. The main workspace starts with selected-run identity and refresh status, then a restrained fact row and blocker region. A large contribution-style activity chapter maps agent rows against hour/day columns, with exact totals and uncertainty adjacent; execution lanes remain a smaller peer. Events and artifacts follow as spacious chapters with far fewer visible rules. At minimum width the rail stacks above the workspace and the heatmap scrolls inside its labeled region without page overflow.
- **Interaction and feedback rules:** Native buttons, links, search, disclosure, and progress semantics; selected run is announced and reflected in the hash; refresh uses `aria-busy`; filters update a visible count; artifact fetch failures render inline with the failed path and recovery advice; no destructive actions exist.
- **Normal state:** Fixture with three projects, one active implementing run, one repaired/reviewing run, and completed runs; selected active run has two lanes, recent events, known usage, and artifacts.
- **Empty state:** Allowed root contains no `.factory/runs/*/state.json`; the surface explains where it looked and provides the exact launch pattern needed to add a root.
- **Long / maximum-content state:** Fixture includes long project and run names, ten lanes, multiple blockers, 120 events with large payloads, unknown usage calls, and many artifact paths; all content remains inspectable.
- **Loading state:** Stable application shell with an explicit “Reading local ledgers…” status and busy semantics while the JSON endpoint responds.
- **Error / degraded / disabled state:** Malformed or unreadable state/event files remain represented as degraded runs with exact safe error text; absent optional artifacts show as missing; refresh and selection remain usable; artifact opening is disabled for paths outside allowed roots.
- **Default viewport:** 1440 by 900 CSS pixels in a real Chromium browser window.
- **Minimum viewport:** 768 by 600 CSS pixels in a real Chromium browser window with browser zoom at 100 percent.
- **Representative content:** `monster-truck-ios-production-v2-with-a-deliberately-long-run-identifier`, phase `reviewing`, operation `repair: design`, owners `design`, `implementation-01` through `implementation-08`, `qa`, blockers describing stale simulator proof and an acceptance-test failure, 1,284,391 total tokens, unknown subscription usage, full paths, receipts, screenshot, video, and 120 timestamped events.
- **Surface-specific anti-slop risks:** A top row of four interchangeable metric cards; oversized “Factory” branding; a decorative chart that hides exact totals; colored dots without words; arbitrary purple gradients; every section boxed twice; fake terminal copy; hiding paths or failures behind ellipses.
- **Acceptance checks:**
  - `OPS-C1` — A user can select a run and see its exact project, run ID, phase, operation, blockers, active agents, lanes, and next command without reading raw state JSON | normal active-run fixture | default and minimum | screenshots plus browser interaction receipt
  - `OPS-C2` — A contribution-style map shows every agent role against hour or day buckets with intensity based on observed tokens, exact aggregate usage remains visible, unknown usage is disclosed, and no cost is invented | normal and long fixtures | default and minimum | screenshots, hour/day interaction receipt, and API assertions
  - `OPS-C3` — Filtering and expanding the event ledger exposes complete event payloads, and permitted artifacts can be opened while out-of-root paths are refused | long and degraded fixtures | default and minimum | interaction recording or before/after screenshots plus HTTP tests
  - `OPS-C4` — Empty, malformed, loading, missing-artifact, and server-error states remain truthful, actionable, keyboard reachable, and free of page-level horizontal overflow | empty and degraded fixtures | default and minimum | screenshots plus accessibility and layout assertions
- **Explicit failure conditions:**
  1. The UI claims a run is live, passed, merged, or blocked without support from its ledger.
  2. Any state, event, artifact, or filesystem path outside an explicitly allowed root can be modified or served.
  3. A blocker, error, event payload, path, or usage uncertainty is silently truncated, hidden, or converted into an invented metric.
- **Evidence:**
  - normal @ default: `evidence/dashboard/scandinavian-default.png`
  - long/maximum @ default: `evidence/dashboard/long-default.png`
  - empty/degraded @ default: `evidence/dashboard/empty-default.png`, `evidence/dashboard/degraded-default.png`, `evidence/dashboard/loading-default.png`, `evidence/dashboard/missing-artifact-default.png`, `evidence/dashboard/server-error-default.png`
  - normal @ minimum: `evidence/dashboard/scandinavian-minimum.png`
  - adverse states @ minimum: `evidence/dashboard/empty-minimum.png`, `evidence/dashboard/degraded-minimum.png`, `evidence/dashboard/loading-minimum.png`, `evidence/dashboard/missing-artifact-minimum.png`, `evidence/dashboard/server-error-minimum.png`
  - interaction before/after or recording: `evidence/dashboard/activity-interaction.json`, `evidence/dashboard/keyboard-interaction.json`
- **Floor F1–F12:**
  - F1 — PASS — No document-level overflow at either locked viewport; the run rail and activity map scroll internally and preserve focused controls, proven by `evidence/dashboard/keyboard-interaction.json`.
  - F2 — PASS — The Scandinavian operations-ledger hierarchy is coherent in `evidence/dashboard/scandinavian-default.png` and `evidence/dashboard/scandinavian-minimum.png`.
  - F3 — PASS — Run, blocker, activity, usage, event, and artifact content remains legible in `evidence/dashboard/scandinavian-default.png` and `evidence/dashboard/long-default.png`.
  - F4 — PASS — Every activity cell has a unique full UTC accessible name and visible focus treatment, proven by `evidence/dashboard/keyboard-interaction.json`.
  - F5 — PASS — Complete keyboard operation uses one roving activity-map tab stop with arrow navigation and exits directly to the event filter, proven by `evidence/dashboard/keyboard-interaction.json`.
  - F6 — PASS — Long identifiers and payloads wrap at 768 by 600 in `evidence/dashboard/long-minimum.png`.
  - F7 — PASS — Empty and degraded states preserve context and recovery in `evidence/dashboard/empty-default.png` and `evidence/dashboard/degraded-default.png`.
  - F8 — PASS — Loading, missing-artifact, and server-error states are distinct, truthful, and recoverable in `evidence/dashboard/loading-default.png`, `evidence/dashboard/missing-artifact-default.png`, and `evidence/dashboard/server-error-default.png`.
  - F9 — PASS — Usage is labeled observed and unknown cost is not invented in `evidence/dashboard/scandinavian-default.png`.
  - F10 — PASS — Receipt identity, artifacts, events, and controller state remain inspectable in `evidence/dashboard/long-default.png`.
  - F11 — PASS — Reduced-motion verification reports zero-second transitions in `evidence/dashboard/review.md`.
  - F12 — PASS — The surface remains read-only, localhost-bound, and path-confined as proven by dashboard HTTP tests and `evidence/dashboard/review.md`.
- **Locked-check results:**
  - OPS-C1 — PASS — Run selection, exact operational state, selection persistence, and minimum-width focus scrolling are proven by `evidence/dashboard/interaction-after.png` and `evidence/dashboard/keyboard-interaction.json`.
  - OPS-C2 — PASS — Every agent, hour/day switch, exact observed usage, uncertainty, and roving interaction is proven by `evidence/dashboard/activity-interaction.json`, `evidence/dashboard/keyboard-interaction.json`, and the normal/maximum screenshots.
  - OPS-C3 — PASS — Complete event filtering/expansion and guarded artifact access are proven by the maximum screenshots, HTTP tests, and `evidence/dashboard/review.md`.
  - OPS-C4 — PASS — Empty, malformed, loading, missing-artifact, and server-error states pass at both viewports in `evidence/dashboard/empty-default.png`, `evidence/dashboard/degraded-minimum.png`, `evidence/dashboard/loading-default.png`, `evidence/dashboard/missing-artifact-minimum.png`, and `evidence/dashboard/server-error-default.png`.
- **Independent reviewer:** `/root/dashboard_ui_reviewer`; final record at `evidence/dashboard/review.md`
- **Verdict:** Pass

## Completion packet

- Final surface inventory: One responsive local operations-ledger surface at `/` with an artifact viewer endpoint.
- Reviewer verdicts: Independent browser QA PASS with OPS-C1–C4 and F1–F12 all passing at `evidence/dashboard/review.md`.
- Unresolved unknowns / risks: none
- Check-change log: OPS-C2 v1 generic hour/day aggregate plot → OPS-C2 v2 agent-by-time contribution map with unchanged exactness and uncertainty requirements → Ali explicitly rejected the v1 rendered direction and requested simple Scandinavian design plus GitHub-like activity by hour/day → authorized by Ali on 2026-08-25 → replacement evidence will be captured in `evidence/dashboard/scandinavian-default.png`, `evidence/dashboard/scandinavian-minimum.png`, and `evidence/dashboard/activity-interaction.json`.
- Final decision: Pass
