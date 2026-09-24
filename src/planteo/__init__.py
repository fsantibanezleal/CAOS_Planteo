"""planteo: a typed representation for a problem after it has been read and before it is solved.

A narrative problem statement is ambiguous, under-specified and unit-bearing. Turning it into a
solver model, a simulation, an experiment design or a learning task is usually done by writing code
straight from the text, which loses the two things that decide whether the result is right: which
words produced which symbol, and what the words did not say.

This package holds the object in between. Quantities carry dimensions, elements carry the span of
text they came from, and what the narrative failed to determine is recorded as an open question
rather than silently resolved.

It does not read natural language and it does not solve anything. It defines the object, validates
it, and emits it.

    >>> from planteo import Narrative, Problem, Family, Quantity, Role, Dimension
    >>> text = Narrative("Buy at most 10 tonnes.")
    >>> problem = Problem(narrative=text, family=Family.OPTIMIZATION)
    >>> problem.family.value
    'optimization'
"""

from __future__ import annotations

from .canonical import Comparison, Verdict, canonical_form, compare, digest
from .dimensions import (
    AXES,
    COUNT,
    CURRENCY,
    DIMENSIONLESS,
    ENERGY,
    LENGTH,
    MASS,
    MASS_RATE,
    POWER,
    TIME,
    Dimension,
    DimensionError,
)
from .dynamics import System, system
from .emit import NotRepresentable
from .evaluate import NotEvaluable, evaluate, holds
from .expressions import (
    BigSum,
    Conditional,
    Constant,
    Expression,
    Power,
    Product,
    Ref,
    Sum,
    expression_from_json,
)
from .problem import (
    SCHEMA_VERSION,
    Assumption,
    Domain,
    Family,
    Metadata,
    OpenQuestion,
    Problem,
    Quantity,
    Query,
    Role,
)
from .relations import (
    Comparator,
    Compare,
    ForAll,
    Logical,
    Objective,
    Rate,
    Relation,
    Sense,
    relation_from_json,
)
from .spans import Narrative, Span, SpanError
from .validate import Finding, Report, Severity, ValidationError, validate

__version__ = "0.2.0"
#: The padded display form used in the CHANGELOG, the tag and any UI string.
__display_version__ = "0.02.000"

__all__ = [
    "__display_version__",
    "__version__",
    "Assumption",
    "AXES",
    "BigSum",
    "canonical_form",
    "Comparator",
    "Compare",
    "compare",
    "Comparison",
    "Conditional",
    "Constant",
    "COUNT",
    "CURRENCY",
    "digest",
    "Dimension",
    "DimensionError",
    "DIMENSIONLESS",
    "Domain",
    "ENERGY",
    "evaluate",
    "Expression",
    "expression_from_json",
    "Family",
    "Finding",
    "ForAll",
    "holds",
    "LENGTH",
    "Logical",
    "MASS",
    "MASS_RATE",
    "Metadata",
    "Narrative",
    "NotEvaluable",
    "NotRepresentable",
    "Objective",
    "OpenQuestion",
    "POWER",
    "Power",
    "Problem",
    "Product",
    "Quantity",
    "Query",
    "Rate",
    "Ref",
    "Relation",
    "relation_from_json",
    "Report",
    "Role",
    "SCHEMA_VERSION",
    "Sense",
    "Severity",
    "Span",
    "SpanError",
    "Sum",
    "System",
    "system",
    "TIME",
    "validate",
    "ValidationError",
    "Verdict",
]
