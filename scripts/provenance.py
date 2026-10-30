"""Record what was actually built; rerun after any source change."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

import correctionlib
import numpy as np
from histogram_nodes import library
from histogram_nodes.workloads import fixture, load

ROOT = Path(__file__).resolve().parents[1]


def command(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def hashes(paths):
    return {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file()}


core = Path(correctionlib.__file__).parent
build_root = Path((ROOT/".build/location.txt").read_text().strip())
load(fixture("fixed64")[0], "binary")
metadata = {
    "correctionlib_commit": command("git", "-C", "_deps/correctionlib", "rev-parse", "HEAD"),
    "correctionlib_source_status": command("git", "-C", "_deps/correctionlib", "status", "--porcelain"),
    "submodules": command("git", "-C", "_deps/correctionlib", "submodule", "status", "--recursive"),
    "python": sys.version, "python_executable": sys.executable,
    "correctionlib_version": correctionlib.__version__, "correctionlib_path": str(core),
    "numpy_version": np.__version__, "compiler": command("c++", "--version"),
    "cmake": command("cmake", "--version"), "uname": platform.uname()._asdict(),
    "cpu": command("lscpu"), "pip_freeze": command(sys.executable, "-m", "pip", "freeze"),
    "binary_sha256": hashes([library(), *library().parent.glob("_json_numbers*.so"),
                              *core.glob("lib/*.so"), *core.glob("_core*.so"), *ROOT.glob("dist/*.whl")]),
    "source_sha256": hashes([*ROOT.glob("src/**/*.cc"), *ROOT.glob("src/**/*.h"),
                              *ROOT.glob("python/**/*.py"), *ROOT.glob("scripts/*.py"),
                              *ROOT.glob("scripts/*.sh"), *ROOT.glob("tests/*.py"),
                              ROOT/"CMakeLists.txt", ROOT/"pyproject.toml"]),
    "provider_flags": "Release -O3 -march=native -ffp-contract=off; no fast-math",
    "core_flags": "Release -O3 -march=native -ffp-contract=off; no fast-math",
    "atlas_release": "AnalysisBase,25.2.100", "wsl_distro": os.getenv("WSL_DISTRO_NAME"),
    "build_root": str(build_root),
    "loaded_libraries": sorted({line.split()[-1] for line in Path("/proc/self/maps").read_text().splitlines()
                                if "libcorrectionlib" in line or "libhistogram_nodes" in line or "correctionlib/_core" in line}),
}
out = ROOT / "results/build/provenance.json"
out.write_text(json.dumps(metadata, indent=2) + "\n")
for component in ("core", "provider"):
    source = build_root / component / "compile_commands.json"
    if source.exists():
        shutil.copyfile(source, out.with_name(f"{component}-compile-commands.json"))
print(f"Wrote {out}")
