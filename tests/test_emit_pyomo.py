"""Gates for R-006 and R-007."""

from __future__ import annotations

import dataclasses

import pytest

from planteo import (
    Comparator,
    Compare,
    Constant,
    Dimension,
    Logical,
    Quantity,
    Ref,
    Role,
    ValidationError,
)
from planteo.emit import NotRepresentable
from planteo.emit import pyomo as emit_pyomo

pyomo = pytest.importorskip("pyomo.environ", reason="the pyomo extra is not installed")

TONNE = Dimension.of("t", mass=1)


def test_conformance_corpus_objectives(blend) -> None:
    """R-007: the emitted model reaches the recorded reference optimum.

    The blend case is a two-variable LP whose optimum is analytic: take the whole demand from the
    cheaper pit, so 100 t at 9 USD/t, which is 900 USD.
    """
    model = emit_pyomo.build_model(blend)
    solver = pyomo.SolverFactory("appsi_highs")
    if not solver.available(exception_flag=False):
        pytest.skip("no HiGHS available in this environment")
    solver.solve(model)
    assert pyomo.value(model.total_cost) == pytest.approx(900.0, rel=1e-9)
    assert pyomo.value(model.x_b) == pytest.approx(100.0, rel=1e-9)


def test_unrepresentable_raises_and_emits_nothing(blend) -> None:
    """R-006: an inexpressible construct raises, naming it, and yields no partial model."""
    disjunction = Logical(
        connective="or",
        operands=(
            Compare(
                left=Ref("x_a"), comparator=Comparator.GE, right=Constant(50.0, TONNE)
            ),
            Compare(
                left=Ref("x_b"), comparator=Comparator.GE, right=Constant(50.0, TONNE)
            ),
        ),
        name="either_pit",
    )
    problem = dataclasses.replace(blend, relations=blend.relations + (disjunction,))

    with pytest.raises(NotRepresentable) as caught:
        emit_pyomo.build_model(problem)
    assert "either_pit" in str(caught.value)
    assert "no partial model" in str(caught.value)

    with pytest.raises(NotRepresentable):
        emit_pyomo.emit_source(problem)


def test_an_invalid_problem_is_refused_rather_than_emitted(blend) -> None:
    broken = dataclasses.replace(
        blend,
        quantities=blend.quantities
        + (
            Quantity(
                name="orphan",
                role=Role.DERIVED,
                dimension=Dimension.of("USD", currency=1),
            ),
        ),
    )
    with pytest.raises(ValidationError):
        emit_pyomo.emit_source(broken)


def test_the_emitted_source_carries_the_provenance(blend) -> None:
    source = emit_pyomo.emit_source(blend)
    assert 'from the narrative: "12 USD per tonne"' in source
    assert "model.x_a = pyo.Var" in source
    assert "sense=pyo.minimize" in source
    # The unit is carried as a comment so a reader can check it against the text.
    assert "# t" in source


def test_the_emitted_source_runs_and_agrees_with_the_built_model(blend, tmp_path) -> None:
    source = emit_pyomo.emit_source(blend)
    namespace: dict[str, object] = {}
    exec(compile(source, "<emitted>", "exec"), namespace)  # noqa: S102, the point of the test
    emitted = namespace["model"]
    built = emit_pyomo.build_model(blend)
    assert sorted(c.name for c in emitted.component_objects(pyomo.Var)) == sorted(
        c.name for c in built.component_objects(pyomo.Var)
    )


def test_an_open_question_is_surfaced_in_the_emitted_source(blend) -> None:
    from planteo import OpenQuestion, Span

    question = OpenQuestion(
        question="does the total cost include haulage",
        span=Span.find(blend.narrative, "Minimise the total cost"),
    )
    problem = dataclasses.replace(blend, open_questions=(question,))
    source = emit_pyomo.emit_source(problem)
    assert "[OPEN] does the total cost include haulage" in source
