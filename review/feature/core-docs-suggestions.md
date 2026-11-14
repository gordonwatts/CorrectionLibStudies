Suggested doc-only followup on CorrectionLib develop after the pinned campaign:

In `docs/native-batches.md`, after the paragraph explaining `column.at(row)`:

> `BatchInput::at(row)` is the supported public reader for a column or scalar
> broadcast and returns a `Variable::Type`. The SDK does not expose typed raw
> column pointers to providers. A callback can hoist input and axis selection out
> of its row loop, but should not inspect private storage or assume SIMD.

In `docs/batch-array-integration.md`, after the first runnable-example link:

> For a complete custom provider, see
> [the array-plugin example](../examples/array_plugin/nodes.cc). It declares
> `output_size()`, implements both `evaluate_array` and `evaluate_batch_array`,
> and includes a probe that throws if the host falls back to per-point evaluation.

These changes need no API change and do not alter the tested core pin.
