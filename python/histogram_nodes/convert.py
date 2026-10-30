"""Replace constant Binning/MultiBinning nodes while keeping the surrounding graph."""
import argparse
import copy
import json
import math
from pathlib import Path

from histogram_nodes import ALGORITHMS


def replace_histograms(payload, algorithm):
    if algorithm not in ALGORITHMS:
        raise ValueError(f"unknown algorithm {algorithm}")

    def visit(value):
        if isinstance(value, list):
            return [visit(child) for child in value]
        if not isinstance(value, dict):
            return value
        kind = value.get("nodetype")
        if kind in ("binning", "multibinning"):
            inputs = [value["input"]] if kind == "binning" else value["inputs"]
            edges = [value["edges"]] if kind == "binning" else value["edges"]
            flow = value["flow"]
            number = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            if (len(inputs) not in (1, 2) or any(not isinstance(a, list) or not all(number(e) for e in a) for a in edges)
                    or not all(number(c) for c in value["content"])
                    or not (number(flow) or flow in ("clamp", "error"))):
                raise ValueError("replacement requires 1D/2D constant histograms with explicit finite edges and clamp/numeric/error flow")
            return {"nodetype": "extension", "type": "study.hist."+algorithm, "version": 1,
                    "config": {"inputs": inputs, "edges": edges, "content": value["content"], "flow": flow}, "children": []}
        if kind == "extension":
            return {**value, "children": visit(value.get("children", []))}
        return {key: visit(child) for key, child in value.items()}

    return visit(copy.deepcopy(payload))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--algorithm", choices=ALGORITHMS, required=True)
    args = parser.parse_args()
    converted = replace_histograms(json.loads(args.input.read_text()), args.algorithm)
    import correctionlib
    # Fully construct the native nodes before writing a reviewable payload.
    correctionlib.CorrectionSet.from_string(json.dumps(converted))
    with args.output.open("x") as stream:
        json.dump(converted, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
