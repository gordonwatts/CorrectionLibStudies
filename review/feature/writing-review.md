# Fresh-context writing and evidence review

Reviewer: `gpt-6.1-sol`, high reasoning, `fork_turns: none`. The reviewer received
only the self-contained [prompt](writing-review-prompt.txt) and the listed
audience, README and source/evidence paths. It did not receive chat history.

README is adequate to continue. No substantive numerical, precision, or
timing-scope errors requiring correction were found.

Verified against retained evidence:

- All 16 table entries and quoted kernel/packed timings match `summary.json`
  after rounding.
- Ratios are 1.4010x and 8.7697x, supporting 1.40x and 8.77x.
- Counts match: 4,636 rows, 37,088 raw records, 467,660,288 comparisons.
  Metadata's provenance hash matches the retained file.
- Ordinary and sanitizer logs each report 503 passing tests.
  `tests/test_nodes.py` has no changes relative to `9ae3d72`.
- Source supports scalar fallback, native scalar-output batches, and explicit
  packed components. Precision, synthetic scope, historical reproduction, and
  allocation/stacking caveats are clear.

Two optional clarity suggestions were applied:

1. Define S as the declared number of components.
2. Clarify that raw records include 4,636 warm rounds and 32,452 retained rounds.

The reviewer performed no builds, new timings or file edits. The implementation
agent applied these prose-only changes; no numerical source changed afterward.
