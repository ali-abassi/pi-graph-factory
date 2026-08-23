# Running the factory on Railway Cloud Agents

Railway Cloud Agents can host an entire Pi Graph Factory run on a persistent
Ubuntu VM. This is the recommended off-laptop execution mode for long Codex or
Claude Code subscription-backed sessions.

Railway's current contract is documented at
<https://docs.railway.com/cloud-agents>. Cloud Agents are presently available
through Priority Boarding and may receive breaking changes.

## Why wrap the whole factory

The factory already owns planning, isolated Git worktrees, integration,
evidence, review, recovery, and merge policy. Run that controller on one Cloud
Agent instead of inventing a second remote state machine for individual lanes.
The VM keeps its disk and sessions across disconnects, has GitHub and Railway
CLI authentication, includes Chromium, and exposes port 8080 at a stable public
domain for previews.

Sessions on the same Cloud Agent share one disk. Do not start two factory
controllers against the same run; the factory's one-writer lock will refuse
that locally, but unrelated sessions can still edit the same repository.

## Setup

Install the Cloud Agent-enabled Railway CLI and complete its setup:

```bash
curl -fsSL agents.railway.com | sh
railway login
railway ca setup
```

Confirm the installed binary exposes the Priority Boarding commands:

```bash
railway code --help
railway ca --help
```

If either command is unrecognized, reinstall through `agents.railway.com`; a
standard Railway CLI release may not yet include the Cloud Agent commands.

Launch a fresh named agent with the subscription-backed coding agent you want:

```bash
railway code --codex --new --name pi-graph-factory
```

Or pass a non-interactive Codex task after `--`:

```bash
railway code --codex --new --name pi-graph-factory -- \
  exec "Clone the target repository, install pi-graph-factory, and initialize the approved request. Stop for plan approval."
```

Use `--keep-awake` only when the work must continue after disconnection. Push
the factory branch and retain the run receipt before using `--rm`, because that
destroys the VM disk. Railway documents a limit of 25 agent creations per user
per day, so reuse a dedicated factory VM during interactive iteration and use a
fresh VM when isolation matters more than startup cost.

## Trust and credentials

This protects the laptop from local build processes, but it is not a hostile-
code sandbox. The VM is personal and receives the selected coding agent
credential plus authenticated GitHub and Railway CLIs. Scope GitHub/Railway
access to the repositories and environments the factory actually needs.

The direct launcher delivers the credential for the selected coding agent.
Mixed Codex and Claude Code lanes require both harnesses to be authenticated on
the VM; do not assume launching one automatically authorizes the other.

## Preview and delivery

Cloud Agent port 8080 is suitable for review previews through
`RAILWAY_PUBLIC_DOMAIN`. Railway explicitly recommends deploying a service with
a public domain for production traffic. Configure the factory's separate
delivery contract for deploy, health, and rollback commands; do not treat the
Cloud Agent preview process as the production deployment.
