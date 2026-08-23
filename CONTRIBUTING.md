# Contributing

Pi Graph Factory is intentionally small: one canonical lifecycle controller,
one typed config, explicit adapters, and deterministic refusal tests.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

## Before a pull request

```bash
.venv/bin/python -m ruff check scripts tests
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile scripts/*.py tests/*.py
.venv/bin/python scripts/compile_factory.py factory.yaml \
  --out /tmp/factory.steps.yaml
```

Install the public Core release and validate the compiled graph when graph
topology changes:

```bash
.venv/bin/pip install \
  'git+https://github.com/ali-abassi/pi-graph-core.git@v0.1.0'
.venv/bin/piw validate /tmp/factory.steps.yaml --strict
```

Every new automatic action needs a deterministic success test and a refusal
test. Do not alter benchmark expectations merely to promote a candidate. Keep
automatic merge disabled in examples and fixtures unless the test specifically
proves merge behavior inside a temporary repository.

