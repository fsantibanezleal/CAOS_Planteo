"""The dynamics family: R-101 to R-110 (docs/design/features/dynamics/requirements.md).

The fixture is a mixing tank with a closed-form answer. 100 L of brine hold 2 kg of salt; brine at
0.4 kg/L flows in at 5 L/min and the mixed solution drains at 5 L/min, so the volume stays at 100 L
and the salt follows x(t) = 40 - 38 exp(-t/20). After 20 minutes that is 40 - 38/e = 26.0207 kg.
"""

from __future__ import annotations

import dataclasses
import json
import math
from fractions import Fraction

import pytest

from planteo import (
    Comparator,
    Compare,
    Conditional,
    Constant,
    Dimension,
    Family,
    Logical,
    Narrative,
    NotEvaluable,
    Objective,
    Power,
    Problem,
    Product,
    Quantity,
    Query,
    Rate,
    Ref,
    Role,
    Sense,
    Sum,
    canonical_form,
    evaluate,
    holds,
    system,
    validate,
)
from planteo.expressions import BigSum

KG = Dimension.of("kg", mass=1)
LITRE = Dimension.of("L", length=3)
MINUTE = Dimension.of("min", time=1)
CONCENTRATION = Dimension.of("kg/L", mass=1, length=-3)
FLOW = Dimension.of("L/min", length=3, time=-1)
NONE = Dimension.dimensionless()

TEXT = (
    "A tank holds 100 L of brine containing 2 kg of salt. Brine with 0.4 kg of salt per litre flows "
    "in at 5 L/min, and the mixed solution drains at the same rate. How much salt is in the tank "
    "after 20 minutes?"
)
ANALYTIC = 40 - 38 * math.exp(-1)


def _inflow_minus_outflow(coefficient: float = -1.0):
    return Sum(
        (
            Product((Ref("c_in"), Ref("q"))),
            Product((Constant(coefficient, NONE), Ref("x"), Power(Ref("V"), Fraction(-1)), Ref("q"))),
        )
    )


def tank(**overrides) -> Problem:
    base = dict(
        narrative=Narrative(TEXT),
        family=Family.DYNAMICS,
        quantities=(
            Quantity("t", Role.INDEPENDENT, MINUTE, lower=0.0, upper=30.0),
            Quantity("x", Role.STATE, KG, value=2.0),
            Quantity("V", Role.PARAMETER, LITRE, value=100.0),
            Quantity("c_in", Role.PARAMETER, CONCENTRATION, value=0.4),
            Quantity("q", Role.PARAMETER, FLOW, value=5.0),
        ),
        relations=(Rate("x", "t", _inflow_minus_outflow(), name="salt_balance"),),
        queries=(Query(Ref("x"), 20.0, name="salt_after_20_min"),),
    )
    base.update(overrides)
    return Problem(**base)  # type: ignore[arg-type]


def _messages(problem: Problem) -> list[str]:
    return [str(f) for f in validate(problem).errors]


def test_a_dynamics_problem_round_trips() -> None:
    """R-101."""
    problem = tank()
    assert validate(problem).ok, _messages(problem)
    again = Problem.from_json(json.loads(json.dumps(problem.to_json())))
    assert again == problem


def test_a_rate_with_the_wrong_dimension_is_rejected() -> None:
    """R-102: kilograms where kilograms per minute are due, named by the rate."""
    wrong = Rate("x", "t", Product((Ref("c_in"), Ref("V"))), name="salt_balance")
    messages = _messages(tank(relations=(wrong,)))
    assert any("dimensions [salt_balance]" in m and "d(x)/d(t)" in m for m in messages), messages


def test_every_state_needs_one_rate_and_an_initial_value() -> None:
    """R-103."""
    assert any("[x]: has no rate" in m for m in _messages(tank(relations=())))
    twice = (Rate("x", "t", _inflow_minus_outflow()), Rate("x", "t", _inflow_minus_outflow(-2.0)))
    assert any("[x]: has 2 rates" in m for m in _messages(tank(relations=twice)))
    no_start = tuple(dataclasses.replace(q, value=None) if q.name == "x" else q for q in tank().quantities)
    assert any("[x]: is a state with no initial value" in m for m in _messages(tank(quantities=no_start)))


def test_the_independent_variable_is_one_and_bounded() -> None:
    """R-104."""
    without = tuple(q for q in tank().quantities if q.name != "t")
    assert any("exactly one independent variable, and has 0" in m for m in _messages(tank(quantities=without)))
    twice = (*tank().quantities, Quantity("s", Role.INDEPENDENT, MINUTE, lower=0.0, upper=1.0))
    assert any("exactly one independent variable, and has 2" in m for m in _messages(tank(quantities=twice)))
    open_ended = tuple(dataclasses.replace(q, upper=None) if q.name == "t" else q for q in tank().quantities)
    assert any("needs both bounds" in m for m in _messages(tank(quantities=open_ended)))


