# Guide: build a problem

A worked example, from a sentence to a solved model.

## The narrative

> A plant blends ore from two pits. Pit A costs 12 USD per tonne and pit B costs 9 USD per tonne.
> Together they must deliver at least 100 tonnes. Minimise the total cost.

## 1. Hold the text

```python
from planteo import Narrative

text = Narrative(
    "A plant blends ore from two pits. Pit A costs 12 USD per tonne and pit B "
    "costs 9 USD per tonne. Together they must deliver at least 100 tonnes. "
    "Minimise the total cost."
)
```

The `Narrative` carries a digest, so a document stored against this text can later detect that the
text changed.

## 2. Name the dimensions before the quantities

```python
from planteo import Dimension

TONNE = Dimension.of("t", mass=1)
PER_TONNE = Dimension.of("USD/t", currency=1, mass=-1)
```

Writing the units first is a habit worth having: `PER_TONNE` is currency divided by mass, and getting
that wrong here is caught the moment it meets a relation, rather than in a number nobody questions.

## 3. Declare the quantities, with their provenance

```python
from planteo import Quantity, Role, Span

quantities = (
    Quantity("x_a", Role.VARIABLE, TONNE, lower=0.0,
             description="tonnes taken from pit A",
             span=Span.find(text, "Pit A")),
    Quantity("x_b", Role.VARIABLE, TONNE, lower=0.0,
             description="tonnes taken from pit B",
             span=Span.find(text, "pit B")),
    Quantity("c_a", Role.PARAMETER, PER_TONNE, value=12.0,
             span=Span.find(text, "12 USD per tonne")),
    Quantity("c_b", Role.PARAMETER, PER_TONNE, value=9.0,
             span=Span.find(text, "9 USD per tonne")),
    Quantity("demand", Role.PARAMETER, TONNE, value=100.0,
             span=Span.find(text, "at least 100 tonnes")),
)
```

`Span.find` raises if the phrase is absent, so a typo becomes an error here rather than a wrong
provenance comment later.

If something was not read from the text, say so:

```python
Span.inferred("the narrative never states a lower bound; non-negativity assumed")
```

## 4. Write the relations and the objective

```python
from planteo import Comparator, Compare, Objective, Product, Ref, Sense, Sum

relations = (
    Compare(Sum((Ref("x_a"), Ref("x_b"))), Comparator.GE, Ref("demand"),
            name="meet_demand", span=Span.find(text, "must deliver at least 100 tonnes")),
)

objectives = (
    Objective(Sense.MINIMISE,
              Sum((Product((Ref("c_a"), Ref("x_a"))),
                   Product((Ref("c_b"), Ref("x_b"))))),
              name="total_cost", span=Span.find(text, "Minimise the total cost")),
)
```

Note the objective's dimension: USD/t times t is USD, twice, summed. If you had written
`Sum((Ref("c_a"), Ref("x_a")))` by mistake, the validator would reject it as USD/t added to t.

## 5. Record what the narrative did not say

```python
from planteo import OpenQuestion

questions = (
    OpenQuestion(
        question="does the total cost include haulage, or only the pit price",
        span=Span.find(text, "Minimise the total cost"),
        resolution="pit price only; haulage is out of scope for this statement",
        affects=("total_cost",),
    ),
)
```

Leave `resolution` empty and the question stays open: a warning from the validator, and an `[OPEN]`
marker in the emitted model.

## 6. Assemble and validate

```python
from planteo import Family, Problem, validate

problem = Problem(narrative=text, family=Family.OPTIMIZATION,
                  quantities=quantities, relations=relations,
                  objectives=objectives, open_questions=questions)

report = validate(problem)
assert report.ok, report
```

## 7. Emit and solve

```python
from planteo.emit import pyomo as emit
import pyomo.environ as pyo

print(emit.emit_source(problem))     # read this against the narrative

model = emit.build_model(problem)
pyo.SolverFactory("appsi_highs").solve(model)
print(pyo.value(model.total_cost))   # 900.0
```

900 USD: the whole demand from the cheaper pit. Which is what the sentence said.
