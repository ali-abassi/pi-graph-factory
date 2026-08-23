# Pi Graph Factory vision

Pi Graph Factory turns an idea, bug report, or change request into a reviewed,
provable, and optionally delivered software change. Agents do the creative
work; deterministic controller code owns order, permissions, state, evidence,
repair limits, and external effects.

## The experience

1. An idea, bug, or request arrives from a person, issue, webhook, or another
   workflow. Broad work chooses either a human-led grill or an autonomous
   self-grill; a specific request may enter directly. Every path produces one
   durable, readiness-classified intake artifact.
2. Autonomous intake resolves evidence-backed and safely reversible choices,
   labels its assumptions, records confidence and overturning evidence, and
   escalates rather than inventing a low-confidence hard-to-reverse decision.
3. The controller prepares repository intelligence. Existing code is indexed or
   refreshed with Graphify; configured semantic extraction enriches repository
   docs and community labels while code retains deterministic AST structure. A
   code-free new project defers its first graph. `VISION.md`, `FEATURE_MAP.md`,
   and any committed domain context supply durable product direction.
4. The planner queries that map, verifies relevant source, researches hidden
   gaps, and resolves uncertainty with defensible assumptions before asking a
   question.
5. A separate model judges grounding, coverage, feasibility, minimality, and
   alignment. Anything below 8.5/10 returns with advice for at most three cycles.
6. The user sees and explicitly approves the exact plan, success criteria,
   ownership, proof mode, and commands.
7. One to ten implementation agents work in isolated Git worktrees. Different
   lanes may use different harnesses, models, instructions, and skills. Product,
   UI design, and copywriting are default specialists; additional specialties
   remain configuration rather than new controller stages.
8. The controller integrates the lanes and runs the approved checks.
9. UI work receives current-commit screenshots, video, and browser evidence.
   Tiny fixes, documentation, refactors, and non-UI work use test evidence
   without ceremonial media.
10. An independent reviewer accounts for every approved outcome. Findings route
   to the exact owner and files. At most five repair cycles may run.
11. A clean review authorizes a guarded merge. When delivery is configured, a
   separate explicit command deploys, checks health, and attempts the configured
   rollback on failure.
12. Every input, output, command, receipt, transition, and artifact remains
   inspectable. Interrupted work resumes from validated checkpoints instead of
   starting the factory again or silently accepting partial state.

## Operating modes

- **Local:** agents run with the invoking account's permissions. This is the
  fast, trusted, subscription-friendly mode and may intentionally be used with
  broad agent permissions.
- **Railway Cloud Agent:** the whole factory runs on a persistent Railway VM so
  it can outlive the laptop, expose a preview URL, and use Codex or Claude Code
  subscriptions. Railway is an execution boundary, not a second workflow
  engine and not a claim of hostile-code sandboxing.
- **Future runner adapters:** disposable or policy-restricted environments may
  wrap the same frozen run contract without changing factory semantics.

## Product principles

- The model never owns control flow or merge authority.
- Approval binds exact bytes, not a conversational summary.
- Git and executed commands outrank agent claims.
- Repository maps reduce context use but never replace source verification.
- Project vision and the feature map are durable decision context, not hidden
  permission to expand an approved request.
- An independent anchored judgment improves plans; exact user approval remains
  the authority for what gets built.
- Evidence is proportional to the change and bound to the reviewed commit.
- Usage is always observed; subscription users are not blocked by arbitrary
  token or dollar ceilings unless they explicitly configure enforcement.
- Timeouts are configurable by role and may be disabled. A timeout is an
  operational policy, not a definition of task failure.
- Recovery validates and continues known checkpoints. Ambiguous repository
  mutations stop for inspection rather than being erased or guessed through.
- Deployment is an explicit external effect with health evidence and an
  operator-provided rollback contract.
- Simplicity wins: one controller, one run ledger, one review loop, one merge
  path, and adapters at the edges.
- Interactive and autonomous intake are different resolution policies, not
  separate downstream factories; both hand the planner the same durable brief.
- Ponytail is a cross-cutting implementation and review discipline, not another
  agent or gate: understand the flow, reuse/delete/native first, and add only the
  smallest code that preserves safety, accessibility, and proof.
- TDD and defect diagnosis are conditional implementation disciplines, not new
  workflow stages: use a real public seam for executable behavior and skip
  ceremony where no honest executable seam exists.
- Durable prose preserves facts, qualifiers, technical terms, and the author's
  voice while cutting formulaic filler. Style cleanup never invents evidence or
  becomes another workflow gate.
- Copywriting is distinct production work. Material messaging starts from a
  reader/channel contract, verified claims, an honest mechanism, and a desired
  response; it is implemented by the owner of the affected files and reviewed
  independently. External publication remains an explicit effect.

## Not the product

- Mandatory screenshots or video for every change.
- A token-reselling layer or default subscription usage limiter.
- An autonomous conflict resolver that crosses approved ownership boundaries.
- A hidden queue, second state machine, or provider-specific workflow fork.
- A promise that screenshots alone prove quality or that every deploy is safe.

## Current quality bar

The core is ready to be used publicly when deterministic tests, both Pi Graph
validators, supported Python/OS CI, security scans, and representative live
runs pass. Complex live runs are improved one inspected input/output at a time;
safe refusal is evidence, but it is not counted as successful delivery.
