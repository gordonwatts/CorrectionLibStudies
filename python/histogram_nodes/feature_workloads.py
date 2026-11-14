"""Additive API4 workloads; historical scalar fixtures stay unchanged."""
import copy
import json

import numpy as np

from . import register_feature_nodes
from .workloads import numpy_reference, payload


def feature_payload(config, algorithm, components=1, packed=False):
    data = payload(config, algorithm, 1)
    if not packed:
        return data
    data["schema_version"] = 3
    corr = data["corrections"][0]
    corr["output"]["shape"] = [components]
    node = corr["data"]
    rows = [[v+s*0.000017 for s in range(components)] for v in config["content"]]
    if algorithm == "builtin":
        node["content"] = [{"nodetype": "array", "content": r} for r in rows]
        if isinstance(config["flow"], (int, float)):
            node["flow"] = {"nodetype": "array", "content": [config["flow"]]*components}
    else:
        node["type"] += "_packed"
        node["output_shape"] = [components]
        node["config"]["content"] = [v for r in rows for v in r]
    return data


def feature_load(config, algorithm, components=1, packed=False):
    import correctionlib
    register_feature_nodes()
    return correctionlib.CorrectionSet.from_string(json.dumps(feature_payload(config, algorithm, components, packed)))


def packed_reference(config, coords, components, rounded=False):
    values = []
    for s in range(components):
        cfg = copy.deepcopy(config)
        cfg["content"] = [v+s*0.000017 for v in cfg["content"]]
        values.append(numpy_reference(cfg, coords, rounded))
    return np.stack(values, axis=-1)
