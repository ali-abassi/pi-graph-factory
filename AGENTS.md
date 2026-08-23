# Pi Graph Factory

This is the local software-factory policy layer around Pi Graph Core. Keep the
Core runner external. `scripts/factory.py` is the canonical lifecycle and state
owner; compiled Pi Graph YAML is an inspectable policy projection, never a
second source of truth.

Never describe a prototype boundary as production-ready. Keep merge application
off by default. New automation needs deterministic evidence and a failing test
for its refusal path. Never weaken the frozen benchmark or reliability cases to
make an implementation score pass. Preserve unrelated work and generated run
evidence.
