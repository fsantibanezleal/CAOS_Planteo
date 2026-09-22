# Security policy

## Scope

`planteo` is a pure-Python library with no runtime dependencies. It parses and validates documents
and emits model source. It opens no network connections and executes no code from a document.

One area deserves care from callers: `emit_source` produces Python source text. Running that text is
the caller's decision, and a `Problem` assembled from an untrusted document should be validated and
read before its emitted source is executed. Quantity and relation names reach the emitted source as
identifiers, so a caller that builds problems from untrusted input should constrain names to
identifiers before emitting.

## Reporting a vulnerability

Report privately to fsantibanez@gmail.com rather than opening a public issue. Include the version, a
minimal document or snippet that reproduces the problem, and what you expected instead.

Expect an acknowledgement within a week. Fixes ship as a new patch release with an entry in the
CHANGELOG.

## Supported versions

The latest released version. This project is pre-1.0; the schema version carried in each document is
what tells you whether a stored document still matches the code.
