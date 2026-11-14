# Clean-context feature documentation assessment

The implementation agent received the task and study paths without the earlier
feature-development chat. On 2026-10-30 it read `AGENTS.md`, `progress.txt`, study
build scripts, then these three guides at the verified remote develop commit
`3e907fd9eb4fe1d5946dcd161c68b2fdd2b341a5`, before opening SDK headers:

- [Native batches](https://github.com/gordonwatts/correctionlib/blob/3e907fd9eb4fe1d5946dcd161c68b2fdd2b341a5/docs/native-batches.md)
- [Array outputs](https://github.com/gordonwatts/correctionlib/blob/3e907fd9eb4fe1d5946dcd161c68b2fdd2b341a5/docs/array-outputs.md)
- [Combined API](https://github.com/gordonwatts/correctionlib/blob/3e907fd9eb4fe1d5946dcd161c68b2fdd2b341a5/docs/batch-array-integration.md)

The guides were sufficient to choose the four separate cases: scalar input and
output, many inputs with scalar outputs, one input with fixed array output, and
many inputs with fixed array outputs. They state unchanged Python syntax,
root-only native callbacks, row-major output, signed element strides, scalar
broadcast, ownership, empty validation and exception handling. API4 registration
and recompilation requirements were explicit. There was no temptation to treat
array outputs as a multi-selector API.

The following questions were recorded before consulting headers/examples:

1. Is there an efficient typed column reader beyond `column.at(row)`? The guide
   only demonstrates a returned `Variable::Type`. The public header confirms
   that `at` is the sole reader and pointer storage is private. This is an API
   limitation for a performance study, not a broken contract. The study uses
   `at` and does not depend on private layout or copy inputs into hidden arrays.
2. How does a complete provider declare packed outputs and implement both
   scalar-point and batch-array entry points? The guides describe the methods
   and envelope, but do not directly link a complete combined provider example. Public
   `correction_plugin.h` supplied exact method declarations, and the existing
   scalar provider example supplied loading/registration details. The study's
   `src/table.h`, `src/registry.cc` and `feature_workloads.py` now provide a
   complete runnable example. A later targeted check, prompted by independent
   review, found `examples/array_plugin/nodes.cc` already implements both
   callbacks and a dispatch probe. The gap is discoverability from the guides,
   not missing example code. No core implementation source was needed for the
   provider's algorithm.

The clean-context run did encounter a study-specific wheelhouse failure, not a
feature API problem: `_deps/wheels` did not exist in this checkout. The retry
used `/home/gwatts/atlas/correctionlib-feature-build/wheels` read-only. The fresh
bootstrap can download dependencies by default or accept `WHEELHOUSE`.

Suggested guide improvements are a sentence stating the public reader limit
and a direct link to the existing complete combined provider from the integration guide.
The study README should distinguish generic array children from its explicit
packed table, and separate Python operation timings from C++ dispatch timings.

After provider implementation and validation, a targeted core-source check of
`PluginNode::evaluate_batch` verified a proposed README performance explanation:
the fallback allocates one argument vector per batch and assigns its entries
per row. The README therefore says the native callback removes per-row argument
assignment and virtual scalar dispatch, not per-row vector allocation.

Documentation followup: both guide improvements were applied and pushed to
CorrectionLib develop in doc-only commit
[`3dcfa20e`](https://github.com/gordonwatts/correctionlib/commit/3dcfa20ec01fb40c4d5fec58383785519dec1c00).
This does not change the tested study dependency: its binaries and retained
provenance remain pinned to `3e907fd9`. A reused source checkout must still be
at that exact tested pin to pass the feature bootstrap guard.
