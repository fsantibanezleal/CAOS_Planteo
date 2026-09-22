"""The optimization family's required structure."""

from __future__ import annotations

import dataclasses

from planteo import Role, validate


def test_a_valid_blend_passes_every_check(blend) -> None:
    report = validate(blend)
    assert report.ok, report
    assert not report.errors


def test_an_optimization_problem_needs_an_objective_or_a_feasibility_declaration(blend) -> None:
    stripped = dataclasses.replace(blend, objectives=())
    report = validate(stripped)
    assert not report.ok
    assert any(f.check == "family" for f in report.errors), report

    declared = dataclasses.replace(blend, objectives=(), feasibility_only=True)
    assert validate(declared).ok


def test_declaring_feasibility_while_carrying_an_objective_is_a_contradiction(blend) -> None:
    both = dataclasses.replace(blend, feasibility_only=True)
    report = validate(both)
    assert not report.ok
    assert any(f.check == "family" for f in report.errors), report


def test_an_optimization_problem_needs_a_decision_variable(blend) -> None:
    only_parameters = dataclasses.replace(
        blend,
        quantities=tuple(
            dataclasses.replace(q, role=Role.PARAMETER, value=1.0)
            if q.role is Role.VARIABLE
            else q
            for q in blend.quantities
        ),
    )
    report = validate(only_parameters)
    assert not report.ok
    assert any("decision variable" in f.message for f in report.errors), report


def test_the_report_lists_every_error_rather_than_stopping_at_the_first(blend) -> None:
    from planteo import Dimension, Quantity

    broken = dataclasses.replace(
        blend,
        objectives=(),
        quantities=blend.quantities
        + (
            Quantity(
                name="orphan",
                role=Role.DERIVED,
                dimension=Dimension.of("USD", currency=1),
            ),
        ),
    )
    report = validate(broken)
    checks = {f.check for f in report.errors}
    assert {"family", "determinacy"} <= checks, report
