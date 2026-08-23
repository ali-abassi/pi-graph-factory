# Pi Graph Factory

Experimental software-factory workflows built on
[Pi Graph Core](https://github.com/ali-abassi/pi-graph-core).

This repository explores one bounded factory:

```text
plan
  ↓
1–10 isolated implementer lanes (Pi / Claude Code / Codex)
  ↓
integrate
  ↓
tests + screenshots + video evidence
  ↓
independent review
  ↓
repair and recapture, at most five cycles
  ↓
guarded approval or merge
```

It is intentionally experimental. The compiler and contracts work; isolated
Git worktrees, harness output normalization, project-specific browser capture,
lane integration, and automatic merge policy still require hardening before
unattended production use.

## Compile the factory

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/compile_factory.py factory.yaml --out steps.yaml

# Use a pi-graph-core checkout to validate and inspect the result:
/path/to/pi-graph-core/bin/piw validate steps.yaml --strict
/path/to/pi-graph-core/bin/piw graph steps.yaml
```

Edit [`factory.yaml`](factory.yaml) to choose implementer lanes, harnesses,
models, instructions, skills, evidence, review cycles, and merge policy.

## Contract

- At most ten implementer lanes.
- At most five evidence → review → repair cycles.
- Every agent has an explicit harness, model, instructions file, skills, and
  tool allowlist.
- Every review consumes fresh test and visual evidence.
- Merge is conditional on the final typed `pass` verdict and `git diff --check`.
- `merge.apply: false` is the safe default: it emits approval evidence without
  changing the target branch.

## Harnesses

The experimental adapter recognizes:

- `pi`
- `claude-code`
- `codex`

Pi receives explicit `--skill` paths while ambient skill discovery remains
disabled. Claude Code and Codex currently receive the instruction and context
prompt, but their tool events, token usage, cost, and settlement are not yet
normalized into the same receipt. That is a known gap, not a claimed feature.

## Visual proof

The factory does not invent a universal browser command. Projects must produce
the paths declared under `evidence`—normally through Playwright or their native
UI test harness. `capture_evidence.py` runs declared test commands and rejects
missing screenshots, missing video, or failed receipts before review.

The reviewer should receive screenshots, selected video frames, interaction
transcripts, console errors, and the underlying browser receipt. The current
adapter validates file presence and test commands; semantic multimodal review
still depends on the chosen harness and model.

## Important current gaps

1. Implementer worktrees are declared conceptually but not provisioned yet.
2. `integrate.py` combines receipts; it does not yet merge isolated branches.
3. Planner output does not dynamically create lanes; lanes are compiled from
   `factory.yaml` before the run.
4. Repair ownership currently defaults to the first implementer lane.
5. Video duration, frame extraction, and capture provenance are not yet checked.
6. Merge application is available but intentionally disabled in the example.

These are the next engineering targets. Until they are closed, keep
`merge.apply: false` and require a human to execute the approved merge.
