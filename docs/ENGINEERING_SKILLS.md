# Engineering skill decisions

Pi Graph Factory uses engineering skills only where they strengthen an existing
boundary. It does not turn each useful skill into another mandatory agent or
state machine. These decisions were made against Matt Pocock's MIT-licensed
skills at commit `5b15a47f2d7150f545fbcacbfe381787fc0230dc`.

## Where they fit

| Capability | Decision | Factory placement |
| --- | --- | --- |
| `grill-with-docs` | Adopt now | An interactive intake producer. It emits the same approved Goal Brief contract as `/grill-me`, while updating durable domain context and only necessary ADRs. It does not create a fourth downstream intake lifecycle. Commit its project-doc changes before factory initialization so Graphify can index them. |
| `diagnosing-bugs` | Adapt now | Conditional implementer discipline for defects only: reproduce, minimize, test falsifiable hypotheses when needed, add a regression at the public seam, rerun the original reproduction, and remove diagnostics. |
| `tdd` | Adapt now | Implementer discipline for executable behavior at the seam approved in the exact plan. Work proceeds red-to-green in thin vertical slices. Docs and metadata do not receive ceremonial tests. |
| `triage` | Adopt as an edge adapter | Issues and pull requests may move through one category plus one triage state before they become factory requests. This state belongs in the issue tracker, not in the factory run ledger. The adapter remains to be built. |
| `improve-codebase-architecture` | Adopt on demand | A discovery workflow may scan for deepening opportunities and present an HTML report. The chosen opportunity is then grilled or submitted as a normal factory request. It must not run on every change, and its report is not implementation proof. |
| `setup-matt-pocock-skills` | Do not adopt wholesale | Its tracker labels and repository layout are useful source ideas, but a vendor-specific one-time initializer would duplicate factory bootstrap and couple the core to one tracker. A future provider-neutral issue adapter may borrow the minimal label mapping. |
| `to-spec` | Optional edge adapter | Useful when a conversation must become a durable issue without another interview. It is not a required factory stage because intake plus the judged plan already provide the executable contract. Publishing remains an explicit external side effect. |
| `to-tickets` | Adopt for work larger than one run | Use vertical tracer-bullet tickets and native blocking edges before the factory when a program cannot fit one approved run. Each ready ticket becomes one factory request. This portfolio-level map is distinct from the controller's small intra-run `depends_on` DAG, which orders concrete owner outputs inside one approved plan. |
| `implement` | Do not adopt as a wrapper | The factory already provides a stronger implementation lifecycle: isolated worktrees, typed receipts, integration, proportional evidence, independent review, bounded repair, and guarded merge. Its useful TDD and review ideas are incorporated directly. |
| `wayfinder` | Adopt on demand before execution | Use it for genuinely huge, foggy work whose decisions exceed one agent session. It resolves a decision map, not code. Once the route is clear, `to-tickets` or a normal request feeds the factory. |
| `code-review` | Adapt now | The existing independent reviewer now evaluates two explicit axes: approved behavior and repository quality. This is combined with the existing security, evidence, and Ponytail minimality checks rather than adding another reviewer stage. |

## Resulting flow

```text
issue / PR ── optional tracker triage ───────────────┐
conversation ── grill / grill-with-docs / auto ─────┤
huge foggy program ── wayfinder ── tickets ─────────┤
architecture search ── HTML report ── chosen item ──┤
                                                    ↓
                                      canonical factory request
                                                    ↓
                        Graphify + project memory → planner → plan judge
                                                    ↓
                             exact-hash judge authorization by default
                                                    ↓
                           isolated implementation with conditional
                              TDD / bug diagnosis + Ponytail
                                                    ↓
                           integration → proportional proof → review
                                                    ↓
                              criterion repair loop or merge
```

The separation is intentional: tracker state, portfolio decisions, architecture
discovery, and conversation publishing are adapters around a run. Deterministic
execution, evidence, repair, and merge authority remain inside one controller.

Writing quality is a separate cross-cutting concern. See
[Prose skill decisions](PROSE_SKILLS.md) for the ten-source review and the one
small evidence-bound skill loaded into existing roles.

## Upstream sources

- [Diagnosing bugs](https://github.com/mattpocock/skills/blob/5b15a47f2d7150f545fbcacbfe381787fc0230dc/skills/engineering/diagnosing-bugs/SKILL.md)
- [TDD](https://github.com/mattpocock/skills/blob/5b15a47f2d7150f545fbcacbfe381787fc0230dc/skills/engineering/tdd/SKILL.md)
- [Triage](https://github.com/mattpocock/skills/blob/5b15a47f2d7150f545fbcacbfe381787fc0230dc/skills/engineering/triage/SKILL.md)
- [Architecture improvement](https://github.com/mattpocock/skills/blob/5b15a47f2d7150f545fbcacbfe381787fc0230dc/skills/engineering/improve-codebase-architecture/SKILL.md)
- [Setup](https://github.com/mattpocock/skills/blob/5b15a47f2d7150f545fbcacbfe381787fc0230dc/skills/engineering/setup-matt-pocock-skills/SKILL.md)
- [To spec](https://github.com/mattpocock/skills/blob/5b15a47f2d7150f545fbcacbfe381787fc0230dc/skills/engineering/to-spec/SKILL.md)
- [To tickets](https://github.com/mattpocock/skills/blob/5b15a47f2d7150f545fbcacbfe381787fc0230dc/skills/engineering/to-tickets/SKILL.md)
- [Implement](https://github.com/mattpocock/skills/blob/5b15a47f2d7150f545fbcacbfe381787fc0230dc/skills/engineering/implement/SKILL.md)
- [Wayfinder](https://github.com/mattpocock/skills/blob/5b15a47f2d7150f545fbcacbfe381787fc0230dc/skills/engineering/wayfinder/SKILL.md)
- [Code review](https://github.com/mattpocock/skills/blob/5b15a47f2d7150f545fbcacbfe381787fc0230dc/skills/engineering/code-review/SKILL.md)
