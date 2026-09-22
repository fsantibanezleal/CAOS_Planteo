"""Gate for R-005."""

from __future__ import annotations

import dataclasses

import pytest

from planteo import Narrative, Span, SpanError, validate


def test_span_text_must_match() -> None:
    """R-005: a span whose recorded text no longer matches the narrative is rejected."""
    narrative = Narrative("Pit A costs 12 USD per tonne.")
    span = Span.find(narrative, "12 USD per tonne")
    span.verify(narrative)

    edited = Narrative("Pit A costs 21 USD per tonne.")
    with pytest.raises(SpanError) as caught:
        span.verify(edited)
    assert "12 USD per tonne" in str(caught.value)


def test_a_detected_span_mismatch_is_reported_by_the_validator(blend) -> None:
    moved = dataclasses.replace(
        blend,
        narrative=Narrative(
            "A plant blends ore from two pits. Pit A costs 99 USD per tonne and pit B "
            "costs 9 USD per tonne. Together they must deliver at least 100 tonnes. "
            "Minimise the total cost."
        ),
    )
    report = validate(moved)
    assert not report.ok
    assert any(f.check == "spans" for f in report.errors), report


def test_offsets_and_text_must_agree_at_construction() -> None:
    with pytest.raises(SpanError):
        Span(start=0, end=5, text="too long for the range")


def test_inferred_span_states_its_reason() -> None:
    span = Span.inferred("the narrative never states the units, tonnes assumed from context")
    assert span.is_inferred
    span.verify(Narrative("anything at all"))  # an inferred span verifies trivially
    with pytest.raises(SpanError):
        Span.inferred("   ")


def test_find_reports_a_missing_phrase_rather_than_guessing() -> None:
    narrative = Narrative("Pit A costs 12 USD per tonne.")
    with pytest.raises(SpanError):
        Span.find(narrative, "pit C")
    with pytest.raises(SpanError):
        Span.find(narrative, "Pit A", occurrence=1)


def test_narrative_digest_detects_an_edited_source() -> None:
    narrative = Narrative("original text")
    stored = narrative.to_json()
    stored["text"] = "edited text"
    with pytest.raises(SpanError):
        Narrative.from_json(stored)
