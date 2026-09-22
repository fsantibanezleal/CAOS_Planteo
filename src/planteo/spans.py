"""Provenance: which words produced this symbol.

The measured failure this package exists to address is a formalization that runs and does not mean
what the text said. That gap is only auditable if each element of the formalization points back at
the span of narrative it came from. A span therefore carries both its offsets and the substring it
covered, so a document that has been moved, stored or edited can be checked against its narrative
instead of trusted.

An element with no span is allowed, and it is a statement: it says the element was inferred rather
than read. ``Span.inferred()`` records that explicitly, with the reason.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


class SpanError(ValueError):
    """Raised when a span does not agree with the narrative it points into."""


@dataclass(frozen=True, slots=True)
class Narrative:
    """The source text, and enough about it to detect that it changed."""

    text: str
    source: str = "inline"
    language: str = "en"

    @property
    def digest(self) -> str:
        """A stable content hash, so a stored Problem can detect a changed narrative."""
        import hashlib

        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def slice(self, start: int, end: int) -> str:
        return self.text[start:end]

    def to_json(self) -> dict[str, object]:
        return {
            "text": self.text,
            "source": self.source,
            "language": self.language,
            "digest": self.digest,
        }

    @classmethod
    def from_json(cls, data: Mapping[str, object]) -> Narrative:
        narrative = cls(
            text=str(data["text"]),
            source=str(data.get("source", "inline")),
            language=str(data.get("language", "en")),
        )
        stored = data.get("digest")
        if stored is not None and stored != narrative.digest:
            raise SpanError(
                "narrative digest does not match its text: the source changed after this "
                "document was written, so every span in it is suspect"
            )
        return narrative


@dataclass(frozen=True, slots=True)
class Span:
    """A character range into a narrative, carrying the text it covered.

    ``text`` is redundant with ``start``/``end`` on purpose. The redundancy is the check: if the
    narrative is edited, the offsets still point somewhere, and only the stored text reveals that
    they now point at something else.
    """

    start: int
    end: int
    text: str
    inferred_reason: str | None = None

    def __post_init__(self) -> None:
        if self.inferred_reason is None:
            if self.start < 0 or self.end < self.start:
                raise SpanError(f"invalid span offsets: [{self.start}, {self.end})")
            if len(self.text) != self.end - self.start:
                raise SpanError(
                    f"span text is {len(self.text)} characters but the range covers "
                    f"{self.end - self.start}"
                )

    @classmethod
    def over(cls, narrative: Narrative, start: int, end: int) -> Span:
        """Take a span from a narrative, capturing the covered text."""
        if end > len(narrative.text):
            raise SpanError(
                f"span ends at {end} but the narrative is {len(narrative.text)} characters"
            )
        return cls(start=start, end=end, text=narrative.slice(start, end))

    @classmethod
    def find(cls, narrative: Narrative, phrase: str, occurrence: int = 0) -> Span:
        """Locate a phrase in the narrative. Raises when it is absent or the index is out of range."""
        position = -1
        for _ in range(occurrence + 1):
            position = narrative.text.find(phrase, position + 1)
            if position == -1:
                raise SpanError(
                    f"phrase {phrase!r} does not occur {occurrence + 1} time(s) in the narrative"
                )
        return cls.over(narrative, position, position + len(phrase))

    @classmethod
    def inferred(cls, reason: str) -> Span:
        """An element that was not read from the text. The reason is required."""
        if not reason.strip():
            raise SpanError("an inferred element must say why it was inferred")
        return cls(start=-1, end=-1, text="", inferred_reason=reason)

    @property
    def is_inferred(self) -> bool:
        return self.inferred_reason is not None

    def verify(self, narrative: Narrative) -> None:
        """Check the span still covers the text it claims. Raises on a mismatch."""
        if self.is_inferred:
            return
        actual = narrative.slice(self.start, self.end)
        if actual != self.text:
            raise SpanError(
                f"span [{self.start}, {self.end}) recorded {self.text!r} "
                f"but the narrative now holds {actual!r}"
            )

    def to_json(self) -> dict[str, object]:
        if self.is_inferred:
            return {"inferred_reason": self.inferred_reason}
        return {"start": self.start, "end": self.end, "text": self.text}

    @classmethod
    def from_json(cls, data: Mapping[str, object]) -> Span:
        if "inferred_reason" in data:
            return cls.inferred(str(data["inferred_reason"]))
        return cls(
            start=int(data["start"]),  # type: ignore[arg-type]
            end=int(data["end"]),  # type: ignore[arg-type]
            text=str(data["text"]),
        )
