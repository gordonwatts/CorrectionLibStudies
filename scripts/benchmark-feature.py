"""Matched API4 campaigns: Python operation and separately timed C++ dispatch."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import shutil
import tempfile
import time

import numpy as np

from histogram_nodes import ALGORITHMS, library, register_feature_nodes
from histogram_nodes._batch_probe import Kernel
from histogram_nodes.feature_workloads import feature_load, feature_payload, packed_reference
from histogram_nodes.workloads import CASES, SIZES, coordinates, fixture, load, numpy_reference

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("label")
    args=parser.parse_args()
    if not args.label.replace("-","").replace("_","").isalnum(): parser.error("invalid label")
    os.sched_setaffinity(0,{0})
    destination=ROOT/"results"/args.label
    destination.mkdir(exist_ok=False)
    # Windows-mounted paths can reject replacing an open/checkpoint file. Keep
    # recording on Linux, then copy each final evidence file exactly once.
    build=Path((ROOT/".build/feature-location.txt").read_text().splitlines()[1])
    out=Path(tempfile.mkdtemp(prefix=args.label+"-",dir=build))
    (destination/"recording-location.txt").write_text(str(out)+"\n")
    register_feature_nodes()
    provenance=ROOT/"results/feature-build/provenance.json"
    metadata={"core_sha":"3e907fd9eb4fe1d5946dcd161c68b2fdd2b341a5","seed":20261029,
              "cpu_affinity":sorted(os.sched_getaffinity(0)),"retained_rounds":7,"warm_rounds":1,
              "target_round_ms":2,"sizes":list(SIZES),"python_operation":"evaluate then multiply x; independent16 stacks results to dense (N,S)",
              "kernel_operation":"public C++ evaluate_batch[_array], preallocated output; no Python conversion, allocation or rescaling",
              "thread_limits":{k:os.getenv(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")},
              "provenance_sha256":hashlib.sha256(provenance.read_bytes()).hexdigest()}
    (out/"metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")
    raw=[]; summary=[]; compared=0; start=time.time()
    for case in CASES:
        cfg,_=fixture(case)
        jobs=[]
        for a in ("builtin",*ALGORITHMS,*(a+"_batch" for a in ALGORITHMS)):
            corr=feature_load(cfg,a)["scale_0"]
            kernel=Kernel(json.dumps(feature_payload(cfg,a)),str(library()))
            jobs.append((a,1,"single",corr,kernel))
        for a in ("builtin",*ALGORITHMS):
            corr=feature_load(cfg,a,16,True)["scale_0"]
            kernel=Kernel(json.dumps(feature_payload(cfg,a,16,True)),str(library()))
            jobs.append((a,16,"packed",corr,kernel))
            independent=load(cfg,a,16)
            jobs.append((a,16,"independent",tuple(independent[f"scale_{s}"] for s in range(16)),None))
            if a!="builtin":
                independent=load(cfg,a+"_batch",16)
                jobs.append((a+"_batch",16,"independent",tuple(independent[f"scale_{s}"] for s in range(16)),None))
        for n in SIZES:
            coords=coordinates(cfg,n,dtype="float64")
            for scope in ("python","kernel"):
                entries=[]
                for a,s,mode,corr,kernel in jobs:
                    if scope=="kernel" and kernel is None:continue
                    rounded=a.startswith("float32")
                    expected=numpy_reference(cfg,coords,rounded) if s==1 else packed_reference(cfg,coords,s,rounded)
                    if scope=="python":
                        if mode=="independent":fn=lambda corr=corr:np.stack([c.evaluate(*coords) for c in corr],axis=-1)*coords[0][:,None]
                        elif s==1:fn=lambda corr=corr:corr.evaluate(*coords)*coords[0]
                        else:fn=lambda corr=corr:corr.evaluate(*coords)*coords[0][:,None]
                        expected=expected*(coords[0] if s==1 else coords[0][:,None])
                        def timed(repeats,fn=fn):
                            begin=time.perf_counter_ns()
                            for _ in range(repeats):fn()
                            return (time.perf_counter_ns()-begin)/repeats
                        get=fn
                    else:
                        timed=lambda repeats,kernel=kernel:kernel.run(list(coords),n,repeats)[0]
                        get=lambda kernel=kernel:kernel.run(list(coords),n)[1]
                    np.testing.assert_array_equal(get(),expected);compared+=expected.size
                    pilot=timed(3)
                    repeats=max(1,min(20000,math.ceil(2e6/max(1,pilot))))
                    entries.append((a,s,mode,timed,get,expected,repeats,[]))
                for r in range(8):
                    rotated=entries[r%len(entries):]+entries[:r%len(entries)]
                    for a,s,mode,timed,get,expected,repeats,rounds in rotated:
                        elapsed=timed(repeats);rounds.append(elapsed)
                        raw.append({"case":case,"items":n,"components":s,"mode":mode,"scope":scope,"algorithm":a,"round":r,"repeats":repeats,"ns":elapsed})
                for a,s,mode,timed,get,expected,repeats,rounds in entries:
                    np.testing.assert_array_equal(get(),expected);compared+=expected.size
                    samples=rounds[1:]
                    summary.append({"case":case,"items":n,"components":s,"mode":mode,"scope":scope,"algorithm":a,"median_us":statistics.median(samples)/1000,"min_us":min(samples)/1000,"max_us":max(samples)/1000,"stdev_us":statistics.stdev(samples)/1000})
            (out/"raw.json").write_text(json.dumps(raw,indent=2)+"\n")
            (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
        print(f"completed {case}",flush=True)
    with (out/"summary.csv").open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    validation={"status":"passed","rows":len(summary),"round_records":len(raw),"exact_comparisons":compared,"elapsed_seconds":time.time()-start}
    (out/"validation.json").write_text(json.dumps(validation,indent=2)+"\n")
    for source in out.iterdir():
        shutil.copyfile(source,destination/source.name)
    print(json.dumps(validation),flush=True)


if __name__=="__main__":main()
