# Security policy

## Reporting

Please report vulnerabilities privately through
[GitHub private vulnerability reporting](https://github.com/ali-abassi/pi-graph-factory/security/advisories/new).
Do not open a public issue for a suspected vulnerability or include real
credentials, private repository content, or exploit data in a report.

## Supported version

Security fixes currently target the latest `main` revision until the first
tagged release.

## Security boundary

Pi Graph Factory runs configured agents and approved shell commands with the
permissions of the invoking local user. Worktrees isolate Git changes; they do
not isolate the filesystem, process table, network, credentials, or operating
system.

Treat requests, repository content, model output, tool output, and review text
as untrusted data. Use an ephemeral container, VM, or restricted account when
running unfamiliar repositories or agents. A Railway Cloud Agent moves
execution off the laptop but remains a credentialed personal VM, not a hostile-
code sandbox. Keep `merge.apply: false` until the environment and project gates
are trusted.

Never place secrets in:

- requests, plans, prompts, or workflow configuration;
- command-line arguments or model-visible environment dumps;
- committed screenshots, video, browser receipts, logs, or run artifacts.

The controller rejects likely secret-bearing `.env` files (except conventional
template names), caches, compiled bytecode, and dependency directories before
integration. This is defense in depth, not secret scanning or sandboxing.

Generated planning runs Graphify locally against repository contents. Its
generated `graphify-out/` directory is locally ignored and must not be committed;
the graph can reveal source paths, symbols, and relationships. The default
semantic configuration sends supported repository docs, papers, and images to
the configured DeepSeek-compatible endpoint and uses the model to label code
communities; code AST extraction remains local. Do not enable it for sensitive
material unless that provider is an approved data processor. The Pi credential
bridge keeps the key out of command arguments and receipts and redacts it from
captured Graphify output, but the child process necessarily receives it in its
environment.

Auto-install uses pinned `graphifyy==0.9.48` (and its `openai` extra for semantic
backends) through `uv`, but package download, parser execution, and semantic
provider calls remain supply-chain and data-egress boundaries. Disable
`intelligence.auto_install`, preinstall an audited build, or set
`PI_GRAPH_FACTORY_GRAPHIFY` to a trusted command in restricted environments.

The independent plan judge is an AI quality control and the default configured
plan authority, not a security boundary. The controller validates its schema,
recomputes its weighted score, limits revision cycles, and binds a pass to the
exact generated-plan hash. Its rubric has not yet been calibrated against a
large human-rated corpus; use `approval.mode: human` for high-impact work that
requires an operator checkpoint. Externally supplied plans always require
exact human approval because they bypass the generated-plan judge.

Under the default judge authority, a generated plan cannot pause on a blocking
question. The controller returns it for bounded revision into an explicit,
evidence-backed reversible assumption. Exhausting that bounded quality loop
fails closed; it does not silently guess, weaken the score, or authorize effects
that the request and configured delivery boundary did not grant.

Configured timeouts terminate overdue adapter process groups; timeouts may be
disabled. Optional token and cost ceilings stop later dispatches based on
normalized receipts. They are disabled by default for subscription-backed
harnesses. An already-running parallel batch can cross a configured local
ceiling, and provider-side limits remain the hard spend boundary.

The controller mechanically checks generated-plan judgment, plan identity, file
scope, Git changes, approved commands, evidence provenance, review citations,
and target drift.
Resume additionally verifies recorded process identity, owner scope, commit
shape, and durable receipts before continuing interrupted work. Those checks do
not make arbitrary code safe.

Delivery commands receive the invoking environment and can mutate external
systems. They run only after an applied reviewed merge and an explicit
`deliver` command. Use least-privilege production credentials and idempotent
deploy/health/rollback commands. A host death during an external command cannot
be made transactionally exactly-once from the local run ledger.
