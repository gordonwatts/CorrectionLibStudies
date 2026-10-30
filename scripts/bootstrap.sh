#!/usr/bin/env bash
cd "$(dirname "$0")/.."
source scripts/environment.sh
set -euo pipefail
sha=8dc0b7a8bfe82c15115ff2a5907d4bfa35ee4710
mkdir -p _deps results/build
export STUDY_BUILD_ROOT="${STUDY_BUILD_ROOT:-/tmp/correctionlib-node-study-$UID}"
mkdir -p .build "$STUDY_BUILD_ROOT"
printf '%s\n' "$STUDY_BUILD_ROOT" > .build/location.txt
if [[ ! -d _deps/correctionlib/.git ]]; then
    git clone https://github.com/gordonwatts/correctionlib.git _deps/correctionlib
fi
git -C _deps/correctionlib checkout --detach "$sha"
git -C _deps/correctionlib submodule update --init --recursive --jobs 4
if [[ ! -f .venv/bin/activate ]]; then python -m venv .venv; fi
source .venv/bin/activate
export PIP_DISABLE_PIP_VERSION_CHECK=1
python -m ensurepip --upgrade
# The ATLAS Python SSL extension needs a newer OpenSSL than this AL9 host.
# Download compatible wheels with the system Python, then install offline.
wheelhouse="${WHEELHOUSE:-$PWD/_deps/wheels}"
packages=(pip==25.3 scikit-build-core setuptools-scm pybind11 numpy pydantic rich packaging pytest)
if [[ -z "${WHEELHOUSE:-}" ]]; then
    mkdir -p "$wheelhouse"
    /usr/bin/python3 scripts/fetch_wheels.py "$wheelhouse" "${packages[@]}"
fi
python -m pip install --no-index --find-links="$wheelhouse" --upgrade "${packages[@]}"
export CMAKE_BUILD_PARALLEL_LEVEL=2
python -m pip wheel --no-index --no-deps --no-build-isolation ./_deps/correctionlib -w dist -v \
    -Cbuild-dir="$STUDY_BUILD_ROOT/core" -Ccmake.define.CMAKE_EXPORT_COMPILE_COMMANDS=ON \
    '-Ccmake.define.CMAKE_CXX_FLAGS=-march=native -ffp-contract=off' \
    2>&1 | tee results/build/core.log
python -m pip install --no-index --force-reinstall --no-deps dist/correctionlib-*.whl
export CMAKE_PREFIX_PATH="$(python -c 'import correctionlib,pathlib; print(pathlib.Path(correctionlib.__file__).parent)'):${CMAKE_PREFIX_PATH:-}"
python -m pip wheel --no-index --no-deps --no-build-isolation . -w dist -v \
    -Cbuild-dir="$STUDY_BUILD_ROOT/provider" -Ccmake.define.CMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -Ccmake.define.RAPIDJSON_INCLUDE_DIR="$PWD/_deps/correctionlib/rapidjson/include" \
    2>&1 | tee results/build/provider.log
python -m pip install --no-index --force-reinstall --no-deps dist/histogram_node_study-*.whl
python scripts/provenance.py
