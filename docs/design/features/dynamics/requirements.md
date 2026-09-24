# The dynamics family, requirements

Part of `docs/design/SDD.md`. Design in [`design.md`](design.md), tasks in [`tasks.md`](tasks.md).
Research: Enunciado's dossier 09 (the dynamics family's prior art, representation and oracle).

A dynamics problem is a system of first-order ordinary differential equations read from a statement:
states with initial values, one independent variable with the range to simulate, a rate for every
state, and the queries the statement asks ("the concentration after 20 minutes").

```
R-101  THE representation SHALL accept a dynamics problem with states, one independent variable, a
       rate per state and at least one query, and SHALL round-trip it through JSON unchanged.
       Gate: tests/test_dynamics.py::test_a_dynamics_problem_round_trips

R-102  IF a rate's expression does not have the dimension of its state divided by the dimension of
       the independent variable, THEN THE validator SHALL reject it and name the rate.
       Gate: tests/test_dynamics.py::test_a_rate_with_the_wrong_dimension_is_rejected

R-103  IF a state has no rate, more than one, or no initial value, THEN THE validator SHALL reject it
       and name the state.
       Gate: tests/test_dynamics.py::test_every_state_needs_one_rate_and_an_initial_value

R-104  IF a dynamics problem has no independent variable, more than one, or one without both bounds
       of its range, THEN THE validator SHALL reject it.
       Gate: tests/test_dynamics.py::test_the_independent_variable_is_one_and_bounded

R-105  IF a dynamics problem has no query, or a query outside the independent variable's range, THEN
       THE validator SHALL reject it.
       Gate: tests/test_dynamics.py::test_a_query_must_exist_and_be_in_range

R-106  IF an optimization problem carries a rate, a query, a state or an independent variable, or a
       dynamics problem carries an objective, a decision variable or an inequality, THEN THE
       validator SHALL reject it.
       Gate: tests/test_dynamics.py::test_the_families_do_not_mix

R-107  THE canonical form of a dynamics problem SHALL be unchanged by renaming quantities and
       reordering elements, and SHALL change when a rate's coefficient changes.
       Gate: tests/test_dynamics.py::test_the_dynamics_canonical_form

R-108  THE evaluator SHALL compute every node of the closed set but the indexed sum, which it SHALL
       refuse by name rather than approximate.
       Gate: tests/test_dynamics.py::test_the_evaluator_covers_the_node_set

R-109  THE SciPy emitter's source SHALL integrate to the same query values as a right-hand side
       built from the evaluator.
       Gate: tests/test_dynamics.py::test_the_emitted_source_agrees_with_the_evaluator

R-110  THE serialiser SHALL write schema 1.1, and a schema 1.0 document SHALL still load.
       Gate: tests/test_dynamics.py::test_a_schema_1_0_document_still_loads
```

Why each exists. R-102 is the unit-conversion trap in its dynamics form: a rate in litres per minute
written for a state counted in hours passes every check but the dimensional one, and only if the
dimensions are checked against the independent variable. R-103 to R-105 make the system determined:
an ODE with a state that has no rate cannot be integrated, and one with two is contradictory. R-106
keeps the families apart, because an inequality in a simulation or a query in an optimization means
the document was written for the wrong family. R-107 carries the structural oracle's decidability
to the new elements. R-108 exists because an approximate evaluation of an indexed sum would be a
number the document never stated. R-109 holds the emitted source, which the site shows a reader, to
the numbers the oracle uses.
