# The dynamics family, design

## Elements

| Element | Where | Meaning |
|---|---|---|
| role `state` | `Quantity.role` | a quantity that evolves; its `value` is its initial value at the start of the range |
| role `independent` | `Quantity.role` | the variable the states evolve along, usually time; `lower` and `upper` are the simulated range |
| `rate` | a relation, tag `rate` | `d(state)/d(wrt) = expression`, one per state; `wrt` names the independent variable |
| `Query` | `Problem.queries` | a named expression evaluated at `at`, a value of the independent variable |

Derived quantities keep their meaning: an equality with a derived quantity alone on one side, which a
dynamics problem evaluates at every point of the range (a volume that grows with time, a
concentration that is an amount over a volume). Parameters are unchanged.

A second-order equation is written as two first-order rates, position and velocity, which is what
every numerical integrator takes; no second-derivative node is added, so the node set stays closed.

## Dimensions

`rate.check_dimensions` needs the independent variable's dimension, so the relation names it (`wrt`)
rather than relying on the problem to supply it: `dim(expression) == dim(state) / dim(wrt)`. The
family check then requires `wrt` to be the problem's one independent variable.

## Validation

`_check_family` gains a dynamics branch: one independent variable with both bounds; at least one
state; every state has an initial value and exactly one rate whose `wrt` is the independent variable;
no rate for anything but a state; at least one query, each within the range; no objective, no
decision variable, and no relation but rates and the equalities that define derived quantities. The
optimization branch gains the converse: no rate, no query, no state, no independent variable.
Determinacy treats a state like a parameter for its value, and an independent variable as given.

## Canonical form

Rates canonicalise as `{"tag": "rate", "state", "wrt", "expression"}` with names renamed by
structural position, and queries as `{"expression", "at"}`, sorted. The positional renaming already
keys on role, so states and the independent variable cannot swap names with parameters.

## Evaluation and emission

`planteo.evaluate(expression, values)` computes a number from a closed-set expression and a map of
names to numbers: constants, references, sums, products, rational powers, and conditionals over
comparisons and logical connectives. An indexed sum is refused (`NotEvaluable`), because a scalar map
cannot say what the set's members are.

`planteo.emit.scipy.emit_source(problem)` writes a readable Python module with `STATES`, `Y0`,
`T_SPAN`, `rhs(t, y)` and one function per query, which `scipy.integrate.solve_ivp` integrates.
The oracle does not execute this source; it builds its right-hand side from the evaluator, and R-109
holds the two to the same numbers.

## Schema

Documents are written at 1.1. A 1.0 document has no queries and no dynamics roles, and loads as it
always did.
