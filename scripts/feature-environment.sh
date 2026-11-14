#!/usr/bin/env bash
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source "$ATLAS_LOCAL_ROOT_BASE/user/atlasLocalSetup.sh" --quiet
asetup AnalysisBase,25.2.100 >/dev/null
unset PYTHONPATH
STUDY_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
if [[ -f "$STUDY_ROOT/.venv-feature/bin/activate" ]]; then
  source "$STUDY_ROOT/.venv-feature/bin/activate"
fi
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
