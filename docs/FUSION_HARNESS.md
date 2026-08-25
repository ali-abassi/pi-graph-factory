# Fusion Harness source review

Pi Graph Factory reviewed Disler's MIT-licensed Fusion Harness at commit
`01a348202482cad0e7d3c34eada180f711aaddd7`. The review covered the TypeScript
runner, collaboration graph, writer lease, prompts, and orchestration contract
tests—not only the README. No Fusion code or prompt is vendored here.

## Adopt now

| Fusion mechanic | Factory adaptation |
| --- | --- |
| Typed dependency DAG | Plans declare `depends_on` task ids. The controller validates unknown edges and owner cycles, runs ready owners in parallel waves, and builds each downstream worktree on the committed transitive dependency outputs. This preserves isolated Git ownership while preventing a UI lane from guessing or recreating another lane's API or assets. |
| Live child event stream | Pi and Codex JSON output plus every harness stderr line are written to private per-attempt files while the process is still running. `inspect` uses those files for last-activity evidence. Raw streams stay private because prompts and tool output can contain sensitive repository data. |
| Immediate failed-task projection | A completed lane failure is written to state and events as soon as its future returns, even while sibling lanes finish. `inspect` exposes the pending lane blocker instead of showing an apparently healthy batch. |
| Gate-first red baseline | Adopt selectively for bug fixes and new executable behavior where a stable public seam exists. Record the initial failing reproduction before implementation. Do not manufacture a red phase for docs, generated art, metadata, or work whose truthful seam exists only after integration. |

## Already covered by stronger factory controls

| Fusion mechanic | Existing factory control |
| --- | --- |
| Single writer lease | One durable run lock owns state, every implementer writes only in an isolated Git worktree, scope is derived from Git, and integration is serialized. This is stronger for repository mutation than sharing one working directory. |
| Process-tree shutdown | Every adapter and command has a process group, timeout, TERM grace period, KILL fallback, durable active record, and guarded resume reconciliation. |
| Persistent reports and usage | Immutable contexts, raw streams, native Claude transcripts, normalized receipts, cache-aware usage, append-only events, evidence manifests, and commit-bound final receipts already exist. |
| Context synchronization | Downstream worktrees now contain exact committed dependency outputs and receive typed dependency commit/receipt summaries. A conversational ACK hash would duplicate the controller's stronger Git and SHA-256 bindings. |

## Bank as measured experiments

- Use independent multi-model opinions or debate only for consequential,
  genuinely unsettled architecture or adversarial review. Promote it to a
  default stage only if the human-rated corpus shows higher unique-defect yield
  than one independent judge at acceptable latency.
- Add a normalized local task-board projection over the canonical event ledger.
  It may display waves, live text/tool events, tokens, throughput, blockers, and
  evidence, but it must never become a second lifecycle state store.
- Test validator-authored executable gates for domains where the repository
  lacks useful checks. Keep approved/frozen evaluators authoritative when they
  already exist.
- Add bounded gate self-diagnosis only when the controller can prove the
  evaluator—not the candidate—failed. Preserve the old gate and its failure,
  allow one audited repair, rerun it without charging the implementer, and never
  weaken a legitimate acceptance criterion.

## Reject

- Do not replace isolated worktrees with Fusion's shared-CWD single-writer
  model. It reduces merge mechanics but weakens containment and parallel
  implementation.
- Do not run every request through architect, debate, fusion, and collaboration
  modes. Extra models are not evidence of better work.
- Do not use one universal `uv` Python gate. Native Swift, Xcode, browser,
  package, and project-owned checks remain the correct seams for their domains.
- Do not let a validator repeatedly move the goalposts. A proven evaluator
  defect gets at most one audit-preserving repair; legitimate failures stay.

Source: <https://github.com/disler/fusion-harness/tree/01a348202482cad0e7d3c34eada180f711aaddd7>
