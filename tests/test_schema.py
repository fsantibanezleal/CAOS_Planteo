"""Gates for R-009 and R-010."""

from __future__ import annotations

import json

import pytest

from planteo import SCHEMA_VERSION, Problem, validate


def test_version_present(blend) -> None:
    """R-010: every serialised document carries its schema version."""
    assert blend.to_json()["schema_version"] == SCHEMA_VERSION


def test_roundtrip_is_lossless(blend) -> None:
    """R-009: serialise and deserialise preserves every field, spans and dimensions included."""
    payload = json.loads(json.dumps(blend.to_json()))
    restored = Problem.from_json(payload)

    assert restored.to_json() == blend.to_json()
    assert restored.narrative.text == blend.narrative.text
    assert [q.name for q in restored.quantities] == [q.name for q in blend.quantities]

    for before, after in zip(blend.quantities, restored.quantities, strict=True):
        assert after.dimension.exponents == before.dimension.exponents
        assert after.dimension.symbol == before.dimension.symbol
        assert (after.span is None) == (before.span is None)
        if before.span is not None:
            assert after.span.text == before.span.text
            assert after.span.start == before.span.start

    assert validate(restored).ok


def test_a_foreign_schema_version_is_refused_rather_than_guessed(blend) -> None:
    payload = blend.to_json()
    payload["schema_version"] = "0.9"
    with pytest.raises(ValueError) as caught:
        Problem.from_json(payload)
    assert "0.9" in str(caught.value)


def test_an_unknown_node_tag_is_refused(blend) -> None:
    payload = blend.to_json()
    payload["relations"][0]["left"]["tag"] = "matrix_inverse"
    with pytest.raises(ValueError) as caught:
        Problem.from_json(payload)
    assert "closed" in str(caught.value)


def test_open_questions_survive_the_round_trip(blend) -> None:
    import dataclasses

    from planteo import OpenQuestion, Span

    question = OpenQuestion(
        question="does the total cost include haulage, or only the pit price",
        span=Span.find(blend.narrative, "Minimise the total cost"),
        resolution="pit price only; haulage is out of scope for this statement",
        affects=("total_cost",),
    )
    with_question = dataclasses.replace(blend, open_questions=(question,))
    restored = Problem.from_json(json.loads(json.dumps(with_question.to_json())))
    assert restored.open_questions[0].question == question.question
    assert restored.open_questions[0].affects == ("total_cost",)
    assert not restored.open_questions[0].is_open


def test_an_unresolved_question_is_surfaced_as_a_warning(blend) -> None:
    import dataclasses

    from planteo import OpenQuestion, Span

    question = OpenQuestion(
        question="are partial tonnes allowed",
        span=Span.find(blend.narrative, "at least 100 tonnes"),
    )
    problem = dataclasses.replace(blend, open_questions=(question,))
    report = validate(problem)
    assert report.ok
    assert any(f.check == "open-questions" for f in report.warnings), report
