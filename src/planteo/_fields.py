"""Reading a required field from a document, with a message a ledger can be read by.

The expression and relation parsers already say which node lacked which field. The document's other
parts did not: a quantity, an assumption, an open question, a span, the problem itself read their
fields with a bare index, and a missing one surfaced as `KeyError('span')`, which reaches a run
ledger as the string `'span'` and names neither the field's owner nor what it did have. That is the
path that parses a language model's output, where a missing field is the normal case, so the message
has to carry both.
"""

from __future__ import annotations

from collections.abc import Mapping


def require(data: object, field: str, what: str) -> object:
    """``data[field]``, or a ValueError naming what lacked the field and which keys it had."""
    if not isinstance(data, Mapping):
        raise ValueError(f"{what} must be an object; got {type(data).__name__}")
    if field not in data:
        raise ValueError(f"{what} is missing its {field!r} field; got keys {sorted(data)}")
    return data[field]
