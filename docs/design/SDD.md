# planteo, software design document

Written before any code, per ADR-0075. Status: draft for review. Date: 2026-09-22.

Research this design rests on: the Enunciado dossiers, in particular the measured formalization gap
across four fields and the oracle analysis. Every design choice below that cites evidence names the
finding it comes from.

## 1. Problem

A narrative problem statement is ambiguous, under-specified and unit-bearing. Turning it into a solver
model, a simulation, an experiment design or a learning task is done today by writing code directly
from the text, which loses the two things that decide whether the result is right: **which words
produced which symbol**, and **what the words did not say**.

`planteo` is the representation in between. It holds a problem after it has been read and before it
has been solved: typed quantities with dimensions, relations, objectives, the assumptions that were
made, and the questions the narrative left open, each traceable to the span of text it came from.

The package does not call a language model and does not solve anything. It defines the object, checks
it, and emits it.

## 2. Non-goals

- **Not a translator.** `planteo` does not read natural language. Producing a `Problem` from text is
  the harness's job (`copela`); this package defines the target and validates it.
- **Not a solver, and not a solver wrapper.** It emits models. Running them belongs elsewhere.
- **Not a modelling language.** It is not competing with MiniZinc or Pyomo; it emits to them.
- **Not an evaluator.** Structural comparison of two problems is in scope because it is a property of
  the representation. Scoring a model against a reference corpus is not.
- **No natural-language generation.** Rendering a `Problem` back to prose is a later, separate
  decision, not part of this design.

## 3. The core design decision

**Every quantity carries a dimension, and every element carries its provenance span.**

Both are non-negotiable and both come from recorded failures rather than from taste.

Dimensions: on this account, a set of anchor-slice constants expressed as 0-to-1 fractions were
applied to quantities in MW, TWh and metres. Four methods broke and two of them had already been
published. A representation for physical and economic problems that treats a number as a float invites
exactly that. So a quantity without a dimension is not representable: dimensionless is a dimension and
must be stated.

Provenance: the formalization gap measured in the research is a gap between an artifact that runs and
an artifact that means what the text said. It cannot be audited unless each symbol points back at the
words that produced it. The span is what makes a wrong formalization explainable instead of merely
wrong.

## 4. The object model

```
Problem
  narrative      : Narrative          # the source text, hashed, with its provenance
  quantities     : [Quantity]         # every named thing, with a dimension
  relations      : [Relation]         # equalities, inequalities, logical structure
  objectives     : [Objective]        # sense and expression; zero for a pure feasibility problem
  assumptions    : [Assumption]       # stated explicitly, each with a span or marked as inferred
  open_questions : [OpenQuestion]     # what the narrative did not determine
  family         : Family             # optimization | dynamics | experiment | learning
  metadata       : Metadata           # ids, version, provenance of the formalization itself
```

`Quantity` carries name, role (parameter, variable, derived, observed), a `Dimension`, a domain
(real, integer, boolean, set-valued, with bounds), an optional value, and a `Span`.

`Dimension` is the seven SI base exponents plus a currency slot and a count slot, with a symbolic unit
string. Dimensionless is exponents all zero and is stated, never defaulted.

`Span` is a character range into the narrative plus the exact substring, so a span survives being
detached from its text and can be checked against it.

`Relation` is a typed expression tree over quantities, with a comparator and a span. Expression nodes
are a closed set: constant, quantity reference, sum, product, power, sum-over-index, conditional,
logical connective. A closed set is what makes structural comparison decidable.

`OpenQuestion` is the part no other representation in the research has: the narrative said "minimise
cost" and never said whether setup cost is included; that is recorded as an open question with the
span that triggered it and the choice that was taken, rather than silently resolved.

### Family specialisations

Each family adds its own required structure on top of the core, and nothing else:

- **optimization**: at least one objective, or an explicit feasibility declaration.
- **dynamics**: a state vector, an independent variable, and a relation per state component.
- **experiment**: factors, levels, blocking structure, randomisation unit, response, analysis model.
- **learning**: target, feature availability time, split policy, metric, baseline.

## 5. Contracts

**Ingestion contract** (anything to `Problem`): a `Problem` is accepted only if it validates. The
validator is the gate, and it rejects rather than coerces.

**Artifact contract** (`Problem` to a backend): every emitter is total on validated problems of its
declared family and class, or raises a typed `NotRepresentable` naming the construct it cannot
express. An emitter never silently drops a relation. This is the rule that prevents the failure where
a constraint disappears and the model still solves.

Serialisation is JSON with a versioned schema, and the schema version is part of the document.

## 6. Validators

1. **Dimensional consistency.** Every relation is checked term by term; adding metres to seconds is a
   rejection, not a warning. Comparators require matching dimensions on both sides.
2. **Closure.** No free symbol: every reference in a relation resolves to a declared quantity.
3. **Determinacy.** Every quantity is either given a value, declared a decision variable, or derived
   by exactly one relation. Anything else is under- or over-determined and is reported as such.
