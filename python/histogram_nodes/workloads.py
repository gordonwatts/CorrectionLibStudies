"""Synthetic, dimensionless calibration factors; no external physics files."""
import copy
import json

import numpy as np

from histogram_nodes import ALGORITHMS

CASES = ("fixed64", "uneven64", "fixed20x20", "uneven20x20")
SIZES = (*range(1, 17), 1000, 10000, 100000)


def fixture(case, flow="clamp", outputs=1):
    two_d = "20x20" in case
    bins = 20 if two_d else 64
    u = np.linspace(0., 1., bins + 1)
    edges = -2. + 5. * (u**1.7 if case.startswith("uneven") else u)
    axes = [edges.tolist()]
    if two_d:
        axes.append((edges * 2. + 0.3).tolist())
    count = bins ** len(axes)
    # Non-float32-exact factors expose content rounding, while unique values
    # allow boundary tests to detect choosing the wrong bin.
    content = (0.8 + np.arange(count) * 0.000731).tolist()
    return {"inputs": ["x", "y"][:len(axes)], "edges": axes,
            "content": content, "flow": flow}, outputs


def payload(config, algorithm="builtin", outputs=1):
    corrections = []
    for output in range(outputs):
        cfg = copy.deepcopy(config)
        cfg["content"] = [v + output * 0.000017 for v in cfg["content"]]
        if algorithm == "builtin":
            data = {"nodetype": "multibinning", **cfg}
        else:
            data = {"nodetype": "extension", "type": "study.hist." + algorithm,
                    "version": 1, "config": cfg, "children": []}
        corrections.append({"name": f"scale_{output}", "version": 1,
                            "inputs": [{"name": name, "type": "real"} for name in cfg["inputs"]],
                            "output": {"name": "factor", "type": "real"}, "data": data})
    return {"schema_version": 2, "description": "Synthetic histogram scale study", "corrections": corrections}


def load(config, algorithm="builtin", outputs=1):
    import correctionlib
    return correctionlib.CorrectionSet.from_string(json.dumps(payload(config, algorithm, outputs)))


def coordinates(config, n, seed=20261029, dtype="float32"):
    rng = np.random.default_rng(seed)
    # Generate float32 coordinates, then widen exactly to float64 for the
    # matched path. Include under/overflow to exercise clamp flow in timings.
    result = []
    for edges in config["edges"]:
        span = edges[-1] - edges[0]
        values = rng.uniform(edges[0] - .1*span, edges[-1] + .1*span, n).astype(np.float32)
        result.append(values.astype(dtype))
    return tuple(result)


def numpy_reference(config, coords, rounded=False):
    from histogram_nodes._json_numbers import parsed_numbers
    # The host's fast JSON reader may differ from Python's float conversion by
    # one ULP. Use the numbers the host actually sees, then do the independent
    # lookup in NumPy. This helper contains no histogram search implementation.
    config = json.loads(parsed_numbers(json.dumps(config)))
    values = [np.asarray(x, dtype=np.float32).astype(np.float64) if rounded
              else np.asarray(x, dtype=np.float64) for x in coords]
    flat = np.zeros(np.broadcast_shapes(*(x.shape for x in values)), dtype=np.int64)
    outside = np.zeros_like(flat, dtype=bool)
    for edges, x in zip(config["edges"], values):
        outside |= (x < edges[0]) | ~(x < edges[-1])
        index = np.clip(np.searchsorted(edges, x, side="right") - 1, 0, len(edges)-2)
        flat = flat * (len(edges)-1) + index
    contents = np.asarray(config["content"])
    result = contents[flat]
    if isinstance(config["flow"], (int, float)):
        result = np.where(outside, config["flow"], result)
    elif config["flow"] == "error" and np.any(outside):
        raise ValueError("outside")
    if rounded:
        result = result.astype(np.float32).astype(np.float64)
    return result


def evaluate_rescaled(corrections, coords):
    # Allocation, each CorrectionLib call, multiplication, and disposal of
    # intermediate factor arrays are inside the measured Python operation.
    return tuple(c.evaluate(*coords) * coords[0] for c in corrections)
