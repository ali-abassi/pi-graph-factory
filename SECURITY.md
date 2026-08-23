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

Configured timeouts terminate overdue adapter process groups; timeouts may be
disabled. Optional token and cost ceilings stop later dispatches based on
normalized receipts. They are disabled by default for subscription-backed
harnesses. An already-running parallel batch can cross a configured local
ceiling, and provider-side limits remain the hard spend boundary.

The controller mechanically checks plan identity, file scope, Git changes,
approved commands, evidence provenance, review citations, and target drift.
Resume additionally verifies recorded process identity, owner scope, commit
shape, and durable receipts before continuing interrupted work. Those checks do
not make arbitrary code safe.

Delivery commands receive the invoking environment and can mutate external
systems. They run only after an applied reviewed merge and an explicit
`deliver` command. Use least-privilege production credentials and idempotent
deploy/health/rollback commands. A host death during an external command cannot
be made transactionally exactly-once from the local run ledger.
