# Histogram lookups with native batches and fixed arrays

This study asks how much faster a histogram lookup can be when CorrectionLib
passes a whole set of particles to a C++ node, and when one declared correction
returns several factors from the same bin. The examples are synthetic tables,
not detector calibrations or full-analysis validation.

The current dependency is the experimental `develop` branch of
[gordonwatts/correctionlib](https://github.com/gordonwatts/correctionlib), pinned
and rebuilt at [`3e907fd9`](https://github.com/gordonwatts/correctionlib/commit/3e907fd9eb4fe1d5946dcd161c68b2fdd2b341a5).
Core and provider use the same GCC 15.2 toolchain and SDK API4. The ordinary
PyPI package does not supply these interfaces. The original scalar-SDK study,
its measurements and reproduction instructions remain in
[README-scalar.md](README-scalar.md), [results/main](results/main/) and
[results/build](results/build/). Its 319 tests remain unchanged and run in the
new suite too. Historical reproduction requires study commit `9ae3d72` in a
separate checkout; the old `bootstrap.sh` targets that source, not current API4.

## What changes for the caller

Python still uses `evaluate(...)`. One input point gets one scalar result from a
scalar correction. Arrays of coordinates get an array of scalar results. A new
native callback lets the node process those coordinates in one C++ loop:

```python
from histogram_nodes.feature_workloads import feature_load
from histogram_nodes.workloads import fixture
import numpy as np

config, _ = fixture("fixed20x20")
scalar = feature_load(config, "unrolled")["scale_0"]
batch = feature_load(config, "unrolled_batch")["scale_0"]
x = np.array([0., 1., 2.])
scalar.evaluate(1., 1.)       # one factor, existing scalar implementation
batch.evaluate(1., 1.)        # the same scalar implementation
batch.evaluate(x, 1.)         # three factors through the native batch callback
```

The old names remain controls: their array calls use the SDK's per-point scalar
fallback. Each `_batch` node has the same scalar method, search policy, table,
flow and precision. Its callback removes per-point assignment into an argument vector and
virtual scalar calls, and resolves the axes outside the loop. Each coordinate
still requires a search. Nested graphs, such as a histogram beneath Transform,
can use scalar fallback rather than the root-node batch fast path.

A separate `_packed` node declares a fixed array output in schema v3. It finds
one bin per point and copies that bin's S factors into one row, where S is the
declared number of components. This explicit
layout creates search reuse across components. It does not request several
systematic selectors or combine independently named corrections. The factors
could represent variations only if the payload author assigns that meaning.

```python
import correctionlib
packed = correctionlib.CorrectionSet.from_file(
    "examples/packed-histogram.json")["three_factors"]
packed.evaluate(0.25)                         # shape (3,)
packed.evaluate(np.array([0.25, 1.25]))        # shape (2, 3)
```

The [runnable example](examples/native-batch.py) checks both forms. The
[small payload](examples/packed-histogram.json) shows the output declaration
`shape: [3]`, extension `output_shape: [3]`, and bin-major contents. The provider
accepts 1D or 2D explicit-edge tables, clamp/error/finite numeric flow, and at
most 1,048,576 stored components. For packed tables a numeric configured flow
fills every component with that value; built-in array payloads express this
with an explicit array-valued flow node.

## Search methods and precision

Each search policy stays in its own [src/nodes](src/nodes/) file: binary search,
linear scan, padded tree, five-step unrolled tree, and guarded arithmetic with
exact-edge repair, plus float32 versions of unrolled and arithmetic. Unrolled
uses the general tree above 32 bins. Arithmetic falls back for uneven axes.
[Shared code](src/table.h) handles batch loops, flow and row-major indexing;
[parsing](src/table.cc) validates geometry and shape when loading.

Double nodes retain double coordinates, edges and contents. Float32 nodes round
coordinates, contents, numeric fallback, and arithmetic intermediates to
float32; edges become the smallest float32 threshold at or above each stored
double edge. Results widen to double. Arbitrary double coordinates can therefore
change bin under rounding. This is a provider precision choice, not a float32
Python API. Inputs in the campaign originate as float32 and widen exactly to
double, permitting exact comparisons under that stated precision contract.
There is no explicit SIMD or worker threading in these implementations. The
public SDK exposes `BatchInput.at(row)` rather than raw typed column pointers.

## Measurements

At 100,000 items, **Python lookup and rescaling**, median of seven rounds in milliseconds:

| Table | Built-in native batch | Unrolled scalar fallback | Unrolled native batch | Arithmetic native batch |
|---|---:|---:|---:|---:|
| fixed64 | 3.230 | 1.156 | 0.878 | 0.872 |
| uneven64 | 2.947 | 1.220 | 0.911 | 0.887 |
| fixed20x20 | 5.047 | 1.472 | 1.051 | 2.101 |
| uneven20x20 | 4.667 | 1.458 | 1.080 | 1.428 |

For fixed20x20, native batching improves the same unrolled scalar-output node
from **1.472 ms to 1.051 ms (1.40x)**. For 16 factors per item, 16 independent
unrolled native-batch corrections take **22.722 ms**, versus **2.591 ms** for
one packed unrolled correction: **8.77x**, including the different allocation
and stacking paths described below. Retained ranges are 22.454–25.229 ms and
2.382–2.954 ms respectively. The built-in packed16 control takes 7.758 ms.

In the separate C++ kernel scope, fixed20x20 unrolled scalar fallback takes
**1.334 ms**, native batch **0.961 ms**, and packed16 **1.095 ms**. These are
different output workloads; the last number is throughput evidence, not a
native packed-versus-independent16 speedup. Arithmetic and float32 do not
consistently outperform the double unrolled node.

The accepted campaign contains **4,636 timing rows**, **37,088 raw rounds**
(4,636 warm and 32,452 retained), and **467,660,288 exact comparisons**. The first attempt failed during a
Windows-mounted filesystem checkpoint; its [partial evidence](results/feature-main/FAILED.txt)
is explicitly excluded. The accepted retry records on Linux before copying
final evidence into the checkout.

The complete [campaign CSV](results/feature-main-2/summary.csv),
[raw rounds](results/feature-main-2/raw.json),
[metadata](results/feature-main-2/metadata.json), and
[validation counts](results/feature-main-2/validation.json) retain every result.
All four fixtures use the existing synthetic data: fixed/uneven 64-bin 1D and
20x20 2D tables. Every size 1 through 16, then 1,000, 10,000 and 100,000, is
measured for all seven methods and controls. All results are checked exactly
before and after timing. Algorithm order rotates; one warm round and seven
retained rounds use CPU0 with one numerical thread and no concurrent build.
Raw data retain repeat counts and the full round spread.

The two timing scopes answer different questions:

- **Python operation:** coordinate conversion/broadcasting inside CorrectionLib,
  output allocation, evaluation, multiplication by x, and temporary disposal.
  The 16-independent-correction case stacks its 16 arrays into dense `(N,16)`
  output before multiplying. Packed16 returns that layout directly. The
  comparison includes that allocation/stacking difference as well as search
  reuse; it is not an isolated measurement of bin sharing.
- **C++ kernel:** the public `evaluate_batch` or `evaluate_batch_array` call into
  a preallocated output buffer, including core validation. Inputs and output
  allocation, Python conversion, rescaling and copying the final check array
  are outside the clock. The [adapter](src/batch_probe.cc) retains the correction
  while destroying its factory registry and CorrectionSet. No independent16
  kernel is timed, so packed kernel times do not establish a matched native
  packed-versus-independent speedup. The two scopes are measured independently;
  cache and execution context can differ, so their times are not an additive
  breakdown and should not be subtracted to estimate Python overhead.

Current built-in histogram nodes also receive native batches on develop. Ratios
in this campaign compare current implementations on the same core. Historical
[PR1 timings](README-scalar.md) used a different core and remain separate evidence.

## Validation and reproduction

The [new tests](tests/test_batches.py) compare every batch method with its scalar
control and check packed results against an independent NumPy oracle. Coverage
includes edges and neighbours, NaN/infinities, flow, one-component arrays,
multidimensional broadcasting, empty inputs, threads, invalid shapes/types,
signed/zero native strides, insufficient/null output, buffer canaries, owning
lifetimes and Transform fallback. Python may copy strided arrays; the C++ probe
separately passes actual strided borrowed columns. Borrowed inputs must stay
alive and unchanged until return, and output must not alias inputs. Discard
partial output after exceptions. The [feature test log](results/feature-tests.log)
and [provider sanitizer log](results/feature-sanitizer.log) retain the checks.
Sanitizer coverage applies to the provider, not the entire core dependency.

Run builds, tests and timings in WSL2 `atlas_al9` with CVMFS AnalysisBase 25.2.100:

```powershell
wsl -d atlas_al9
```

```bash
cd /mnt/c/Users/gwatts/Code/atlas/CorrectionLibStudies
export FEATURE_BUILD_ROOT=$(mktemp -d /tmp/correctionlib-batch-study.XXXXXX)
bash scripts/bootstrap-feature.sh
bash scripts/sanitize-feature.sh > results/feature-sanitizer.log 2>&1
bash scripts/run-feature.sh my-new-feature-run
source scripts/feature-environment.sh
python examples/native-batch.py
```

Give every checkout a separate Linux build directory. Bootstrap uses the pinned
core source and submodules, `.venv-feature`, `dist-feature`, and the feature
build directory. A clean existing source at the exact pin can be supplied with
`FEATURE_CORE_SOURCE=/path/to/checkout`; it is read-only. Use
`WHEELHOUSE=/path/to/compatible/wheels` for offline dependencies. By default,
system Python downloads wheels because ATLAS Python's OpenSSL cannot load on
this host. Other Python dependencies are selected at bootstrap; the exact
installed versions, source/binary hashes, compiler commands and environment
are in [feature provenance](results/feature-build/provenance.json).

Core and provider use Release/O3, native CPU tuning and `-ffp-contract=off`, with
no fast-math. Rebuild binaries on another host. Existing campaign directories
are never overwritten; choose a new label. Feature test/build/provenance log
names are shared and will be replaced on rerun, so preserve them before another
build. The original `results/main` and `results/build` files remain untouched.

The clean-context agent's [API documentation assessment](review/feature/documentation-usability.md)
records questions before public-header fallback. The requested separate writing
review is retained in [review/feature/writing-review.md](review/feature/writing-review.md). Read
[AGENTS.md](AGENTS.md) and [progress.txt](progress.txt) before continuing.
