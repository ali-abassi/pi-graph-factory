# Prompt engineering and measured optimization

Pi Graph Factory treats prompts and optimization as engineering work with
controller-enforced contracts. They are specialist lanes inside the ordinary
plan → implement → integrate → prove → review lifecycle, not hidden
post-processing agents.

## Production prompt contract

The `prompt` owner handles independently owned system prompts, tool
descriptions, structured-output schemas, evaluator prompts, and prompt
pipelines. Prompt text embedded in a product-owned file stays with `product`,
which has the same prompt-engineering skill. One file always has one owner.

A prompt-owned task cannot pass plan validation without `prompt_contract`:

```json
{
  "prompt_contract": {
    "runtime": "decision-agent-v2",
    "objective": "Return a grounded routing decision.",
    "authoritative_context": ["signed host policy"],
    "untrusted_inputs": ["user request", "retrieval", "tool output"],
    "output_schema": "schemas/decision.schema.json",
    "abstention": "status=insufficient_evidence with missing fields",
    "host_enforcement": ["schema validation", "tool allowlist"],
    "evaluation_commands": ["python3 -m unittest tests.test_prompt_contract -v"],
    "cases": [
      {"id":"happy","kind":"happy_path","assertion":"valid grounded decision"},
      {"id":"missing","kind":"missing_input","assertion":"typed failure"},
      {"id":"malformed","kind":"malformed_input","assertion":"typed failure"},
      {"id":"injection","kind":"prompt_injection","assertion":"data stays data"},
      {"id":"tool-failure","kind":"tool_failure","assertion":"observable failure"},
      {"id":"abstain","kind":"abstention","assertion":"declared abstention form"}
    ]
  }
}
```

The controller requires every field, all six case kinds, and evaluation
commands assigned to the prompt task's acceptance. That makes the
runtime, trust boundary, schema, host responsibility, and failure surface
inspectable. A no-op `true` command is rejected. Each evaluation command must
end with a typed `pi-graph-factory.prompt-evaluation.v1` receipt; across those
receipts, every declared case id and kind must have `passed: true` plus non-empty
observed evidence. Case descriptions alone are never proof.

```json
{
  "schema": "pi-graph-factory.prompt-evaluation.v1",
  "runtime": "decision-agent-v2",
  "cases": [
    {"id":"happy","kind":"happy_path","passed":true,"evidence":"observed output"}
  ]
}
```

## When hill climbing is appropriate

Use a direct implementation task when the defect and remedy are known. Use
`optimization` only when several plausible changes exist and a repeatable
metric can distinguish them: for example, improving a prompt, agent harness,
routing policy, code path, design, copy, or workflow against a task suite or
outcome metric.

The approved plan freezes this generic optimization contract:

```json
{
  "optimization": {
    "objective": "Increase passed tasks without preservation regressions.",
    "evaluation_version": "eval-v1",
    "mutable_files": ["agent/**"],
    "forbidden_files": ["eval/**", "tests/**"],
    "metric": {
      "name": "passed_tasks",
      "direction": "maximize",
      "minimum_gain": 1
    },
    "target_score": 20,
    "development_commands": ["python3 scripts/score.py"],
    "preservation_commands": ["python3 -m unittest tests.test_public_api -v"],
    "promotion_commands": ["python3 scripts/run_holdout.py"],
    "max_candidates": 5,
    "max_consecutive_non_keeps": 3,
    "max_seconds": 28800,
    "stop_conditions": [
      "target achieved",
      "candidate budget exhausted",
      "plateau",
      "wall time exhausted",
      "invalid evaluation"
    ]
  }
}
```

The one development command must exit successfully and end with:

```json
{"schema":"pi-graph-factory.metric.v1","evaluation_version":"eval-v1","score":14}
```

`mutable_files` exactly matches the optimization task scope. Forbidden
evaluator and case files cannot overlap any implementation task. Preservation
commands also appear in top-level acceptance so the integrated commit rechecks
them. Promotion commands must not appear in ordinary acceptance because the
optimization controller invokes them exactly once.

## Controller-owned search

```text
frozen plan
    ↓
controller fingerprints protected files and scores untouched baseline
    ↓
fresh detached candidate worktree
    ↓
optimizer proposes one hypothesis + one scoped mutation
    ↓
controller checks Git scope, protected fingerprint, metric, and gates
    ↓
keep as incumbent or delete isolated worktree
    ↓
repeat until candidate / plateau / wall-time bound
    ↓
controller applies best incumbent and runs promotion once
    ↓
controller receipt → ordinary integration, proof, review, guarded merge
```

The optimizer cannot grade itself. It receives baseline/incumbent scores and
prior controller history, then returns only a candidate id, hypothesis, diff,
and cheap local checks. The controller computes every score, owns keep/discard,
enforces at most ten candidates plus the plateau and wall-time limits, deletes
rejected candidate worktrees, fingerprints protected files, and creates the
promotion receipt bound to the lane commit. If nothing clears the approved
minimum gain and gates, the lane fails without a promoted diff.

The controller writes a durable attempt record before baseline and reserves
promotion before invoking it. An interrupted generic search fails closed on
resume instead of redispatching omitted candidates or replaying promotion; start
a new approved run. Promotion is also consumed once across review cycles. If
review finds a defect in the promoted optimization, Factory enters
`human_required`; a new evaluation version and exact plan approval are required
before fresh search/promotion. Use `piw optimize` when crash-resumable search is required.

Generic optimization is still not an OS sandbox. An agent with normal file
and shell access may read data or invoke evaluator/promotion commands visible
in its environment, even though the controller bounds its own dispatches and
promotion call and checks final scope/protected bytes. Use an external sandbox
for an adversarial-agent or private-holdout threat model.

## Stronger Pi Graph workflow optimization

For Pi Graph `steps.yaml` optimization, use the installed `piw optimize`
lifecycle rather than approximating it in Factory. It adds schema-frozen
contracts, one-mechanism JSON-pointer diffs, protected source hashes, canonical
batch evaluation, finite token/cost/failure budgets, exact rollback,
hash-chained durable events, crash recovery, and one-use private holdout
promotion. See Pi Graph's `docs/optimization.md` and start with:

```bash
piw version --json
piw doctor --json
piw optimize scaffold workflow/steps.yaml \
  --inputs workflow/dev.jsonl --holdout /private/holdout.jsonl --json
```

## AutoAgent relationship

[thirdlayerinc/autoagent](https://github.com/thirdlayerinc/autoagent) supplied
useful high-level patterns: baseline before mutation, diagnose trajectories,
change one general harness mechanism, score, keep or discard, and prefer simpler
ties. Its public repository currently lacks a committed license file despite
the README's MIT statement, so this project copies no code.

Factory rejects AutoAgent's unbounded “NEVER STOP” instruction. Candidate,
plateau, and wall-time bounds are mechanical, not suggestions.
