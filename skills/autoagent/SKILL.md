---
name: autoagent-patterns
description: Apply AutoAgent-style trajectory diagnosis and keep-or-discard harness experiments under the factory improvement contract.
---

# AutoAgent patterns

This is a reference layer, not a second controller. Obey the configured
`factory-improvement` skill and the approved optimization contract. Propose one
candidate per dispatch; the factory controller runs and records the loop.

Useful patterns from `thirdlayerinc/autoagent`:

- let the controller measure the untouched harness before editing;
- diagnose task trajectories and verifier output, not only aggregate score;
- group failures by general root cause;
- change one prompt, tool, configuration, or orchestration mechanism at a time;
- prefer passed tasks, then simpler structure as a tie-break;
- use controller history to learn from both kept and discarded experiments;
- reject task-specific benchmark hacks;
- verify what the agent produced, not what it intended.

The public repository currently has no committed license file even though its
README says MIT. Use these high-level ideas only; do not copy its code. Its
unbounded “NEVER STOP” instruction is intentionally replaced by controller-
enforced candidate, plateau, and wall-time limits, isolated candidate
worktrees, one-time promotion, and independent review.
