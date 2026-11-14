# Histogram lookup nodes for CorrectionLib

Historical scalar-SDK study, retained from commit `9ae3d72`. To reproduce this
page's commands, check out that study commit in a separate directory first.
The current checkout uses API4 and [different build instructions](README.md).
All measurements below belong to the original PR1 campaign, not develop.

This repository tests alternative ways to find a histogram bin **inside the
CorrectionLib evaluator**. Each implementation is a named C++ plugin node:
one step in the sequence of transformations and lookups that defines a
correction, with its own [source file](src/nodes/). A Python converter replaces
supported constant histogram tables in a CorrectionLib JSON file while keeping
the surrounding correction steps.

The dependency is the experimental native-node interface in
[CorrectionLib PR #1](https://github.com/gordonwatts/correctionlib/pull/1), pinned
to [`8dc0b7a`](https://github.com/gordonwatts/correctionlib/commit/8dc0b7a8bfe82c15115ff2a5907d4bfa35ee4710).
The build script compiles that fork and the histogram plugin together. Installing the
ordinary PyPI release does not provide this interface.

## What is measured

For each item, a histogram supplies a dimensionless calibration factor, then
Python multiplies the first input coordinate by that factor:

```python
rescaled_x = correction.evaluate(x, y) * x  # use evaluate(x) for a 1D table
```

The synthetic examples use 64 bins in one dimension, or 20×20 bins in two
dimensions, with either equal or unequal bin widths. Coordinates are random,
including 10% of the histogram span beyond each endpoint. These are tests of
lookup behavior; they are not measured detector calibrations. The
[fixture definitions](python/histogram_nodes/workloads.py) specify the edges,
contents, and random seed.

Batch size means the **number of items**, not the number of histogram axes or
systematic variations. Every size from **1 through 16**, then **1,000, 10,000,
and 100,000**, is tested. A separate workload evaluates 16 independent scale
corrections at the same coordinates. It repeats the search for each correction;
the current interface does not share bin indices across those outputs.

## Algorithms and source

All node names start with `study.hist.`. All use the same
[configuration checks](src/table.cc), [flow handling and content indexing](src/table.h),
and [native registration](src/registry.cc).

| Name | How the bin is found |
| --- | --- |
| Built-in control | CorrectionLib `MultiBinning` with explicit edge lists, using the pinned fork's [binary search](https://github.com/gordonwatts/correctionlib/blob/8dc0b7a8bfe82c15115ff2a5907d4bfa35ee4710/src/correction.cc#L165). Even the equal-width fixtures use explicit edges, rather than its separate uniform-bin representation. |
| [`binary`](src/nodes/binary.cc) | The C++ standard binary search repeatedly halves the remaining edge range. This is the control for introducing a plugin around a familiar search. |
| [`linear`](src/nodes/linear.cc) | Compare against successive edges until reaching the bin. It may do more comparisons, but is a useful simple control. |
| [`tree`](src/nodes/tree.cc) | Halve the candidate range at each step, storing extra unused entries so the search follows the same sequence of step sizes. The code calculates the next position from the comparison result. The [shared helper](src/table.h) also supplies other nodes' fallback. This does not establish which machine instructions the compiler emits. |
| [`unrolled`](src/nodes/unrolled.cc) | For at most 32 bins per axis, write out five comparison steps instead of running a search loop. Larger axes use the tree. Even a one-bin axis executes the five steps. |
| [`arithmetic`](src/nodes/arithmetic.cc) | For approximately equal-width axes, estimate the bin from the coordinate and inverse bin width. Guard and clamp the estimate before integer conversion, then compare against the stored edges to repair rounding errors. Axes that fail the equal-width check or have unusable scales use the tree. |
| [`float32_unrolled`](src/nodes/float32_unrolled.cc) | The unrolled search with float32 coordinates and stored numbers, under the precision contract below. |
| [`float32_arithmetic`](src/nodes/float32_arithmetic.cc) | The arithmetic search with that same float32 contract and tree fallback. |

The earlier companion study explored sharing a search across outputs, packing
several outputs together, compiler hints on the output loop, and AVX2 instructions
that process several items at once. The PR's
[`PluginNode::evaluate`](https://github.com/gordonwatts/correctionlib/blob/8dc0b7a8bfe82c15115ff2a5907d4bfa35ee4710/include/correction_plugin.h)
accepts scalar arguments and returns one double. It provides neither a batch
callback nor a multiple-output result. Those grouped techniques therefore do
not become equivalent nodes here. Historical companion timings are not used in
these tables.

## Precision and boundaries

Float64 means a 64-bit floating-point number, called `double` in C++; float32
means a 32-bit floating-point number, called `float`. No float16 (16-bit
floating-point) implementation is included.

Here, the original edges and contents mean the float64 values **after
CorrectionLib parses the JSON payload**. Its decimal conversion can differ
slightly from Python's. The provider preserves those parsed numbers when the
configuration crosses the plugin interface.

The first five plugin variants keep coordinates, edges, factors, and arithmetic
in float64. In the two float32 variants:

* Each coordinate arrives from CorrectionLib as float64 and is rounded to
  float32 inside the node.
* Contents and numeric fallback values are rounded to float32 during
  construction. Values that cannot remain finite are rejected.
* Search thresholds are stored as float32, rounded **upward** from the original
  float64 edges. This preserves the original bin decision for coordinates
  already representable as float32. Arithmetic estimates also use float32.
* The selected factor is widened to float64 when returned. CorrectionLib's
  Python result array and the subsequent multiplication remain float64.
  There is no float32 array API or implied halving of total memory use.

The precision contract is: first round the coordinates to float32; find their
bins using the original float64 edges; round the selected factor to float32;
then widen it for return. For arbitrary float64 inputs, rounding can change
the selected bin. For example, a tiny negative number immediately below zero
can become negative zero. The [counterexample test](tests/test_nodes.py)
checks this explicitly.

Bins include their lower edge and exclude their upper edge. `clamp` flow uses
the nearest endpoint bin outside the range; numeric flow returns a configured
factor; `error` flow throws an exception. NaN follows overflow behavior, as in
the explicit-edge built-in control. The provider supports one or two axes with
finite increasing edges and finite constant contents. Histogram cells containing
formulas, interpolation, and wrap flow are outside this study.

## Measured timings

For the equal-width **20×20 table, one output, contiguous float64 input arrays**,
the following are **microseconds per complete batch**, including lookup,
result allocation, multiplication, and result disposal. Columns give the
number of items. One millisecond is 1,000 microseconds.

| Algorithm | 1 | 8 | 16 | 1,000 | 10,000 | 100,000 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| builtin | 6.019 | 7.161 | 7.362 | 49.495 | 555.754 | 5840.445 |
| binary | 6.249 | 7.131 | 7.266 | 43.574 | 492.194 | 5247.905 |
| linear | 6.376 | 7.298 | 7.145 | 33.989 | 430.381 | 4002.501 |
| tree | 6.521 | 7.102 | 7.157 | 29.191 | 241.829 | 2620.265 |
| unrolled | 6.482 | 7.066 | 7.020 | 25.431 | 206.397 | 2299.930 |
| arithmetic | 6.516 | 7.222 | 7.047 | 26.154 | 324.027 | 3326.379 |
| float32_unrolled | 6.598 | 7.020 | 7.046 | 26.977 | 213.112 | 2523.432 |
| float32_arithmetic | 6.186 | 7.171 | 6.935 | 29.078 | 327.535 | 3656.579 |

At 100,000 items, the float64 unrolled node takes **2.30 ms**, compared with
**5.84 ms** for the built-in control: about **2.5× faster** for this operation.
For 1–16 items, times are similar across searches and change little with batch
size; they do not establish a useful advantage for a particular search. This
suggests costs outside the search are important, although those costs were not
measured separately. For the same fixture, the complete scalar lookup-and-rescale
operation takes **2.66 microseconds** with unrolling, compared with
**6.48 microseconds** when passed one-element arrays.

Other workloads also favor the tree or unrolled searches. At 100,000 items,
the unequal-width 20×20 case takes **2.64 ms** with float64 unrolling versus
**5.63 ms** for the control. Sixteen independent equal-width corrections take
**35.58 ms** with unrolling versus **87.49 ms** for the control, including all
16 rescalings. Arithmetic and reduced precision do not provide a consistent
additional gain. These are single-host synthetic results, not a speedup
measurement for a complete physics analysis.

The [complete timing matrix](results/main/timing-matrix.md) includes **every
size from 1–16**, all four fixtures, 16-output calls, float32 input-array
controls, and scalar calls. [CSV](results/main/summary.csv) and
[JSON summaries](results/main/summary.json) retain means, sample standard
deviations, minima and maxima; [raw data](results/main/raw.json) retain every
round. Close median values should be read alongside that variation.

[The benchmark](scripts/benchmark.py) ran in `atlas_al9` on an Intel Core Ultra
7 265T, pinned to logical CPU 0, with numerical thread limits set to one.
A pilot chooses repetitions targeting three milliseconds per round. One warm
round is discarded; the table gives the median of seven further rounds, with
algorithm order rotated. Imports, payload loading, construction, and input
preparation are excluded. CorrectionLib's own array conversions are included.
The primary coordinates originate as float32 and are widened exactly to
float64, keeping the bin choices matched across precisions. The float32 nodes
still return rounded factors, so their rescaled results can differ from float64.

[Campaign validation](results/main/validation.json) records **944 timing rows**
and **37,341,760 exact output comparisons**, before and after timing, under each
node's stated precision contract. [Build provenance](results/build/provenance.json)
records source and library hashes, loaded libraries, compiler, and package
versions; the [core](results/build/core-compile-commands.json) and
[provider](results/build/provider-compile-commands.json) compile commands are
retained as well.

The source hashes describe the measured version, before the later axis-search
comments were added. A [comparison of code tokens and string literals](review/axis-comments-check.json)
verifies that those annotations leave the executable source unchanged.

The [correctness suite](tests/test_nodes.py) checks exact edges and neighboring
representable values, NaN and infinities, all three flow policies, singleton
axes, the 32-bin search limit, extreme scales, malformed configurations,
strided arrays, lists, broadcasting, concurrent calls, and transformed graphs.
There are **319 passing tests** in [the ordinary run](results/tests.log).
The same **319 tests pass with the provider instrumented** for undefined
behavior and float-to-integer overflow in [the sanitizer run](results/sanitizer.log).
The dependency itself is not instrumented in that run.
The independent lookup reference uses NumPy; a small
[validation-only helper](src/json_numbers.cc) reproduces the host's initial
JSON number conversion. It does no histogram search and runs outside timings.

## Reproduce in WSL2

These instructions require `atlas_al9` with access to ATLAS software on CVMFS,
Git, and system Python. They do not install WSL or configure CVMFS.

Use a fresh checkout to preserve the evidence linked above, and adjust the
checkout path below accordingly. Timing labels create new directories, but
build provenance and test logs use shared filenames that reruns replace.

From PowerShell, enter the requested distro and checkout:

```powershell
wsl -d atlas_al9
```

Then in its Bash shell:

```bash
cd /mnt/c/Users/gwatts/Code/atlas/CorrectionLibStudies
export STUDY_BUILD_ROOT=$(mktemp -d /tmp/correctionlib-node-study.XXXXXX)
bash scripts/bootstrap.sh
bash scripts/run.sh my-run
bash scripts/sanitize.sh > results/sanitizer.log 2>&1
source scripts/environment.sh
python scripts/tables.py my-run
```

The scripts use CVMFS AnalysisBase 25.2.100 for Python and GCC. Core and provider
use the same compiler, Release optimization, native CPU tuning, and disabled
floating-point contraction; fast-math is not enabled. CPU tuning means the
resulting binaries should be rebuilt on another host. The
[bootstrap](scripts/bootstrap.sh) keeps a separate `.venv`, fetches the exact
CorrectionLib commit and submodules, and compiles both wheels. The study does
not change an existing CorrectionLib installation.

Build directories default to `/tmp/correctionlib-node-study-$UID` on the Linux
filesystem, overridable with `STUDY_BUILD_ROOT`. This avoids slow extraction and
directory-rename errors on the Windows mount. Source, logs, and measurements
stay in this checkout. Give each checkout a separate build directory; the
command above creates one.

CorrectionLib is pinned to the specified commit. Other Python dependencies
are selected when bootstrap runs; the exact versions for the published results
are recorded in the build provenance. A later run may use a different environment.

ATLAS Python on this AL9 installation cannot load the host's OpenSSL for HTTPS.
Bootstrap uses system Python to download dependency wheels, then installs them
offline. An existing compatible wheel cache can be supplied with
`WHEELHOUSE=/path/to/wheels bash scripts/bootstrap.sh`. ATLAS's `PYTHONPATH` is
cleared so that packages come from this repository's virtual environment.

To replace histograms in an existing payload after building:

```bash
source scripts/environment.sh
python -m histogram_nodes.convert original.json tree.json --algorithm tree
```

For a small runnable example, use
[`examples/tiny-histogram.json`](examples/tiny-histogram.json) as `original.json`.

The [converter](python/histogram_nodes/convert.py) accepts constant `Binning`
and `MultiBinning` nodes with explicit edges and the supported flow policies.
It validates the converted graph before writing a new file and refuses to
overwrite an existing output. Its [graph test](tests/test_nodes.py) places
the replacement beneath a coordinate transform.

For continuation, read [AGENTS.md](AGENTS.md) and the running
[progress log](progress.txt).

The [fresh-context writing review](review/writing-review.md) and its
[self-contained prompt](review/writing-review-prompt.txt) are retained. Its
wording and reproduction suggestions have been incorporated.
