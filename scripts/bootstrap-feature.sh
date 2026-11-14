#!/usr/bin/env bash
cd "$(dirname "$0")/.." || exit 1
source scripts/feature-environment.sh
set -euo pipefail
sha=3e907fd9eb4fe1d5946dcd161c68b2fdd2b341a5
core="${FEATURE_CORE_SOURCE:-$PWD/_deps/correctionlib-feature}"
build="${FEATURE_BUILD_ROOT:-/tmp/correctionlib-batch-study-$UID}"
if [[ ! -d "$core/.git" ]]; then
  git clone --recurse-submodules https://github.com/gordonwatts/correctionlib.git "$core"
  git -C "$core" checkout --detach "$sha"
  git -C "$core" submodule update --init --recursive
fi
[[ "$(git -C "$core" rev-parse HEAD)" == "$sha" ]]
[[ -z "$(git -C "$core" status --porcelain)" ]]
mkdir -p results/feature-build dist-feature "$build" .build
printf '%s\n%s\n' "$core" "$build" > .build/feature-location.txt
if [[ ! -f .venv-feature/bin/activate ]]; then python -m venv .venv-feature; fi
source .venv-feature/bin/activate
wheelhouse="${WHEELHOUSE:-$PWD/_deps/wheels}"
packages=(pip==25.3 scikit-build-core setuptools-scm pybind11 numpy pydantic rich packaging pytest)
if [[ -z "${WHEELHOUSE:-}" ]]; then
  /usr/bin/python3 scripts/fetch_wheels.py "$wheelhouse" "${packages[@]}"
fi
python -m pip install --no-index --find-links="$wheelhouse" "${packages[@]}"
export CMAKE_BUILD_PARALLEL_LEVEL=2
python -m pip wheel --no-index --no-deps --no-build-isolation "$core" -w dist-feature -v \
  -Cbuild-dir="$build/core" -Ccmake.define.CMAKE_EXPORT_COMPILE_COMMANDS=ON \
  '-Ccmake.define.CMAKE_CXX_FLAGS=-march=native -ffp-contract=off' \
  2>&1 | tee results/feature-build/core.log
python -m pip install --no-index --force-reinstall --no-deps dist-feature/correctionlib-*.whl
export CMAKE_PREFIX_PATH="$(python -c 'import correctionlib,pathlib; print(pathlib.Path(correctionlib.__file__).parent)'):${CMAKE_PREFIX_PATH:-}"
python -m pip wheel --no-index --no-deps --no-build-isolation . -w dist-feature -v \
  -Cbuild-dir="$build/provider" -Ccmake.define.CMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -Ccmake.define.RAPIDJSON_INCLUDE_DIR="$core/rapidjson/include" \
  2>&1 | tee results/feature-build/provider.log
python -m pip install --no-index --force-reinstall --no-deps dist-feature/histogram_node_study-*.whl
