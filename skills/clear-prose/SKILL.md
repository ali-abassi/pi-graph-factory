---
name: factory-clear-prose
description: Keep durable factory prose direct, specific, evidence-bound, and free of formulaic AI filler.
---

Apply this to human-readable text inside plans, research findings, risks, issue
messages, receipts, documentation, UI copy, pull requests, and commit messages.
The typed contract, exact facts, and repository terminology outrank style.

1. Read the whole artifact and identify its audience, job, and existing voice.
2. Preserve every fact, qualifier, constraint, citation, technical term, and
   product decision. Never invent a name, number, date, source, mechanism,
   anecdote, promise, opinion, or measured result to make prose sound concrete.
   Name missing evidence instead of polishing a vague claim into a fact.
3. Prefer the real actor, mechanism, consequence, command, or measurement over
   abstract importance. Name a source or remove a vague attribution.
4. Cut throat-clearing, inflated claims, promotional adjectives, generic
   optimism, recap endings, chatbot chatter, reasoning scaffolding, repeated
   headings, and sentences that only tell the reader what to notice.
5. Describe current behavior in docs and comments. Mention the old behavior only
   in changelogs, migrations, incident reports, or other history-shaped text.
6. Make the minimum effective edit. Treat patterns as candidates, not automatic
   defects. A deliberate fragment, passive sentence, repeated term, list of
   three, or em dash can be correct. Do not flatten an author's voice to satisfy
   a word blacklist.
7. Match the medium. Technical and factual artifacts should stay neutral. UI
   text should match the product. Personal voice belongs only where the source
   or approved request calls for it.

Never rewrite code, shell commands, JSON keys, identifiers, URLs, quotations,
logs, error text, citations, frontmatter, or test fixtures as a prose cleanup.
Do not expose chain-of-thought. Do not claim a detector score or promise that
text is undetectably human.

Before returning, ask:

- Did any fact or scope qualifier change?
- Can a generic sentence be replaced by supplied evidence or deleted?
- Does the text state what happened instead of announcing or praising it?
- Did the edit preserve protected spans and the artifact's required format?
- Is any remaining unusual phrasing a defensible voice choice? If so, keep it.

This factory-specific synthesis draws on the reviewed MIT-licensed Stop Slop,
No AI Slop, Humanizer, Slopbeth, Deslop, and Anti-Slop skills. Source decisions
and pinned revisions are recorded in `docs/PROSE_SKILLS.md`.
