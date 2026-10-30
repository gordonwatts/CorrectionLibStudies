import copy
import json
from concurrent.futures import ThreadPoolExecutor

import correctionlib
import numpy as np
import pytest

from histogram_nodes import ALGORITHMS
from histogram_nodes.workloads import CASES, coordinates, fixture, load, numpy_reference, payload
from histogram_nodes.convert import replace_histograms

pytestmark = pytest.mark.filterwarnings("ignore:overflow encountered in cast:RuntimeWarning")


@pytest.mark.parametrize("algorithm", ("builtin", *ALGORITHMS))
@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("flow", ("clamp", -9.125))
def test_random_and_python_input_formats(algorithm, case, flow):
    cfg, _ = fixture(case, flow)
    corr = load(cfg, algorithm)["scale_0"]
    coords = coordinates(cfg, 10003, dtype="float64")
    expected = numpy_reference(cfg, coords, algorithm.startswith("float32"))
    for arguments in (coords, tuple(c.astype("float32") for c in coords),
                      tuple(c.tolist() for c in coords), tuple(np.repeat(c, 2)[::2] for c in coords)):
        np.testing.assert_array_equal(corr.evaluate(*arguments), expected)
    np.testing.assert_array_equal(corr.evaluate(*(c[::-1] for c in coords)), expected[::-1])


def edge_coordinates(edges):
    e = np.asarray(edges)
    f = e.astype(np.float32)
    return np.concatenate([e, np.nextafter(e, -np.inf), np.nextafter(e, np.inf),
                           f.astype(float), np.nextafter(f, np.float32(-np.inf)).astype(float),
                           np.nextafter(f, np.float32(np.inf)).astype(float),
                           [-np.inf, np.inf, np.nan, -0., 0., -1.e308, 1.e308]])


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("bins", (1, 2, 3, 20, 31, 32, 33, 64, 65, 1024))
@pytest.mark.parametrize("flow", ("clamp", -3.14159))
def test_edges_neighbours_singletons_and_search_fallback(algorithm, bins, flow):
    edges = np.linspace(-1.3, 2.7, bins+1)
    cfg = {"inputs": ["x"], "edges": [edges.tolist()],
           "content": (np.arange(bins)+.1234567).tolist(), "flow": flow}
    points = edge_coordinates(edges)
    corr = load(cfg, algorithm)["scale_0"]
    expected = numpy_reference(cfg, (points,), algorithm.startswith("float32"))
    np.testing.assert_array_equal(corr.evaluate(points), expected)
    quantized = points.astype(np.float32).astype(float)
    builtin = load(cfg)["scale_0"]
    reference = builtin.evaluate(quantized if algorithm.startswith("float32") else points)
    if algorithm.startswith("float32"):
        reference = reference.astype(np.float32).astype(float)
    np.testing.assert_array_equal(corr.evaluate(points), reference)
    for n in (0, 1, 2, 3, 7, 8, 15, 16, 17, 33):
        np.testing.assert_array_equal(corr.evaluate(points[:n]), expected[:n])


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_two_dimensional_boundaries(algorithm):
    cfg, _ = fixture("uneven20x20", -3.14159)
    x = edge_coordinates(cfg["edges"][0])
    y = edge_coordinates(cfg["edges"][1])
    x, y = np.meshgrid(x, y)
    corr = load(cfg, algorithm)["scale_0"]
    expected = numpy_reference(cfg, (x, y), algorithm.startswith("float32"))
    np.testing.assert_array_equal(corr.evaluate(x, y), expected)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_error_flow_scalar_broadcast_and_threads(algorithm):
    cfg, _ = fixture("fixed20x20", "error")
    corr = load(cfg, algorithm)["scale_0"]
    for value in (-np.inf, np.inf, np.nan, -99., 99.):
        with pytest.raises(RuntimeError):
            corr.evaluate(value, 1.)
        with pytest.raises(RuntimeError):
            corr.evaluate(1., value)
    for args in ((1., 1.), (np.ones(17), 1.)):
        np.testing.assert_array_equal(corr.evaluate(*args), numpy_reference(cfg, args, algorithm.startswith("float32")))
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: corr.evaluate(np.ones(33), np.ones(33)), range(16)))
    for result in results:
        np.testing.assert_array_equal(result, results[0])


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("mutation", ("short", "duplicate", "reversed", "nonfinite", "shape", "contents",
                                      "flow", "axis_count", "unknown", "duplicate_input", "input_type", "children"))
