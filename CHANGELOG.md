# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions are `X.XX.XXX` in this file, the
git tag and any interface string, and the semver form with zeros dropped in `pyproject.toml`.

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
