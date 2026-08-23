# Prose skill decisions

Ten anti-slop and humanizer skills were reviewed at source level. They solve
nearly the same problem, so the factory takes the strongest compatible rules
into one small `skills/clear-prose` skill. It loads into existing roles and adds
no agent, rewrite stage, score, or merge gate.

## Source-by-source decision

| Source | Decision | What the factory keeps or rejects |
| --- | --- | --- |
| `stop-slop` by Hardik Pandya | Partial adopt | Keep directness, specificity, density, and rhythm checks. Reject absolute bans on adverbs, passive voice, lists of three, and em dashes; those rules create false positives in technical prose. |
| `no-ai-slop` by Peter Yang | Strong adopt | Keep minimum effective edits, the portability test for generic sentences, source preservation, and the rule that an audit names observable patterns rather than guessing who wrote text. |
| `humanizer` by Blader | Strong adopt | Keep fact preservation, voice matching, false-positive checks, protected quotations, and current-state documentation. Reject a large always-on pattern catalog inside every agent prompt. |
| `unslop` from Cursor's plugin repository | Concept only | Keep plain speech and concrete mechanisms. Reject forced “soul,” deliberate mess, or opinions in factual factory artifacts. The repository did not expose a license in GitHub metadata, so no wording was copied. |
| `slopbeth` by Ehmo | Strong adopt | Keep the evidence boundary: vague input remains a proof gap, not a polished promise. Keep detector humility and preservation of scope qualifiers. Reject bundled prose benchmarks as a factory runtime dependency. |
| `humanizer` by Adam Boudj | Partial adopt | Keep protected code/quotes/frontmatter, false-positive clusters, and context-specific technical voice. Reject 53-pattern scoring, synthetic voice profiles, and aggressive rewrite loops for normal factory work. |
| `deslop` by Stephen Turner | Partial adopt | Keep register-aware technical writing, exact domain terminology, active actors where clearer, and direct cited claims. Reject fixed 35/50 scoring and blanket punctuation rules. |
| `anti-slop` by Elithrar | Strong adopt | Keep its surgical workflow: read the whole artifact, collect candidates, separate formula from voice, make the smallest edits, and stop before the prose turns flat. |
| `humanize` by Aasha | Partial adopt | Keep no-fabrication, current-state docs, repo-aware protected spans, and internal self-audit. Reject slop-lint scores and a separate repository rewrite workflow. |
| `anti-ai-slop-writing` by Jalaal | Limited concept only | Keep medium-aware formatting and the ban on fabricated specificity. Reject universal activation, rigid punctuation quotas, intentional grammatical mess, forced word rarity, and detector-oriented claims. The repository did not expose a license in GitHub metadata, so no wording was copied. |

## Factory rule

The merged rule is deliberately narrower than any source skill:

- Apply it only to human-readable prose, including string values inside typed
  receipts. Never rewrite contract keys, commands, identifiers, logs, quotes,
  citations, URLs, code, frontmatter, or fixtures.
- Preserve facts, qualifications, technical language, and approved scope.
- Replace generic claims with supplied evidence. If evidence is absent, name the
  gap or cut the claim. Do not invent a better-sounding detail.
- Prefer current behavior, named actors, concrete mechanisms, and measured
  outcomes. Cut announcements, praise, puffery, recaps, and chatbot residue.
- Make surgical edits and respect intentional voice. No token blacklist or
  punctuation mark proves AI authorship by itself.

This belongs inside planner, plan-judge, implementer, designer, and reviewer
prompts because those roles already produce durable prose. A post-processing
agent would risk changing typed evidence after the responsible role produced it.

## Pinned sources

- [Stop Slop](https://github.com/hardikpandya/stop-slop/blob/8da1f030185bdfe8471220585162991eaeb970e9/SKILL.md)
- [No AI Slop](https://github.com/petergyang/no-ai-slop/blob/d30eddb9e04562234f2070b5ee63ca4649d9a05e/skills/no-ai-slop/SKILL.md)
- [Blader Humanizer](https://github.com/blader/humanizer/blob/e2e92e7b4b8229253ed5c8e81dc65463fdeddda5/SKILL.md)
- [Cursor Unslop](https://github.com/cursor/plugins/blob/46125561306434d8a1d7745d540d8932ab0cd2a2/pstack/skills/unslop/SKILL.md)
- [Slopbeth](https://github.com/ehmo/slopkit/blob/b33718bb9283c11b09567dc714f92d90ffb7bd16/skills/slopbeth/SKILL.md)
- [Adam Boudj Humanizer](https://github.com/Aboudjem/humanizer-skill/blob/9a7f35b7b9ad8c3abd71f10757ec9f91fb8ae165/skills/humanizer/SKILL.md)
- [Deslop](https://github.com/stephenturner/skills/blob/48287d806e61534bc14939b55b72c3f3f11a7db5/deslop/SKILL.md)
- [Elithrar Anti-Slop](https://github.com/elithrar/dotfiles/blob/36b4a7e8d41b55ff5dff568a22f62bb0214967df/.agents/skills/anti-slop/SKILL.md)
- [Sounds Human](https://github.com/aashaexo/soundshuman/blob/a45cfbba9fde843d670e553a0aa98f6a23d7fb28/SKILL.md)
- [Anti-AI-Slop Writing](https://github.com/jalaalrd/anti-ai-slop-writing/blob/63255f9bbb75a265dc5786a04535cd033f487756/skills/anti-ai-slop-writing/SKILL.md)
