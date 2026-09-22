# Emitters

## The rule

**An emitter is total on the problems it declares it can take, or it raises.**

It never drops a relation it did not understand. A model that solves because a constraint quietly
vanished produces a plausible number, passes every check anyone runs, and is wrong. That failure is
invisible in every output except the one nobody looks at, which is why it is prevented structurally
rather than by care.

`NotRepresentable` names the construct and the element it appeared in:

```
pyomo cannot express the logical connective 'or'
(it needs a disjunctive reformulation or pyomo.gdp) in 'either_pit'; no partial model was emitted
```

"Unsupported" with no subject is not actionable. The construct, the backend and the element are all
in the message, so the caller can choose between reformulating and changing backend.

## Two entry points

`emit_source(problem)` writes a runnable script as text. It needs nothing installed. This is the
artifact a reader checks against the narrative, so it carries the provenance inline:

```python
# tonnes taken from pit A
# from the narrative: "Pit A"
model.x_a = pyo.Var(domain=pyo.Reals, bounds=(0.0, None))  # t
```

`build_model(problem)` builds a live object. It needs the backend installed. The model is assembled
completely before it is returned, so a refusal part-way leaves no half-built object in the caller's
hands.

Both call the validator first and refuse an invalid problem. An emitter that trusted the caller to
have validated would be correct exactly as often as callers remember.

## What Pyomo takes today

Accepted: comparisons with `==`, `<=`, `>=`; sums, products, powers with a rational exponent, indexed
sums; real, integer and binary domains; one or more objectives.

Refused, with the reason in the message: logical connectives (they need a disjunctive reformulation
or `pyomo.gdp`), conditional expressions (big-M or indicator), indexed constraint families (they need
an indexed `Constraint` rule), strict inequalities and `!=` (no solver takes them directly).

Each refusal is a design decision recorded here, not a gap to be quietly filled with an
approximation. A big-M reformulation chosen by the emitter would change the model without the caller
knowing, which is the same failure as dropping a constraint, wearing better clothes.

## Adding an emitter

The interface is fixed: `emit_source(problem) -> str` and `build_model(problem) -> Any`, both
validating first, both total or raising. MiniZinc and OR-Tools are next, and the families beyond
optimization each get their own targets.
