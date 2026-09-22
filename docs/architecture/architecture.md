# Architecture

The representation, in the order it is worth reading.

1. [Why dimensions and provenance are not optional](01_why_dimensions_and_provenance.md), the
   measured failures the two core commitments come from.
2. [The validator](02_validation.md), the five checks, their order, and why severity is assigned the
   way it is.
3. [Canonical form](03_canonical_form.md), what is normalised, and why there is no "different"
   verdict.
4. [Emitters](04_emitters.md), the totality-or-refusal rule.

## The shape in one picture

```
narrative text
   |
   |  (a harness reads it; not this library)
   v
Problem ......... quantities (dimensioned) + relations + objectives
   |              + assumptions + open questions, each with a span
   |
   +--> validate() ......... names, closure, spans, dimensions,
   |                         determinacy, family, open questions
   |
   +--> canonical_form() ... compare two formalizations
   |
   +--> emit.pyomo ......... a runnable model, or NotRepresentable
```

Nothing in the library calls a language model, opens a network connection, or solves anything.
