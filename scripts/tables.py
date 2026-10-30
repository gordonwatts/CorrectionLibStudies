"""Render measured values; never type timings into documentation by hand."""
import json
from pathlib import Path
import sys

from histogram_nodes import ALGORITHMS

root = Path(__file__).resolve().parents[1]
directory = root / "results" / sys.argv[1]
rows = json.loads((directory/"summary.json").read_text())
algorithms = ("builtin", *ALGORITHMS)


def table(subset, sizes):
    lookup = {(r["algorithm"], r["items"]): r["median_us"] for r in subset}
    lines = ["| Algorithm | " + " | ".join(f"{n:,}" for n in sizes) + " |",
             "| --- | " + " | ".join("---:" for _ in sizes) + " |"]
    for a in algorithms:
        lines.append("| " + a + " | " + " | ".join(f"{lookup[a,n]:.3f}" for n in sizes) + " |")
    return "\n".join(lines)


groups = list(dict.fromkeys((r["case"], r["outputs"], r["input_dtype"], r["call_kind"]) for r in rows))
text = ["# Complete timing matrix", "", "All values are median microseconds per complete Python lookup-and-rescale operation, including every output. Columns give the number of items. Round zero is discarded; seven rounds remain. See raw.json and summary.csv for samples and spread.", ""]
for group in groups:
    subset = [r for r in rows if (r["case"], r["outputs"], r["input_dtype"], r["call_kind"]) == group]
    sizes = sorted({r["items"] for r in subset})
    text += [f"## {group[0]} / {group[1]} outputs / {group[2]} / {group[3]}", "", table(subset, sizes), ""]
(directory/"timing-matrix.md").write_text("\n".join(text))
primary = [r for r in rows if r["case"] == "fixed20x20" and r["outputs"] == 1
           and r["input_dtype"] == "float64" and r["call_kind"] == "array"]
(directory/"readme-table.md").write_text(table(primary, (1, 8, 16, 1000, 10000, 100000))+"\n")
print(table(primary, (1, 8, 16, 1000, 10000, 100000)))
