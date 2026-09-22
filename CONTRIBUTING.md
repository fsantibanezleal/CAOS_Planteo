# Contributing

## The one rule that is unusual here

**Every requirement names the gate that verifies it.** A change that adds behaviour adds a
requirement to `docs/design/SDD.md` in EARS form, and that requirement names the test that fails when
the behaviour is violated:

```
R-0NN  WHEN <trigger>, THE <component> SHALL <behaviour>.
       Gate: tests/test_<file>.py::test_<name>
```

"Tested" is not a gate. "Covered by the suite" is not a gate. The name of the failing test is.

The reason is not bureaucracy. A green check that measures the wrong thing is worse than no check,
because it is believed. Naming the gate in the requirement is what makes that auditable.

## Before you open a pull request

```bash
python -m venv .venv
./.venv/Scripts/python -m pip install -e ".[dev,pyomo]"   # Linux or macOS: .venv/bin/python
./.venv/Scripts/python -m pytest -rs
./.venv/Scripts/python -m ruff check .
```

Run the suite with `-rs`. A skipped test is not a passing test, and a gate that silently skips in
your environment is exactly the failure the rule above exists to catch.

## Design changes

The expression and relation node sets are **closed**. Adding a node is a design change: it goes in
the SDD first, with its dimensional rule, its canonical form and its behaviour in each emitter, and
then in the code. There is no escape hatch that accepts arbitrary expressions, and a pull request
that adds one will be declined however convenient the motivating case is.

## Style

English only, in code, comments, docs and commit messages. No em-dash and no emoji in any content.
Line length 100. The `ruff` settings live in `pyproject.toml`.

## Versioning

`X.XX.XXX` in `VERSION`, the `CHANGELOG`, the tag and any interface string; the semver form with
zeros dropped in `pyproject.toml`. Bump by the nature of the change, not by commit count. Every
release updates the CHANGELOG and carries a `vX.XX.XXX` tag.
