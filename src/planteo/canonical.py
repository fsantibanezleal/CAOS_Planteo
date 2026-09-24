"""Canonical form, and an honest verdict vocabulary.

Two formalizations of the same narrative can differ in every name and every ordering and still be
the same model. Canonicalising removes the differences that do not matter (names, term order, which
side of a comparator a term sits on) so that what remains can be compared.

**What this is not.** Equality of canonical form proves equivalence. Inequality proves nothing: two
genuinely equivalent models can canonicalise differently, because deciding equivalence in general is
not something a normaliser does. So the verdicts are ``EQUIVALENT`` and ``NOT_PROVEN_EQUIVALENT``,
and there is deliberately no ``DIFFERENT``. Naming the weak verdict after what it actually
establishes is the difference between a useful check and one that produces confident false negatives.

The stronger test, graph isomorphism over the model structure, belongs where reference models live,
not here. The boundary is stated rather than blurred.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .expressions import (
    BigSum,
    Conditional,
    Constant,
    Expression,
    Power,
    Product,
    Ref,
    Sum,
    flatten_factors,
    flatten_terms,
)
from .problem import Problem, Quantity
from .relations import Compare, ForAll, Logical, Objective, Rate, Relation


class Verdict(str, Enum):
    EQUIVALENT = "equivalent"
    NOT_PROVEN_EQUIVALENT = "not-proven-equivalent"


@dataclass(frozen=True, slots=True)
class Comparison:
    verdict: Verdict
    left_digest: str
    right_digest: str

    @property
    def equivalent(self) -> bool:
        return self.verdict is Verdict.EQUIVALENT


def canonical_form(problem: Problem) -> dict[str, Any]:
    """A name-independent, order-independent form of the problem's mathematical content.

    Narrative, spans, descriptions and metadata are excluded on purpose: they are provenance, not
    content, and two formalizations of the same narrative should compare equal whatever they recorded
    about where they came from.
    """
    renaming = _canonical_names(problem)
    quantities = sorted(
        (_canonical_quantity(q, renaming) for q in problem.quantities),
        key=lambda item: json.dumps(item, sort_keys=True),
    )
    relations = sorted(
        (_canonical_relation(r, renaming) for r in problem.relations),
        key=lambda item: json.dumps(item, sort_keys=True),
    )
    objectives = sorted(
        (_canonical_objective(o, renaming) for o in problem.objectives),
        key=lambda item: json.dumps(item, sort_keys=True),
    )
    form = {
        "family": problem.family.value,
        "feasibility_only": problem.feasibility_only,
        "quantities": quantities,
        "relations": relations,
        "objectives": objectives,
    }
    # Only a problem with queries gains the key, so every form computed before the dynamics family
    # existed is unchanged.
    if problem.queries:
        form["queries"] = sorted(
            (
                {"expression": _canonical_expression(q.expression, renaming), "at": q.at}
                for q in problem.queries
            ),
            key=lambda item: json.dumps(item, sort_keys=True),
        )
    return form


def digest(problem: Problem) -> str:
    """A stable hash of the canonical form."""
    payload = json.dumps(canonical_form(problem), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compare(left: Problem, right: Problem) -> Comparison:
    """Compare two problems. See the module docstring for what a negative verdict means."""
    left_digest, right_digest = digest(left), digest(right)
    verdict = (
        Verdict.EQUIVALENT
        if left_digest == right_digest
        else Verdict.NOT_PROVEN_EQUIVALENT
    )
    return Comparison(verdict, left_digest, right_digest)


# -- canonical naming --------------------------------------------------------------------


def _canonical_names(problem: Problem) -> dict[str, str]:
    """Rename quantities by structural position, not by their given names.

    The sort key is everything about a quantity except its name: role, dimension, domain, bounds,
    value, and how often it is referenced. Two quantities that are indistinguishable by all of that
    are tied, and the tie is broken by the original name so the result stays deterministic. A tie
    that is broken by name is the one place where naming still leaks into the form, and it can only
    produce a false NOT_PROVEN_EQUIVALENT, never a false EQUIVALENT.
    """
    usage: dict[str, int] = {}
    for relation in _walk_relations(problem.relations):
        for name in relation.references():
            usage[name] = usage.get(name, 0) + 1
    for objective in problem.objectives:
        for name in objective.references():
            usage[name] = usage.get(name, 0) + 1
    for query in problem.queries:
        for name in query.references():
            usage[name] = usage.get(name, 0) + 1

    def key(quantity: Quantity) -> tuple:
        return (
            quantity.role.value,
            tuple(str(e) for e in quantity.dimension.exponents),
            quantity.domain.value,
            _sortable(quantity.lower),
            _sortable(quantity.upper),
            _sortable(quantity.value),
            -usage.get(quantity.name, 0),
            quantity.name,
        )

    ordered = sorted(problem.quantities, key=key)
    return {quantity.name: f"q{index}" for index, quantity in enumerate(ordered)}


def _sortable(value: float | None) -> tuple[int, float]:
    return (0, 0.0) if value is None else (1, float(value))


def _canonical_quantity(quantity: Quantity, renaming: dict[str, str]) -> dict[str, Any]:
    return {
        "name": renaming[quantity.name],
        "role": quantity.role.value,
        "dimension": [str(e) for e in quantity.dimension.exponents],
        "domain": quantity.domain.value,
        "lower": quantity.lower,
        "upper": quantity.upper,
        "value": quantity.value,
    }


# -- canonical relations ------------------------------------------------------------------


def _canonical_relation(relation: Relation, renaming: dict[str, str]) -> dict[str, Any]:
    if isinstance(relation, Compare):
        left = _canonical_expression(relation.left, renaming)
        right = _canonical_expression(relation.right, renaming)
        comparator = relation.comparator
        # Orient the comparator so the two sides are in a fixed order. `a <= b` and `b >= a` are the
        # same constraint written twice, and the form must not distinguish them.
        left_key = json.dumps(left, sort_keys=True)
        right_key = json.dumps(right, sort_keys=True)
        if left_key > right_key:
            left, right = right, left
            comparator = comparator.flipped
        return {
            "tag": "compare",
            "comparator": comparator.value,
            "left": left,
            "right": right,
        }
    if isinstance(relation, Logical):
        operands = [_canonical_relation(o, renaming) for o in relation.operands]
        if relation.connective in {"and", "or"}:
            operands.sort(key=lambda item: json.dumps(item, sort_keys=True))
        return {
            "tag": "logical",
            "connective": relation.connective,
            "operands": operands,
        }
    if isinstance(relation, ForAll):
        # The bound index is renamed positionally so two spellings of the same family agree.
        inner = dict(renaming)
        inner[relation.index] = "i0"
        return {
            "tag": "forall",
            "index_set": renaming.get(relation.index_set, relation.index_set),
            "body": _canonical_relation(relation.body, inner),
        }
    if isinstance(relation, Rate):
        return {
            "tag": "rate",
            "state": renaming.get(relation.state, relation.state),
            "wrt": renaming.get(relation.wrt, relation.wrt),
            "expression": _canonical_expression(relation.expression, renaming),
        }
    raise ValueError(f"cannot canonicalise relation node {relation.tag!r}")


def _canonical_objective(objective: Objective, renaming: dict[str, str]) -> dict[str, Any]:
    return {
        "sense": objective.sense.value,
        "expression": _canonical_expression(objective.expression, renaming),
    }


def _canonical_expression(expression: Expression, renaming: dict[str, str]) -> dict[str, Any]:
    if isinstance(expression, Constant):
        return {
            "tag": "const",
            "value": expression.value,
            "dimension": [str(e) for e in expression.unit.exponents],
        }
    if isinstance(expression, Ref):
        return {"tag": "ref", "name": renaming.get(expression.name, expression.name)}
    if isinstance(expression, Sum):
        terms = [
            _canonical_expression(t, renaming) for t in flatten_terms(expression.terms)
        ]
        terms.sort(key=lambda item: json.dumps(item, sort_keys=True))
        return {"tag": "sum", "terms": terms}
    if isinstance(expression, Product):
        factors = [_canonical_expression(f, renaming) for f in flatten_factors(expression.factors)]
        factors.sort(key=lambda item: json.dumps(item, sort_keys=True))
        return {"tag": "product", "factors": factors}
    if isinstance(expression, Power):
        return {
            "tag": "power",
            "base": _canonical_expression(expression.base, renaming),
            "exponent": str(expression.exponent),
        }
    if isinstance(expression, BigSum):
        inner = dict(renaming)
        inner[expression.index] = "i0"
        return {
            "tag": "bigsum",
            "index_set": renaming.get(expression.index_set, expression.index_set),
            "body": _canonical_expression(expression.body, inner),
        }
    if isinstance(expression, Conditional):
        return {
            "tag": "conditional",
            "when": _canonical_relation(expression.when, renaming),
            "then": _canonical_expression(expression.then, renaming),
            "otherwise": _canonical_expression(expression.otherwise, renaming),
        }
    raise ValueError(f"cannot canonicalise expression node {expression.tag!r}")


def _walk_relations(relations):
    for relation in relations:
        yield relation
        if isinstance(relation, Logical):
            yield from _walk_relations(relation.operands)
        elif isinstance(relation, ForAll):
            yield from _walk_relations([relation.body])
