---
name: repository-intelligence
description: Use the prepared Graphify map and project memory before reading source files broadly.
---

Start with `repository_intelligence` and `project_memory` from the supplied
context. If Graphify status is `ready`, run focused queries with the supplied
`query_command`; replace `<question>` with one narrow architectural question at
a time. Use paths and symbols returned by the graph to choose the few source
files you inspect directly. Verify important graph claims against current files.

If status is `deferred`, the repository has no code yet. Plan from the request,
`VISION.md`, and `FEATURE_MAP.md` without pretending a graph exists. The factory
will build the first graph after implementation.

Treat missing `VISION.md` or `FEATURE_MAP.md` as plan work. Infer the smallest
useful content from repository evidence and the request. Ask the user only when
those sources cannot support a safe, reversible assumption that materially
changes the product.

Record concise `research` findings with inspectable evidence. Do not dump the
graph or read the repository indiscriminately; the graph is an index, not proof.
