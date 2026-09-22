# planteo documentation

| Theme | What it covers |
|---|---|
| [`design/`](design/) | The software design document, written before the code. Every requirement names the test that verifies it. |
| [`architecture/`](architecture/) | How the representation is put together, and why each piece is shaped that way. |
| [`guides/`](guides/) | How to do things: build a problem, emit it, compare two formalizations. |
| [`data-contract.md`](data-contract.md) | The document schema, field by field, with what is rejected and why. |

## Where to start

- To use the library: the [README](../README.md), then [`guides/01_build_a_problem.md`](guides/01_build_a_problem.md).
- To understand the design: [`architecture/01_why_dimensions_and_provenance.md`](architecture/01_why_dimensions_and_provenance.md).
- To change the library: [`design/SDD.md`](design/SDD.md) and [`../CONTRIBUTING.md`](../CONTRIBUTING.md).

## What this library is, and is not

**It is** a representation for a problem that has been read and not yet solved, with a validator and
emitters.

**It is not** a natural-language reader, a solver, a modelling language, or an equivalence oracle.
Each of those boundaries is deliberate and is stated where it matters: the reader belongs to a
harness, the solving belongs to the backends, and the oracle question is answered honestly by the
verdict vocabulary in [`architecture/03_canonical_form.md`](architecture/03_canonical_form.md).
