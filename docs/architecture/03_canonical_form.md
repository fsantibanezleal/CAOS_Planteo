# Canonical form, and why there is no "different" verdict

## The question it answers

Two people formalize the same narrative. One calls the pit tonnages `x_a` and `x_b`, the other calls
them `alpha` and `beta`. One writes `x_a + x_b >= demand`, the other writes `demand <= beta + alpha`.
These are the same model. Nothing in the text of the two documents says so.

Canonical form removes the differences that carry no meaning, so that what is left can be compared.

## What is normalised

**Names.** Quantities are renamed by structural position, not by their given names. The sort key is
everything about a quantity except its name: role, dimension exponents, domain, bounds, value, and
how many times it is referenced. Two quantities that are indistinguishable by all of that are tied,
and the tie is broken by the original name to keep the result deterministic.

That tie-break is the one place where naming still leaks into the form. It is worth knowing which
direction the error can go: a tie broken differently in two documents can produce a false
`NOT_PROVEN_EQUIVALENT`. It can never produce a false `EQUIVALENT`, because the rest of the key still
has to match. The check is conservative in the safe direction.

**Order.** Sum terms and product factors are sorted by their own canonical form, and nested sums are
flattened, so `(x_a) + x_b` and `x_b + x_a` agree.

**Comparator orientation.** `a <= b` and `b >= a` are one constraint written two ways. The sides are
put in a fixed order and the comparator is flipped to match, so both canonicalise identically.

**Provenance is excluded.** Narrative, spans, descriptions and metadata are not content. Two
formalizations of the same narrative that recorded different spans are the same model, and the form
says so.

**Units are included.** A dimension is content, not provenance. The same numbers in different units
are a different model, and the form distinguishes them.

## The verdict vocabulary

```python
class Verdict(str, Enum):
    EQUIVALENT = "equivalent"
    NOT_PROVEN_EQUIVALENT = "not-proven-equivalent"
```

There is deliberately no `DIFFERENT`.

Equality of canonical form **proves** equivalence: the normalisation only ever removes distinctions
that carry no meaning, so two documents that reduce to the same form denote the same model.

Inequality proves **nothing**. Two genuinely equivalent models can canonicalise differently, because
deciding equivalence in general is not something a normaliser does. `x >= 1` and `2x >= 2` are the
same constraint and this form will not say so. It keeps the objective's sense, so maximising `f` and
minimising `-f` come out `NOT_PROVEN_EQUIVALENT` although they are one model. Neither will it
recognise a constraint that has been
substituted through an equality, or a reformulation that is equivalent by an argument rather than by
syntax.

A vocabulary with `DIFFERENT` in it would report all of those as differences, confidently, and be
believed. Naming the weak verdict after what it actually establishes is the difference between a
useful check and a generator of false negatives.

## What this is not

This is not the equivalence oracle. The stronger test in the literature converts a model to a graph
and reduces equivalence to graph isomorphism, using a customised Weisfeiler-Lehman test
([arXiv:2510.27610](https://arxiv.org/abs/2510.27610)), which is reported as giving consistent
verdicts across random parameter configurations where solver-based checking is inconsistent.

That belongs where reference models live, not in the representation. Keeping the boundary explicit
matters more than making this module sound stronger than it is: an overstated check is how a green
result stops meaning anything.

## Using it

```python
from planteo import compare, digest

result = compare(mine, theirs)
result.verdict      # Verdict.EQUIVALENT
result.equivalent   # True
digest(mine)        # a stable 64-character hash of the canonical form
```

The digest is stable across runs and across processes, so it can be stored alongside a formalization
and used later to detect that a model changed without re-reading it.
