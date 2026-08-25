# pstack source review

Pi Graph Factory reviewed Cursor's MIT-licensed `pstack` plugin at commit
`46125561306434d8a1d7745d540d8932ab0cd2a2`. The review used source files, not
only the README. These are placement decisions, not a vendored dependency.

## Adopt now

| pstack mechanic | Factory adaptation |
| --- | --- |
| Experience first | New product and UI planning now optimizes for one polished core loop instead of maximizing feature count. The visual contract makes audience, screens, states, art direction, and observable quality explicit. |
| Exhaust the design space | A new product or major redesign records at least two genuinely distinct directions and why one won. Incremental work may follow the established system without prototype ceremony. |
| Blast radius | Planner and reviewer must identify the cross-component fact a risky change depends on and push it toward executable proof. An unproved safety assumption stays named rather than becoming confident prose. |
| Create a verification skill | The QA owner can add the smallest project-local launch/doctor/drive/evidence/cleanup harness when the changed surface lacks one. It depends on the production owner, must be executed once after integration, and must validate artifact semantics. |
| Show me your work | The factory already preserves append-only events, contexts, commands, receipts, raw streams, native transcripts, and artifacts. The local operations surface will present decision-grade checkpoints from that canonical ledger instead of introducing a second TSV source of truth. |

## Bank for a later measured experiment

| pstack mechanic | Decision |
| --- | --- |
| Multi-model `interrogate` | Test a risk-triggered review panel against the human-rated plan/review corpus. Do not multiply reviewers by default until independent findings measurably improve defect detection enough to justify latency and context. |
| `reflect` over transcripts | Add a post-run improvement-proposal view after the operations UI can expose exact evidence. Suggestions may propose a gate, skill, or prompt change, but cannot rewrite shared skills automatically. |
| Architecture arena | Use competing shapes for genuinely consequential, unsettled boundaries. The current deep-thinking and decision contracts capture alternatives; a separate pre-implementation arena needs evidence that it improves outcomes without duplicating the plan judge. |
| Verification-map maintenance | Revisit when target repositories consistently carry project-local verification maps. Until then, ordinary factory requests update `FEATURE_MAP.md` and the touched driver together. |

## Do not import

- `poteto-mode` is a useful interactive router, but the factory already has one
  deterministic controller and typed phase contracts. A second sticky mode would
  split lifecycle authority.
- PR, Graphite, babysitting, and merge-when-ready playbooks conflict with this
  repository's direct-main maintenance policy and remain target-specific delivery
  adapters.
- Unbounded “push past every plateau” behavior conflicts with the factory's
  frozen candidate, plateau, wall-time, and stop contracts.
- Worktree, resume, pause, and concurrency playbooks are weaker duplicates of the
  controller's isolated ownership, checkpoint validation, process identity, and
  recovery rules.

## Source files inspected

- `skills/principle-experience-first/SKILL.md`
- `skills/principle-exhaust-the-design-space/SKILL.md`
- `skills/blast-radius/SKILL.md`
- `skills/create-verification-skill/SKILL.md`
- `skills/maintain-verification-skill/SKILL.md`
- `skills/show-me-your-work/SKILL.md`
- `skills/architect/SKILL.md`
- `skills/interrogate/SKILL.md`
- `skills/figure-it-out/SKILL.md`
- `skills/reflect/SKILL.md`
- the feature, prototype, visual-parity, autonomous-run, hillclimb,
  session-pickup, and pause-safely playbooks

Source: <https://github.com/cursor/plugins/tree/46125561306434d8a1d7745d540d8932ab0cd2a2/pstack>
