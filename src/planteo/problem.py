"""The Problem document: a narrative after it has been read and before it has been solved.

Two pieces of this object do not appear in the representations surveyed in the research, and both
are there because of what the research measured.

``open_questions`` records what the narrative did not determine. A formalizer that silently resolves
an ambiguity produces an artifact that runs and may not mean what the text said, and nothing in the
artifact reveals the choice. Recording the question, the span that raised it and the resolution taken
makes that choice reviewable.

Every element carries a ``Span``. An element with an inferred span is stating that it was not read
from the text, and why.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from .dimensions import Dimension
from .relations import Objective, Relation, relation_from_json
from .spans import Narrative, Span

SCHEMA_VERSION = "1.0"


class Family(str, Enum):
    """The target family. Each adds required structure, and nothing else."""

    OPTIMIZATION = "optimization"
    DYNAMICS = "dynamics"
    EXPERIMENT = "experiment"
    LEARNING = "learning"


class Role(str, Enum):
    """What a quantity is, which is what determinacy is checked against."""

    #: Given by the problem statement.
    PARAMETER = "parameter"
    #: Chosen by the solver.
    VARIABLE = "variable"
    #: Defined by exactly one relation in terms of others.
    DERIVED = "derived"
    #: Measured, for the dynamics, experiment and learning families.
    OBSERVED = "observed"
    #: An index set, used by BigSum and ForAll.
    SET = "set"


class Domain(str, Enum):
    REAL = "real"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    SET = "set"


@dataclass(frozen=True, slots=True)
class Quantity:
    """A named thing with a dimension. The dimension is not optional.

    ``lower`` and ``upper`` are in the quantity's own units. ``value`` is present only for a
    parameter; a variable with a value is a contradiction the validator reports.
    """

    name: str
    role: Role
    dimension: Dimension
    domain: Domain = Domain.REAL
    lower: float | None = None
    upper: float | None = None
    value: float | None = None
    description: str = ""
    span: Span | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.dimension, Dimension):
            raise TypeError(
                f"quantity {self.name!r} needs a Dimension; dimensionless must be stated "
                "explicitly with Dimension.dimensionless()"
            )
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError(
                f"quantity {self.name!r} has lower {self.lower} above upper {self.upper}"
            )

    def to_json(self) -> dict[str, object]:
        out: dict[str, object] = {
            "name": self.name,
            "role": self.role.value,
            "dimension": self.dimension.to_json(),
            "domain": self.domain.value,
            "description": self.description,
        }
        for key in ("lower", "upper", "value"):
            got = getattr(self, key)
            if got is not None:
                out[key] = got
        if self.span is not None:
            out["span"] = self.span.to_json()
        return out

    @classmethod
    def from_json(cls, data: Mapping[str, object]) -> Quantity:
        span = data.get("span")
        return cls(
            name=str(data["name"]),
            role=Role(str(data["role"])),
            dimension=Dimension.from_json(data["dimension"]),  # type: ignore[arg-type]
            domain=Domain(str(data.get("domain", "real"))),
            lower=_opt_float(data.get("lower")),
            upper=_opt_float(data.get("upper")),
            value=_opt_float(data.get("value")),
            description=str(data.get("description", "")),
            span=Span.from_json(span) if isinstance(span, Mapping) else None,
        )


@dataclass(frozen=True, slots=True)
class Assumption:
    """Something taken to be true that the narrative did not guarantee."""

    statement: str
    span: Span

    def to_json(self) -> dict[str, object]:
        return {"statement": self.statement, "span": self.span.to_json()}

    @classmethod
    def from_json(cls, data: Mapping[str, object]) -> Assumption:
        return cls(
            statement=str(data["statement"]),
            span=Span.from_json(data["span"]),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class OpenQuestion:
    """Something the narrative left undetermined, and what was done about it.

    ``resolution`` may be empty, which means the question is still open and the formalization is
    conditional on an answer. That is a legitimate state and the emitters report it.
    """

    question: str
    span: Span
    resolution: str = ""
    affects: tuple[str, ...] = ()

    @property
    def is_open(self) -> bool:
        return not self.resolution.strip()

    def to_json(self) -> dict[str, object]:
        return {
            "question": self.question,
            "span": self.span.to_json(),
            "resolution": self.resolution,
            "affects": list(self.affects),
        }

    @classmethod
    def from_json(cls, data: Mapping[str, object]) -> OpenQuestion:
        return cls(
            question=str(data["question"]),
            span=Span.from_json(data["span"]),  # type: ignore[arg-type]
            resolution=str(data.get("resolution", "")),
            affects=tuple(str(a) for a in data.get("affects", ())),  # type: ignore[union-attr]
        )


@dataclass(frozen=True, slots=True)
class Metadata:
    problem_id: str = ""
    title: str = ""
    formalizer: str = ""
    created: str = ""
    notes: str = ""

    def to_json(self) -> dict[str, object]:
        return {
            "problem_id": self.problem_id,
            "title": self.title,
            "formalizer": self.formalizer,
            "created": self.created,
            "notes": self.notes,
        }

    @classmethod
    def from_json(cls, data: Mapping[str, object]) -> Metadata:
        return cls(
            problem_id=str(data.get("problem_id", "")),
            title=str(data.get("title", "")),
            formalizer=str(data.get("formalizer", "")),
            created=str(data.get("created", "")),
            notes=str(data.get("notes", "")),
        )


@dataclass(frozen=True, slots=True)
class Problem:
    """A formalized problem statement."""

    narrative: Narrative
    family: Family
    quantities: tuple[Quantity, ...] = ()
    relations: tuple[Relation, ...] = ()
    objectives: tuple[Objective, ...] = ()
    assumptions: tuple[Assumption, ...] = ()
    open_questions: tuple[OpenQuestion, ...] = ()
    metadata: Metadata = field(default_factory=Metadata)
    feasibility_only: bool = False

    # -- lookups ---------------------------------------------------------------------

    @property
    def scope(self) -> dict[str, Dimension]:
        """Name to dimension, the map every dimensional check runs against."""
        return {q.name: q.dimension for q in self.quantities}

    def quantity(self, name: str) -> Quantity:
        for q in self.quantities:
            if q.name == name:
                return q
        raise KeyError(f"no quantity named {name!r}")

    def by_role(self, role: Role) -> tuple[Quantity, ...]:
        return tuple(q for q in self.quantities if q.role is role)

    @property
    def has_open_questions(self) -> bool:
        return any(q.is_open for q in self.open_questions)

    def references(self) -> set[str]:
        names: set[str] = set()
        for relation in self.relations:
            names |= relation.references()
        for objective in self.objectives:
            names |= objective.references()
        return names

    # -- serialisation ----------------------------------------------------------------

    def to_json(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "family": self.family.value,
            "narrative": self.narrative.to_json(),
            "quantities": [q.to_json() for q in self.quantities],
            "relations": [r.to_json() for r in self.relations],
            "objectives": [o.to_json() for o in self.objectives],
            "assumptions": [a.to_json() for a in self.assumptions],
            "open_questions": [q.to_json() for q in self.open_questions],
            "metadata": self.metadata.to_json(),
            "feasibility_only": self.feasibility_only,
        }

    @classmethod
    def from_json(cls, data: Mapping[str, object]) -> Problem:
        version = str(data.get("schema_version", ""))
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"document schema version {version!r} is not {SCHEMA_VERSION!r}; "
                "refusing to guess at a different shape"
            )
        return cls(
            narrative=Narrative.from_json(data["narrative"]),  # type: ignore[arg-type]
            family=Family(str(data["family"])),
            quantities=tuple(Quantity.from_json(q) for q in data.get("quantities", ())),  # type: ignore[union-attr]
            relations=tuple(relation_from_json(r) for r in data.get("relations", ())),  # type: ignore[union-attr]
            objectives=tuple(Objective.from_json(o) for o in data.get("objectives", ())),  # type: ignore[union-attr]
            assumptions=tuple(Assumption.from_json(a) for a in data.get("assumptions", ())),  # type: ignore[union-attr]
            open_questions=tuple(
                OpenQuestion.from_json(q) for q in data.get("open_questions", ())  # type: ignore[union-attr]
            ),
            metadata=Metadata.from_json(data.get("metadata", {})),  # type: ignore[arg-type]
            feasibility_only=bool(data.get("feasibility_only", False)),
        )


def _opt_float(value: object) -> float | None:
    return None if value is None else float(value)  # type: ignore[arg-type]
