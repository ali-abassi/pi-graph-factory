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
running unfamiliar repositories or agents. Keep `merge.apply: false` until the
environment and project gates are trusted.

Never place secrets in:

- requests, plans, prompts, or workflow configuration;
- command-line arguments or model-visible environment dumps;
- committed screenshots, video, browser receipts, logs, or run artifacts.

The controller rejects likely secret-bearing `.env` files (except conventional
template names), caches, compiled bytecode, and dependency directories before
integration. This is defense in depth, not secret scanning or sandboxing.

Configured timeouts terminate overdue adapter process groups. Token and cost
ceilings stop later dispatches based on normalized receipts; an already-running
parallel batch can cross a local ceiling, and provider-side limits remain the
hard spend boundary.

The controller mechanically checks plan identity, file scope, Git changes,
approved commands, evidence provenance, review citations, and target drift.
Those checks do not make arbitrary code safe.
