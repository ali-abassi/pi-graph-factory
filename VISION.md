# Pi Graph Factory vision

Pi Graph Factory turns an idea, bug report, or change request into a reviewed,
provable, and optionally delivered software change. Agents do the creative
work; deterministic controller code owns order, permissions, state, evidence,
repair limits, and external effects.

## The experience

1. A request arrives from a person, issue, webhook, or another workflow.
2. The planner inspects the repository and asks only questions that materially
   change the result.
3. The user sees and explicitly approves the exact plan, success criteria,
   ownership, proof mode, and commands.
4. One to ten implementation agents work in isolated Git worktrees. Different
   lanes may use different harnesses, models, instructions, and skills.
5. The controller integrates the lanes and runs the approved checks.
6. UI work receives current-commit screenshots, video, and browser evidence.
   Tiny fixes, documentation, refactors, and non-UI work use test evidence
   without ceremonial media.
7. An independent reviewer accounts for every approved outcome. Findings route
   to the exact owner and files. At most five repair cycles may run.
8. A clean review authorizes a guarded merge. When delivery is configured, a
   separate explicit command deploys, checks health, and attempts the configured
   rollback on failure.
9. Every input, output, command, receipt, transition, and artifact remains
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
