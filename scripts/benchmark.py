"""Measure complete Python lookup-and-rescale calls, retaining every round."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import time

import numpy as np

from histogram_nodes import ALGORITHMS
from histogram_nodes.workloads import CASES, SIZES, coordinates, evaluate_rescaled, fixture, load, numpy_reference

ROOT = Path(__file__).resolve().parents[1]


def measure(function, repeats):
    start = time.perf_counter_ns()
    for _ in range(repeats):
        # Each return is discarded here, so result disposal is timed as well.
        function()
    return (time.perf_counter_ns() - start) / repeats


def check(function, config, coords, outputs, algorithm):
    actual = function()
    comparisons = 0
    for s in range(outputs):
        cfg = {**config, "content": [v + s * 0.000017 for v in config["content"]]}
        expected = numpy_reference(cfg, coords, algorithm.startswith("float32")) * coords[0]
        np.testing.assert_array_equal(actual[s], expected)
        comparisons += np.size(expected)
    return comparisons


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("label", help="New results subdirectory; existing evidence is preserved")
    parser.add_argument("--cpu", type=int, default=0)
    args = parser.parse_args()
    if not args.label.replace("-", "").replace("_", "").isalnum():
        parser.error("label must contain letters, numbers, hyphens or underscores")
    os.sched_setaffinity(0, {args.cpu})
    out = ROOT / "results" / args.label
    out.mkdir(exist_ok=False)
    algorithms = ("builtin", *ALGORITHMS)
    jobs = [(case, outputs, dtype, "array") for case, outputs, dtype in
            [(c, 1, "float64") for c in CASES] +
            [("fixed20x20", 16, "float64"), ("fixed20x20", 1, "float32")]]
    jobs += [(c, 1, "float64", "scalar") for c in CASES]
    records, summary = [], []
    total_compared = 0
    begin = time.time()
    metadata = {"seed": 20261029, "cpu_affinity": sorted(os.sched_getaffinity(0)),
                "retained_rounds": 7, "discarded_warm_rounds": 1,
                "target_round_ms": 3, "sizes": list(SIZES),
                "operation": "tuple(c.evaluate(*coords) * coords[0] for each independent output)",
                "units": "nanoseconds per complete Python operation, all outputs",
                "thread_limits": {key: os.getenv(key) for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
                "build_provenance_sha256": hashlib.sha256((ROOT/"results/build/provenance.json").read_bytes()).hexdigest()}
    (out/"metadata.json").write_text(json.dumps(metadata, indent=2)+"\n")
    for case, outputs, dtype, kind in jobs:
        config, _ = fixture(case)
        loaded = {a: load(config, a, outputs) for a in algorithms}
        corrections = {a: tuple(loaded[a][f"scale_{s}"] for s in range(outputs)) for a in algorithms}
        for n in (SIZES if kind == "array" else (1,)):
            coords = coordinates(config, n, dtype=dtype)
            if kind == "scalar":
                coords = tuple(float(x[0]) for x in coords)
            functions = {a: (lambda a=a: evaluate_rescaled(corrections[a], coords)) for a in algorithms}
            repeats, rounds = {}, {a: [] for a in algorithms}
            for a in algorithms:
                total_compared += check(functions[a], config, coords, outputs, a)
                pilot = measure(functions[a], 3)
                repeats[a] = max(1, min(5000, math.ceil(3.e6 / max(pilot, 1))))
            for round_index in range(8):
                order = algorithms[round_index % len(algorithms):] + algorithms[:round_index % len(algorithms)]
                for a in order:
                    elapsed = measure(functions[a], repeats[a])
                    rounds[a].append(elapsed)
                    records.append({"case": case, "items": n, "outputs": outputs, "input_dtype": dtype,
                                    "call_kind": kind, "algorithm": a, "round": round_index,
                                    "repeats": repeats[a], "ns_per_batch": elapsed})
            for a in algorithms:
                total_compared += check(functions[a], config, coords, outputs, a)
                samples = rounds[a][1:]
                summary.append({"case": case, "items": n, "outputs": outputs, "input_dtype": dtype,
                                "call_kind": kind, "algorithm": a, "median_us": statistics.median(samples)/1000,
                                "mean_us": statistics.mean(samples)/1000, "stdev_us": statistics.stdev(samples)/1000,
                                "min_us": min(samples)/1000, "max_us": max(samples)/1000})
            # Checkpoint each workload for resumable evidence if interrupted.
            (out/"raw.json").write_text(json.dumps(records, indent=2)+"\n")
            (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
        print(f"completed {case}, outputs={outputs}, {dtype}, {kind}", flush=True)
    with (out/"summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    validation = {"status": "passed", "rows": len(summary), "round_records": len(records),
                  "output_comparisons_before_and_after": total_compared,
                  "elapsed_seconds": time.time()-begin}
    (out/"validation.json").write_text(json.dumps(validation, indent=2)+"\n")
    print(json.dumps(validation), flush=True)


if __name__ == "__main__":
    main()
