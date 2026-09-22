"""Emitters: a validated Problem into a backend's model.

The rule every emitter obeys, and the reason this package exists rather than a pile of ad-hoc
translation code: **an emitter is total on the problems it declares it can take, or it raises**. It
never drops a relation it did not understand. A model that solves because a constraint quietly
vanished is the failure mode this representation is built to make impossible, and it is invisible in
every output except the one nobody checks.

``NotRepresentable`` names the construct that could not be expressed, so the caller can decide
between changing the formulation and choosing another backend.
"""

from __future__ import annotations


class NotRepresentable(ValueError):
    """An emitter cannot express a construct in its target language.

    Carries the construct and, where known, the element it appeared in, because "unsupported" with
    no subject is not actionable.
    """

    def __init__(self, construct: str, backend: str, element: str = "") -> None:
        where = f" in {element!r}" if element else ""
        super().__init__(
            f"{backend} cannot express {construct}{where}; "
            "no partial model was emitted"
        )
        self.construct = construct
        self.backend = backend
        self.element = element


__all__ = ["NotRepresentable"]
