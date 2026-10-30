# Fresh-context writing review

Reviewed as a particle physicist familiar with histogram calibrations but unfamiliar with computer architecture. I read the README before inspecting the supplied source and evidence; I did not read the chat or progress log, modify implementation, or run builds or benchmarks.

The numerical timing claims, test counts, precision contract, and scalar-interface limitations are supported by the retained evidence. I found one causal performance statement that is stronger than the measurement supports, plus several wording and reproduction improvements below. No measured number needs correction.

## Priority 1: qualify the explanation of small-batch timings

At README lines 122–125, “Python call and array costs dominate” reads as a measured breakdown of where time is spent. `scripts/benchmark.py` measures the whole operation and does not measure these components separately. The near-flat small-batch timings and the scalar comparison are consistent with this explanation, but do not establish the attribution.

Replace the small-batch and scalar sentences with:

> For 1–16 items, the measured times are similar across searches and change little with batch size; these results do not establish a useful advantage for a particular search. This suggests that costs outside the bin search are important, although we did not measure those costs separately. For the same 20×20 fixture, the complete scalar lookup-and-rescale operation takes **2.66 microseconds** with unrolling, compared with **6.48 microseconds** when passed one-element arrays.

This also avoids making 2.66 microseconds sound like the isolated cost of `correction.evaluate`: the measurement includes the Python wrapper, multiplication, tuple creation, and disposal, as it does for the array workloads. The values match the `fixed20x20`, `unrolled`, one-output float64 rows of `results/main/summary.csv`.

## Priority 2: make the reproduction scope and evidence preservation explicit

The new label preserves the timing directory, but the reproduction commands overwrite shared evidence: bootstrap and `scripts/provenance.py` write `results/build/`, `scripts/run.sh` writes `results/tests.log`, and the displayed sanitizer redirection writes `results/sanitizer.log`. In particular, a new provenance file can replace the file whose hash is recorded in the published campaign's `metadata.json`.

Add before the commands:

> Run these commands in a fresh checkout to preserve the evidence linked above. Each timing label creates a new results directory, but build provenance and test logs use shared filenames and are replaced when you rerun the scripts.

The dependency list in bootstrap is partly unpinned. The commands reproduce the procedure, rather than guaranteeing the identical dependency environment. Add near the package-version discussion:

> CorrectionLib is pinned to the commit above. Other Python dependencies are selected when bootstrap runs; the exact versions used for the published results are recorded in the build provenance. Rerunning later may therefore use a different environment.

Also state the prerequisites before entering WSL:

> These instructions require the `atlas_al9` WSL2 distribution with access to ATLAS software on CVMFS, plus Git and system Python. They do not install the distribution or configure CVMFS.

## Priority 3: define the few terms needed to read the introduction

The opening assumes the reader already knows “native node,” “payload,” and “correction graph.” These matter to understanding what this study adds. Replace its first paragraph with:

> This repository tests alternative ways to find a histogram bin **inside the CorrectionLib evaluator**. Each implementation is a named C++ plugin node: one step in the sequence of transformations and lookups that defines a correction. A Python converter replaces supported constant histogram tables in a CorrectionLib JSON file while keeping the surrounding correction steps.

In the dependency paragraph, replace “these providers” with “the histogram plugin.” This uses one name consistently for the library that supplies all seven nodes.

## Priority 4: simplify the tree description and sharpen the source link

The current tree description is accurate but its “comparison contributes zero or one to the next index” explanation requires programming knowledge. Suggested replacement for the table cell:

> Halve the candidate range at each step, storing extra unused entries so the search follows the same sequence of step sizes. The code calculates the next position from the comparison result. The shared helper also supplies other nodes' fallback. This does not establish which machine instructions the compiler emits.

Keep the existing link to `src/nodes/tree.cc` and the shared-helper link to `src/table.h`. For the built-in control, change the pinned `correction.cc` link from `#L118` to `#L165`, where `std::upper_bound` implements the explicit-edge search. Line 118 starts a longer function whose first branch handles the separate uniform representation.

## Checks that support keeping the remaining claims

- The README table agrees with the matching rows of `summary.csv` and `timing-matrix.md`; the quoted 2.30/5.84 ms, 2.64/5.63 ms, and 35.58/87.49 ms comparisons round correctly. The “about 2.5×” statement applies to the complete measured operation.
- `metadata.json` and the benchmark support logical CPU 0, seven retained rounds after one discarded round, a three-millisecond pilot target, rotated algorithm order, and the documented inclusion/exclusion of work. `validation.json` records 944 rows and 37,341,760 output comparisons.
- `src/table.h` narrows coordinates on entry, rounds content and numeric fallback during construction, rounds edge thresholds upward, and widens the returned factor. The float32 arithmetic source uses float32 estimates. The primary coordinates are generated in float32 and widened in `workloads.py`, so matched bin selection is a deliberately restricted benchmark input condition, not a promise for arbitrary doubles. The README already makes that distinction clearly.
- The precision counterexample, edge and neighboring-value tests, malformed-configuration tests, transform-graph test, and ordinary/sanitizer logs support the stated validation coverage and 319 passing tests. The sanitizer qualification that the dependency is not instrumented is correct.
- The pinned SDK header returns one double per scalar evaluation. The 16-output benchmark explicitly makes 16 independent correction calls and multiplications. The README correctly avoids claiming shared-bin reuse, packed outputs, batch SIMD, a float32 Python array API, or full-analysis/real-calibration validation.
- The retained core and provider compile commands use the same GCC executable and the documented optimization flags. The build provenance identifies the requested CorrectionLib commit and records source/library hashes and loaded libraries.