def test_a_query_must_exist_and_be_in_range() -> None:
    """R-105."""
    assert any("needs at least one query" in m for m in _messages(tank(queries=())))
    late = (Query(Ref("x"), 40.0, name="too_late"),)
    assert any("[too_late]: asks at 40.0, outside the range 0.0 to 30.0" in m for m in _messages(tank(queries=late)))


def test_the_families_do_not_mix() -> None:
    """R-106."""
    as_optimization = tank(family=Family.OPTIMIZATION, objectives=(Objective(Sense.MINIMISE, Ref("x")),))
    messages = _messages(as_optimization)
    for expected in ("cannot carry a rate", "cannot carry a query", "cannot have a state quantity", "cannot have a independent quantity"):
        assert any(expected in m for m in messages), (expected, messages)

    objective = tank(objectives=(Objective(Sense.MINIMISE, Ref("x")),))
    assert any("a dynamics problem has no objective" in m for m in _messages(objective))
    decision = tank(quantities=(*tank().quantities, Quantity("u", Role.VARIABLE, KG)))
    assert any("[u]: a dynamics problem has states, not decision variables" in m for m in _messages(decision))
    bound = Compare(Ref("x"), Comparator.LE, Constant(50.0, KG), name="cap")
    inequality = tank(relations=(*tank().relations, bound))
    assert any("[cap]: a dynamics problem has no inequality" in m for m in _messages(inequality))


def test_the_dynamics_canonical_form() -> None:
    """R-107: renaming and reordering change nothing; a rate's coefficient changes the form."""
    reference = canonical_form(tank())
    renamed = tank(
        quantities=tuple(reversed(tank().quantities)),
        relations=(Rate("x", "t", _inflow_minus_outflow()),),
    )
    assert canonical_form(renamed) == reference
    other = tank(relations=(Rate("x", "t", _inflow_minus_outflow(-2.0)),))
    assert canonical_form(other) != reference
    assert "queries" in reference


def test_the_evaluator_covers_the_node_set() -> None:
    """R-108."""
    values = {"a": 2.0, "b": 3.0}
    assert evaluate(Constant(1.5, NONE), values) == 1.5
    assert evaluate(Ref("a"), values) == 2.0
    assert evaluate(Sum((Ref("a"), Ref("b"))), values) == 5.0
    assert evaluate(Product((Ref("a"), Ref("b"))), values) == 6.0
    assert evaluate(Power(Ref("b"), Fraction(1, 2)), values) == pytest.approx(math.sqrt(3))
    below = Compare(Ref("a"), Comparator.LT, Ref("b"))
    assert evaluate(Conditional(below, Ref("a"), Ref("b")), values) == 2.0
    both = Logical("and", (below, Compare(Ref("b"), Comparator.GE, Constant(3.0, NONE))))
    assert holds(both, values) and not holds(Logical("not", (both,)), values)
    with pytest.raises(NotEvaluable, match="indexed sum"):
        evaluate(BigSum("i", "items", Ref("a")), values)
    with pytest.raises(ArithmeticError):
        evaluate(Power(Constant(-1.0, NONE), Fraction(1, 2)), values)


def test_the_emitted_source_agrees_with_the_evaluator() -> None:
    """R-109: both reach the analytic answer, and each other, through solve_ivp."""
    scipy_integrate = pytest.importorskip("scipy.integrate")
    from planteo.emit.scipy import emit_source

    problem = tank()
    namespace: dict = {}
    exec(compile(emit_source(problem), "emitted", "exec"), namespace)  # noqa: S102, the emitted module
    built = system(problem)

    def at_20(rhs, y0, t_span, query):
        solution = scipy_integrate.solve_ivp(rhs, t_span, y0, dense_output=True, rtol=1e-10, atol=1e-12)
        return query(20.0, solution.sol(20.0))

    emitted = at_20(namespace["rhs"], namespace["Y0"], namespace["T_SPAN"], namespace["QUERIES"][0][2])
    evaluated = at_20(built.rhs, list(built.y0), built.t_span, built.queries["salt_after_20_min"][1])
    assert emitted == pytest.approx(evaluated, rel=1e-9)
    assert evaluated == pytest.approx(ANALYTIC, rel=1e-7)


def test_a_schema_1_0_document_still_loads(blend) -> None:
    """R-110: written at 1.1; an optimization document from before the family loads unchanged."""
    assert tank().to_json()["schema_version"] == "1.1"
    old = blend.to_json()
    old["schema_version"] = "1.0"
    del old["queries"]
    assert Problem.from_json(old) == blend
