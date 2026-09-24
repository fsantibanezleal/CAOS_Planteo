# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions are `X.XX.XXX` in this file, the
git tag and any interface string, and the semver form with zeros dropped in `pyproject.toml`.

## [0.02.001] - 2026-09-24

### Fixed

- **The canonical form folds nested products (R-012),** as it already folded nested sums. A rate
  written `-1 * (k * m)` and one written `-1 * k * m` compared as different forms, so a candidate that
  grouped a product differently from its reference could never be found equivalent. Found on the
  first model run of Enunciado's dynamics corpus. The change can only turn a not-proven-equivalent
  into an equivalent.

## [0.02.000] - 2026-09-24

### Added

- **The dynamics family** (R-101 to R-110, `docs/design/features/dynamics/`):
  - the roles `state`, whose value is its initial value, and `independent`, whose bounds are the
    range to simulate;
  - the `rate` relation, `d(state)/d(wrt) = expression`, with a dimensional check against the
    independent variable;
  - `Problem.queries`, what a dynamics statement asks, the analogue of an objective.
- Validation for the family: one bounded independent variable, a rate and an initial value per state,
  queries in range. The families do not mix: a rate or a query in an optimization problem, or an
  objective, a decision variable or an inequality in a dynamics problem, is rejected.
- Canonical form for rates and queries. The form of a problem without queries is unchanged.
- `planteo.evaluate` and `planteo.holds`: numbers from the closed node set, with the indexed sum
  refused by name.
- `planteo.system`: a dynamics problem as states, initial values, range, a right-hand side and one
  function per query, for any ODE integrator. Pure Python.
- `planteo.emit.scipy.emit_source`: the same system as a readable Python module for `solve_ivp`, held
  to the evaluator's numbers by a test.

### Changed

- Documents are written at schema 1.1. A 1.0 document loads unchanged.

## [0.01.002] - 2026-09-23

### Fixed

- **A missing field raised a bare KeyError (R-011).** A quantity, an assumption, an open question,
  a span, an objective, a narrative and the problem itself read their fields with a bare index, so a
  missing one reached a run ledger as the string `'span'`, naming neither the field's owner nor the
  keys it had. Four records in Enunciado's ledgers carry exactly that. Every one now raises
  `ValueError("an assumption is missing its 'span' field; got keys [...]")`, worded like the
  messages expression nodes and relations already gave. An `if` node's three fields go through the
  same check.

## [0.01.001] - 2026-09-23

A documentation release. No code changed.

### Fixed

- **The README claimed a MiniZinc emitter that does not exist.** It said the package "emits to Pyomo
  and MiniZinc"; 0.01.000 emits Pyomo only, and the design document already listed MiniZinc as out
  of scope. The claim reached the PyPI project page, which is why this is a release and not only a
  commit.
- The canonical-form page now names a limit it had left implicit: the form keeps the objective's
  sense, so maximising `f` and minimising `-f` are not proven equivalent.

## [0.01.000] - 2026-09-22

First release. The representation, its validator, the Pyomo emitter and canonical comparison.

### Added

- **The `Problem` document**: narrative, quantities, relations, objectives, assumptions, open
  questions and metadata, with a versioned JSON schema and a lossless round trip.
- **Dimensions as first-class data**: seven SI base axes plus currency and count, rational
  exponents, algebra, and comparison by exponent vector rather than by unit label. A quantity cannot
  be constructed without one, and dimensionless must be stated.
- **Provenance spans**: character offsets plus the covered text, so a stored document can be checked
  against its narrative instead of trusted. An inferred element must give its reason. The narrative
  carries a digest that detects an edited source.
- **Open questions**: what the narrative did not determine, with the span that raised it, the
  resolution taken, and the quantities it affects. Unresolved questions surface as warnings and are
  reproduced in the emitted model.
- **A closed expression and relation node set**: constant, reference, sum, product, power, indexed
  sum, conditional; compare, logical, for-all. Closed on purpose, because it is what makes
  dimensional checking total and canonical comparison decidable.
- **The validator**: names, closure, spans, dimensions, determinacy, family completeness, open
  questions. Reports every finding rather than stopping at the first, and names the element in each.
- **The Pyomo emitter**: `emit_source` writes a runnable script with the narrative quoted beside each
  declaration, `build_model` builds a live `ConcreteModel`. Both are total on what they accept and
  raise `NotRepresentable` naming the construct otherwise, never emitting a partial model.
- **Canonical form and comparison**: name-independent, order-independent, comparator-oriented, with
  the verdicts `EQUIVALENT` and `NOT_PROVEN_EQUIVALENT` and deliberately no `DIFFERENT`.

[0.01.000]: https://github.com/fsantibanezleal/CAOS_Planteo/releases/tag/v0.01.000
