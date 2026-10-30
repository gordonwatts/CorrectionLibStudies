"""Python discovery only; every lookup runs inside the native provider."""
from pathlib import Path

from correctionlib.plugins import NodePlugin

ALGORITHMS = (
    "binary", "linear", "tree", "unrolled", "arithmetic",
    "float32_unrolled", "float32_arithmetic",
)


def library():
    return Path(__file__).with_name("libhistogram_nodes.so")


def provider():
    # Native validation is authoritative, including for non-Python consumers.
    return NodePlugin(library())
