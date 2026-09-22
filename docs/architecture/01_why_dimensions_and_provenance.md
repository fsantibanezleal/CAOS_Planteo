# Why dimensions and provenance are not optional

Two things in this representation look like overhead until you know what they are for. Both come from
measured failures rather than from taste.

## The measured problem

Across four separate fields, the check that gets reported is that the artifact **ran**, and the
faithfulness to what was actually asked is lower, sometimes much lower.

| Field | Reported check | Measured faithfulness |
|---|---|---|
| Optimization modelling | the solver reached the reference objective | objective correctness does not imply a correct model; a formulation can reach the right number through compensating errors ([arXiv:2508.10047](https://arxiv.org/abs/2508.10047)) |
| Statement formalization | it compiles | a compile-to-faithfulness gap of 3.0 to 29.0 percentage points; the strongest system measured compiled 89.5% of the time and was semantically faithful 60.5% ([arXiv:2606.31002](https://arxiv.org/abs/2606.31002)) |
| Experiment design | the plan looks complete | every model tested was weak at the layer that binds: datasets, baselines and metrics ([arXiv:2608.03501](https://arxiv.org/abs/2608.03501)) |
| Simulation modelling | the model runs | better at discussion and qualitative work than at causal reasoning and quantitative error fixing ([arXiv:2605.28994](https://arxiv.org/abs/2605.28994)) |

The pattern is one thing seen four times: **executable is not faithful.** A representation that only
has to produce something runnable will sail straight through that gap.

## Dimensions

A quantity in this library cannot exist without a `Dimension`, and `dimensionless` is a dimension
that has to be stated rather than a default that happens when nobody thought about it.

The reason is concrete. On this account, a set of anchor-slice constants expressed as fractions
between 0 and 1 were applied to quantities measured in MW, TWh and metres. Four methods broke. Two of
them had already been published. Nothing in the code looked wrong, because to the code they were all
floats.

Three design consequences follow:

**Comparison is by exponent vector, never by label.** `Dimension.of("t", mass=1)` and
`Dimension.of("kg", mass=1)` are compatible, because they are the same dimension written in different
units. A string comparison of "t" against "kg" would reject a legitimate relation. Conversely `"MW"`
and `"TWh"` differ in the time exponent, and that is caught whatever they are called.

**Exponents are rational, not integer.** A square root of a dimensioned quantity is ordinary in
engineering relations, so `Fraction` is the type and `m^1/2` is representable.

**Sums are checked, products are not.** Adding metres to seconds is meaningless and is rejected.
Multiplying them is a velocity's reciprocal and is fine. The checker has to be strict in exactly one
of those places, and a checker that over-rejects gets switched off, which is worse than no checker.

```python
speed = Dimension.of("m/s", length=1, time=-1)
duration = Dimension.of("s", time=1)
(speed * duration).compatible_with(Dimension.of("m", length=1))   # True
```

## Provenance

Every element carries a `Span`: the character offsets into the narrative **and the text they
covered**.

The redundancy is the point. Offsets alone always point somewhere. If the narrative is edited, they
point at something else and nothing complains. The stored text is what turns a silent drift into a
rejection:

```python
span = Span.find(narrative, "12 USD per tonne")
span.verify(edited_narrative)   # SpanError: recorded '12 USD per tonne', narrative now holds '21 USD per tonne'
```

The `Narrative` also carries a digest, so a document deserialised against a changed source is
refused outright rather than validated span by span against text that has moved underneath it.

An element with no span is allowed and it means something specific: `Span.inferred(reason)` states
that this was not read from the text, and why. That is different from "we did not record it", and
the difference is exactly what a reviewer needs to see.

## Open questions

The third piece, which none of the representations in the surveyed work carries.

When a narrative does not determine something, a formalizer has to choose. The choice is usually
reasonable and it is always invisible: nothing in the resulting model says that "minimise the total
cost" was read as excluding haulage. `OpenQuestion` records the question, the span that raised it,
the resolution taken and the quantities it affects.

An unresolved question is a validator warning rather than an error, because a conditional
formalization is a legitimate state, and it is reproduced in the emitted model source so it survives
into the artifact a reader actually looks at.

```python
# [OPEN] does the total cost include haulage, or only the pit price
```

That comment is the difference between a model that is wrong and a model that is wrong **and says
where to look**.
