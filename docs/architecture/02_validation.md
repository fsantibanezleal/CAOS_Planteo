# The validator

Five checks. It rejects; it does not coerce. Every finding names the element it is about, because a
validator that says "invalid" and nothing else pushes the work onto the person with the least
context.

## Order matters

```
names -> closure -> spans -> dimensions -> determinacy -> family -> open questions
```

Dimensions are checked **only if closure passed**. A dimensional error reported against an
undeclared symbol is noise: the real problem is the missing declaration, and reporting both trains a
reader to skim the output. This is enforced, not just intended, by
`tests/test_validate_closure.py::test_dimensional_check_is_skipped_while_closure_fails`.

Everything else runs regardless, so one call reports every problem rather than one problem per call.

## The five checks

### 1. Names

No quantity is declared twice.

### 2. Closure

Every reference in a relation or objective resolves to a declared quantity. A bound index inside a
`BigSum` or a `ForAll` is not a free reference; the set it ranges over is.

### 3. Spans

Every span still covers the text it recorded, checked against the narrative in the document. See
[`01_why_dimensions_and_provenance.md`](01_why_dimensions_and_provenance.md).

### 4. Dimensions

Both sides of a comparator must be compatible. Sum terms must all agree. Conditional branches must
agree. Products are unconstrained, because that is where mixing dimensions is legitimate.

### 5. Determinacy

Every quantity is exactly one of: given a value, chosen by the solver, derived by exactly one
relation, or observed.

The definition rule is deliberately syntactic. A relation defines a quantity when it is an equality
and that quantity stands alone on one side **and does not appear on the other**. So
`total == c * x` defines `total`; `total == total + x` defines nothing, and the validator reports
`total` as under-determined rather than counting the circular equality as a definition.

Solving for a symbol is not this library's job, and a rule a reader can check by eye is easier to
satisfy on purpose than a clever one.

Severity is chosen to match what a caller can do about it:

| Situation | Severity | Why |
|---|---|---|
| a derived quantity with no defining relation | error | the model is incomplete |
| a derived quantity with two defining relations | error | the model is over-determined |
| a decision variable that also carries a fixed value | error | a contradiction |
| a parameter with no value | **warning** | legitimate: a template awaiting data |

### 6. Family completeness

For the optimization family: at least one objective or an explicit `feasibility_only` declaration,
never both, and at least one decision variable.

The other three families have no checks yet, and the code says so in a comment rather than
pretending. Declaring a family and giving it an empty check would be a gate that measures nothing,
which is the failure this whole project is about.

## Reading a report

```python
report = validate(problem)
report.ok          # False if any finding is an error
report.errors      # only the errors
report.warnings    # only the warnings
report.raise_if_invalid()
print(report)      # one line per finding
```

```
error: dimensions [meet_demand]: left side is m but right side is s; they cannot be compared
error: determinacy [total]: is derived but no relation defines it (under-determined)
warning: open-questions [are partial tonnes allowed]: is unresolved; the formalization is conditional on an answer
```

Emitters call the validator themselves and refuse an invalid problem, rather than trusting the caller
to have run it.