4. **Span integrity.** Every span's stored substring matches the narrative at its offsets.
5. **Family completeness.** The family's required structure is present.

## 7. Emitters, first release

Optimization only, per the build order. Pyomo first because it is solver-agnostic and reaches HiGHS,
CBC and SCIP; then MiniZinc for the constraint classes; OR-Tools CP-SAT after. The emitter interface
is fixed now so later families do not reshape it.

## 8. Structural comparison

Two problems compare by canonical form: quantities renamed to canonical indices by structural
position, relations normalised (sides ordered, terms sorted, comparators oriented), and the result
hashed. Equality of canonical form is sufficient for equivalence, not necessary, and the package says
so: a `different` verdict is `not-proven-equivalent`, never `proven-different`.

This is deliberately weaker than the graph-isomorphism approach in the research, and the boundary is
stated rather than blurred. Isomorphism belongs in the harness where the reference models live.

## 9. Requirements

Each names the gate that verifies it, per ADR-0075.

```
R-001  THE validator SHALL reject a Problem containing a relation whose two sides
       have different dimensions.
       Gate: tests/test_validate_dimensions.py::test_mismatched_sides_rejected

R-002  THE validator SHALL reject a Problem containing a reference to an undeclared quantity.
       Gate: tests/test_validate_closure.py::test_free_symbol_rejected

R-003  WHEN a quantity is neither valued, nor a decision variable, nor derived by exactly one
       relation, THE validator SHALL report it as under- or over-determined, naming the quantity.
       Gate: tests/test_validate_determinacy.py::test_underdetermined_named

R-004  THE Quantity type SHALL NOT be constructible without a dimension.
       Gate: tests/test_types.py::test_quantity_requires_dimension

R-005  WHEN a Span is validated, THE validator SHALL compare its stored substring against the
       narrative at its offsets and reject a mismatch.
       Gate: tests/test_validate_spans.py::test_span_text_must_match

R-006  IF an emitter encounters a construct it cannot express, THEN THE emitter SHALL raise
       NotRepresentable naming the construct, and SHALL NOT emit a partial model.
       Gate: tests/test_emit_pyomo.py::test_unrepresentable_raises_and_emits_nothing

R-007  THE Pyomo emitter SHALL emit a model whose optimal objective equals the recorded reference
       for every case in the conformance corpus.
       Gate: tests/test_emit_pyomo.py::test_conformance_corpus_objectives

R-008  WHEN two Problems have equal canonical form, THE comparison SHALL report equivalent; when
       they differ, it SHALL report not-proven-equivalent and never proven-different.
       Gate: tests/test_canonical.py::test_verdict_vocabulary

R-009  WHILE a Problem is serialised and deserialised, THE round trip SHALL preserve every field
       including spans and dimensions.
       Gate: tests/test_schema.py::test_roundtrip_is_lossless

R-010  THE JSON schema version SHALL be present in every serialised document.
       Gate: tests/test_schema.py::test_version_present

R-011  IF a document lacks a required field, THEN THE parser SHALL raise a message naming the element
       that lacks it, the field, and the keys it had, and SHALL NOT raise a bare KeyError.
       Gate: tests/test_schema.py::test_a_missing_field_names_its_element_and_the_field
```

R-011 came from reading run ledgers. Expression nodes and relations already said what they lacked,
but a quantity, an assumption, an open question, a span, an objective and the problem itself read
their fields with a bare index, and four records in Enunciado's ledgers carried the string `'span'`
as their whole diagnosis.

## 10. Convergence

Per ADR-0075, implementation ends with a verdict against this document rather than with the absence
of further work.

Recorded for 0.01.000, on 2026-09-22:

| Requirement | Gate | Result |
|---|---|---|
| R-001 to R-011 | as named above | all pass, 65 tests, no skips (0.01.002) |
| The SDD gate itself | `scripts/check_sdd.py` | passes, and catches all four negative controls: a gate naming a missing test, a gate naming a missing file, a requirement with no gate, and a human gate instead of a mechanical one |
| R-007 specifically | HiGHS through Pyomo | solved, objective 900.0 against the analytic optimum, not skipped |

Unmet: nothing in this release's scope. Out of scope and therefore not claimed: the MiniZinc and
OR-Tools emitters, and the dynamics, experiment and learning families. Those have no requirements in
this document and no gates, which is the honest state, rather than requirements marked pending.

## 11. Risks and kill criteria

- **The expression node set is too small for a real family.** Mitigation: it is closed on purpose and
  extended by an explicit design change, not by an escape hatch. Kill criterion: if the optimization
  corpus needs an escape hatch to be representable, the node set is wrong and gets redesigned before
  the next family is added.
- **Dimensional checking is too strict for unit-free textbook problems.** Mitigation: dimensionless is
  a first-class dimension, so those problems are expressible; they just have to say so.
- **Canonical form is too weak to be useful.** Accepted, and bounded by the verdict vocabulary in
  R-008. If the harness finds it useless, isomorphism replaces it there, not here.

## 12. Deploy driver

Not applicable. This is a library: PyPI, trusted publishing, no hosted surface.
