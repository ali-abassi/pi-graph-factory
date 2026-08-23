# Pi Graph Factory

This is the local software-factory policy layer around Pi Graph Core. Keep the
Core runner external. `scripts/factory.py` is the canonical lifecycle and state
owner; compiled Pi Graph YAML is an inspectable policy projection, never a
second source of truth.

Apply Ponytail's full discipline to code changes: understand the touched flow,
then prefer deletion/reuse, standard library, native platform behavior, an
installed dependency, and finally the fewest new lines that work. Never cut
validation, data-loss handling, security, accessibility, approved behavior, or
the smallest meaningful check.

Never describe a prototype boundary as production-ready. Keep merge application
off by default. New automation needs deterministic evidence and a failing test
for its refusal path. Never weaken the frozen benchmark or reliability cases to
make an implementation score pass. Preserve unrelated work and generated run
evidence.

For maintenance of this repository, Ali's instruction to update, merge, ship,
or push to production is standing authorization to finish the verified change
and push it directly to `main`. Run the relevant local reliability and security
gates, then push without asking again and without opening a pull request unless
Ali explicitly requests one. If the host rejects the direct push, attempt the
authorized repository-owner path and report only a real remaining blocker.
This repository-maintenance rule does not change the factory product's public
default: target-repository merge and delivery remain off until a run explicitly
enables them.
