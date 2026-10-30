"""Python discovery only; every lookup runs inside the native provider."""
from pathlib import Path
import os

from correctionlib.plugins import NodePlugin

ALGORITHMS = (
    "binary", "linear", "tree", "unrolled", "arithmetic",
    "float32_unrolled", "float32_arithmetic",
)


def library():
    return Path(os.environ.get("HISTOGRAM_STUDY_LIBRARY", Path(__file__).with_name("libhistogram_nodes.so")))


def provider():
    # Native validation is authoritative, including for non-Python consumers.
    return NodePlugin(library())


def register_feature_nodes():
    """Explicit loading also registers batch/packed names with native consumers."""
    import correctionlib
    correctionlib.plugins.load_library(library())