def test_reject_invalid_native_config(algorithm, mutation):
    cfg, _ = fixture("fixed64")
    data = payload(cfg, algorithm)
    c = data["corrections"][0]
    config = c["data"]["config"]
    if mutation == "short": config["edges"][0] = [0.]
    elif mutation == "duplicate": config["edges"][0][1] = config["edges"][0][0]
    elif mutation == "reversed": config["edges"][0].reverse()
    elif mutation == "nonfinite": config["edges"][0][1] = "inf"
    elif mutation == "shape": config["content"].pop()
    elif mutation == "contents": config["content"][0] = {"nodetype": "formula"}
    elif mutation == "flow": config["flow"] = "wrap"
    elif mutation == "axis_count": config["edges"] = []
    elif mutation == "unknown": config["extra"] = 1
    elif mutation == "duplicate_input": config["inputs"] = ["x", "x"]; config["edges"] *= 2
    elif mutation == "input_type": c["inputs"][0]["type"] = "int"
    elif mutation == "children": c["data"]["children"] = [1.]
    with pytest.raises((RuntimeError, ValueError)):
        correctionlib.CorrectionSet.from_string(json.dumps(data))


@pytest.mark.parametrize("algorithm", ("float32_unrolled", "float32_arithmetic"))
def test_precision_contract_and_counterexample(algorithm):
    cfg = {"inputs": ["x"], "edges": [[-1., 0., 1.]], "content": [.123456789, 1.123456789], "flow": "clamp"}
    x = np.array([np.nextafter(0., -np.inf), 0., 1.e308])
    node = load(cfg, algorithm)["scale_0"]
    np.testing.assert_array_equal(node.evaluate(x), numpy_reference(cfg, (x,), True))
    assert node.evaluate(x)[0] != np.float32(load(cfg)["scale_0"].evaluate(x)[0])
    cfg["content"][0] = 1.e100
    with pytest.raises(RuntimeError):
        load(cfg, algorithm)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_extreme_edges_and_arithmetic_repair(algorithm):
    for edges in ([1.e10, 1.e10+.1, 1.e10+.2], [-1.e308, 0., 1.e308],
                  [0., 1.e-300, 2.e-300], [-1., .10000000000000002, 1.],
                  [0., 1., 1. + 1.e-12, 3.]):
        cfg = {"inputs": ["x"], "edges": [edges], "content": list(range(1, len(edges))), "flow": "clamp"}
        x = edge_coordinates(edges)
        np.testing.assert_array_equal(load(cfg, algorithm)["scale_0"].evaluate(x),
                                      numpy_reference(cfg, (x,), algorithm.startswith("float32")))


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_replace_histogram_in_transform_graph(algorithm):
    cfg, _ = fixture("fixed64")
    original = payload(cfg)
    c = original["corrections"][0]
    # Transform changes x before the histogram reads it. This exercises the
    # host graph, not a companion evaluator outside CorrectionLib.
    c["data"] = {"nodetype": "transform", "input": "x",
                 "rule": {"nodetype": "formula", "expression": "x*2", "parser": "TFormula", "variables": ["x"]},
                 "content": c["data"]}
    converted = replace_histograms(original, algorithm)
    node = correctionlib.CorrectionSet.from_string(json.dumps(converted))["scale_0"]
    x = np.linspace(-1., 1., 101, dtype=np.float32).astype(float)
    expected = numpy_reference(cfg, (2*x,), algorithm.startswith("float32"))
    np.testing.assert_array_equal(node.evaluate(x), expected)
    assert original["corrections"][0]["data"]["content"]["nodetype"] == "multibinning"


def test_converter_binning_and_unsupported_contents():
    cfg, _ = fixture("fixed64")
    original = payload(cfg)
    data = original["corrections"][0]["data"]
    data["nodetype"] = "binning"
    data["input"] = data.pop("inputs")[0]
    data["edges"] = data["edges"][0]
    converted = replace_histograms(original, "tree")
    reference = correctionlib.CorrectionSet.from_string(json.dumps(original))["scale_0"]
    candidate = correctionlib.CorrectionSet.from_string(json.dumps(converted))["scale_0"]
    x = np.linspace(-3., 4., 107)
    np.testing.assert_array_equal(candidate.evaluate(x), reference.evaluate(x))
    data["content"][0] = {"nodetype": "formula"}
    with pytest.raises(ValueError):
        replace_histograms(original, "tree")
