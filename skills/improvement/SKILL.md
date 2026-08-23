---
name: factory-improvement
description: Improve prompts, agents, code, designs, and other artifacts through bounded controller-scored candidate loops.
---

# Measured improvement

Treat “make it better” as an experiment only when a repeatable evaluator can
distinguish plausible candidates. Use a direct fix when the causal defect and
remedy are already known. Never build a search loop for ceremony.

## Authority split

The approved plan freezes the objective, evaluation version, mutable and
forbidden files, metric and minimum gain, development metric command,
preservation gates, one-time promotion commands, candidate and plateau limits,
wall time, and stop conditions.

The factory controller owns the untouched baseline, one fresh detached
worktree per candidate, metric parsing, preservation checks, protected-file
fingerprints, scope checks, keep/discard decisions, incumbent selection,
budgets, the single promotion run, and the final receipt.

The optimizer owns only one candidate mutation and its falsifiable hypothesis.
Never self-report a score, verdict, fingerprint, candidate history, or promotion
claim. Never create commits, edit the contract/evaluator/cases, or run a nested
search. The controller deletes rejected candidate worktrees.

## Candidate discipline

1. Read the current incumbent, complete failures/traces, approved objective,
   and prior controller-recorded history.
2. Separate artifact, evaluator, infrastructure, stochastic, and missing-
   capability failures.
3. State one hypothesis that should generalize beyond known cases.
4. Change one material mechanism inside the mutable scope.
5. Run only cheap local checks useful before controller evaluation.
6. Return the exact controller candidate id, hypothesis, changed files, and
   observed checks.

Reject task-specific benchmark hacks, parser exploits, cached answers, skipped
work, or trades against correctness, safety, accessibility, truth, privacy,
compatibility, and user outcomes. Surprising jumps are a reason to audit the
evaluator, not declare victory.

For ordinary artifacts, the factory provides bounded controller-scored search
but not an OS security boundary or unreadable holdout isolation. Use an external
sandbox when the threat model requires it. For Pi Graph workflow optimization,
use Pi Graph's installed `piw optimize` lifecycle: it adds frozen manifests,
one-mechanism JSON pointers, durable hash-chained evidence, byte-exact rollback,
recovery, and one-use private holdout promotion.

Stop when the controller stops dispatching candidates. “Never stop” is not a
valid policy.
