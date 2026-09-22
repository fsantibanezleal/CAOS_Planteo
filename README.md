# planteo

[![PyPI](https://img.shields.io/pypi/v/planteo.svg)](https://pypi.org/project/planteo/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A typed representation for a problem **after it has been read and before it is solved**.

A narrative problem statement is ambiguous, under-specified and unit-bearing. Turning it into a
solver model is usually done by writing code straight from the text, and that loses the two things
that decide whether the result is right: **which words produced which symbol**, and **what the words
did not say**.

`planteo` holds the object in between. It does not read natural language and it does not solve
anything. It defines the object, checks it, and emits it.

## Why this exists

Across four different fields, the reported check is that the artifact **ran**, and the measured
faithfulness is much lower:

| Field | What gets reported | What was measured |
|---|---|---|
| Optimization modelling | the solver reached the reference objective | objective correctness does not imply a correct model; compensating errors pass ([survey](https://arxiv.org/abs/2508.10047)) |
| Statement formalization | it compiles | a 3.0 to 29.0 point compile-to-faithfulness gap; the strongest agent compiled 89.5% and was faithful 60.5% ([study](https://arxiv.org/abs/2606.31002)) |
| Experiment design | the plan looks complete | every model tested is weak at datasets, baselines and metrics ([benchmark](https://arxiv.org/abs/2608.03501)) |
| Simulation modelling | the model runs | tools do well at qualitative work, badly at causal reasoning and quantitative fixes ([benchmark](https://arxiv.org/abs/2605.28994)) |

A model that runs is not a model that is right. This package makes the difference inspectable.

## The two design commitments

**Every quantity carries a dimension.** Not optional, and dimensionless is a dimension that must be
stated. Adding metres to seconds is rejected before a solver ever sees it, and a unit is compared by
its exponent vector rather than by its label, so tonnes and kilograms are compatible while a
string comparison would say otherwise.

**Every element carries its provenance.** A `Span` records the offsets *and* the text it covered, so
a document that has been stored or moved can be checked against its narrative rather than trusted. An
element with no span states that it was inferred, and why.

And one thing no surveyed representation carries: **`open_questions`**. When the narrative does not
determine something, the question is recorded with the span that raised it and the choice that was
taken, instead of being silently resolved.

## Install

```bash
pip install planteo               # the representation, zero dependencies
pip install "planteo[pyomo]"      # plus the Pyomo emitter
```

## Use

```python
from planteo import (
    Comparator, Compare, Dimension, Domain, Family, Narrative,
    Objective, Problem, Product, Quantity, Ref, Role, Sense, Span, Sum, validate,
)

text = Narrative(
    "A plant blends ore from two pits. Pit A costs 12 USD per tonne and pit B "
    "costs 9 USD per tonne. Together they must deliver at least 100 tonnes. "
    "Minimise the total cost."
)

TONNE = Dimension.of("t", mass=1)
PER_TONNE = Dimension.of("USD/t", currency=1, mass=-1)

problem = Problem(
    narrative=text,
    family=Family.OPTIMIZATION,
    quantities=(
        Quantity("x_a", Role.VARIABLE, TONNE, lower=0.0, span=Span.find(text, "Pit A")),
        Quantity("x_b", Role.VARIABLE, TONNE, lower=0.0, span=Span.find(text, "pit B")),
        Quantity("c_a", Role.PARAMETER, PER_TONNE, value=12.0),
        Quantity("c_b", Role.PARAMETER, PER_TONNE, value=9.0),
        Quantity("demand", Role.PARAMETER, TONNE, value=100.0),
    ),
    relations=(
        Compare(Sum((Ref("x_a"), Ref("x_b"))), Comparator.GE, Ref("demand"), name="meet_demand"),
    ),
    objectives=(
        Objective(Sense.MINIMISE, Sum((
            Product((Ref("c_a"), Ref("x_a"))),
            Product((Ref("c_b"), Ref("x_b"))),
        )), name="total_cost"),
    ),
)

report = validate(problem)
assert report.ok, report
```

Emit it:

```python
from planteo.emit import pyomo as emit

print(emit.emit_source(problem))   # a runnable Pyomo script, with provenance comments
model = emit.build_model(problem)  # or a live ConcreteModel
```

The emitted source carries the narrative alongside the code, so a reader can check the formalization
against the words:

```python
# tonnes taken from pit A
# from the narrative: "Pit A"
model.x_a = pyo.Var(domain=pyo.Reals, bounds=(0.0, None))  # t
```

Compare two formalizations:

```python
from planteo import compare

compare(mine, yours).verdict   # Verdict.EQUIVALENT | Verdict.NOT_PROVEN_EQUIVALENT
```

There is deliberately no `DIFFERENT` verdict. Equal canonical form proves equivalence; unequal
canonical form proves nothing, and a vocabulary that pretended otherwise would produce confident
false negatives.

## What it validates

1. **Dimensions.** Every relation is checked term by term; both sides of a comparator must agree.
2. **Closure.** No free symbol.
3. **Determinacy.** Every quantity is given, chosen, derived by exactly one relation, or observed.
4. **Span integrity.** Every span still covers the text it recorded.
5. **Family completeness.** The family's required structure is present.

The validator reports every finding rather than stopping at the first, and each finding names the
element it is about.

## What it is not

- Not a translator. Producing a `Problem` from text is the job of a harness; this defines the target.
- Not a solver or a solver wrapper.
- Not a modelling language. It emits to Pyomo and MiniZinc rather than competing with them.
- Not an equivalence oracle. See the verdict vocabulary above.

## Documentation

The wiki is in [`docs/`](docs/). The design document that governs this package, written before any
code, is [`docs/design/SDD.md`](docs/design/SDD.md); every requirement in it names the test that
verifies it.

## License

MIT. See [LICENSE](LICENSE).
