import copy
import json
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from histogram_nodes import ALGORITHMS, library
from histogram_nodes._batch_probe import Kernel
from histogram_nodes.feature_workloads import feature_load, feature_payload, packed_reference
from histogram_nodes.workloads import CASES, coordinates, fixture, numpy_reference
from test_nodes import edge_coordinates

pytestmark = pytest.mark.filterwarnings("ignore:overflow encountered in cast:RuntimeWarning")


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("flow", ("clamp", -3.125, "error"))
def test_matched_scalar_batch(algorithm, case, flow):
    cfg, _ = fixture(case, flow)
    scalar = feature_load(cfg, algorithm)["scale_0"]
    batch = feature_load(cfg, algorithm+"_batch")["scale_0"]
    coords = coordinates(cfg, 1003, dtype="float64")
    if flow == "error":
        coords = tuple(np.clip(x, e[0]+.01, e[-1]-.01) for x, e in zip(coords,cfg["edges"]))
    np.testing.assert_array_equal(batch.evaluate(*coords),scalar.evaluate(*coords))
    for n in (0,1,2,16,33):
        np.testing.assert_array_equal(batch.evaluate(*(x[:n] for x in coords)),scalar.evaluate(*(x[:n] for x in coords)))
    np.testing.assert_array_equal(batch.evaluate(*(float(x[0]) for x in coords)),scalar.evaluate(*(float(x[0]) for x in coords)))
    if flow != "error":
        points=tuple(edge_coordinates(e) for e in cfg["edges"])
        np.testing.assert_array_equal(batch.evaluate(*points),scalar.evaluate(*points))
    else:
        for bad in (-np.inf,np.inf,np.nan,-1.e308,1.e308):
            args=[x[:3].copy() for x in coords]; args[-1][1]=bad
            with pytest.raises(RuntimeError): batch.evaluate(*args)


@pytest.mark.parametrize("algorithm", ("builtin",*ALGORITHMS))
@pytest.mark.parametrize("components", (1,2,16))
@pytest.mark.parametrize("flow", ("clamp",-3.125,"error"))
def test_packed_edges_broadcast_threads(algorithm,components,flow):
    cfg,_=fixture("uneven20x20",flow)
    corr=feature_load(cfg,algorithm,components,True)["scale_0"]
    coords=coordinates(cfg,37,dtype="float64")
    if flow=="error": coords=tuple(np.clip(x,e[0]+.01,e[-1]-.01) for x,e in zip(coords,cfg["edges"]))
    for args in (coords,tuple(x[::-1] for x in coords),(coords[0][:,None],coords[1][None,:]),(coords[0],1.),(1.,1.),(coords[0][:0],coords[1][:0])):
        expected=packed_reference(cfg,args,components,algorithm.startswith("float32"))
        np.testing.assert_array_equal(corr.evaluate(*args),expected)
    if flow!="error":
        args=tuple(edge_coordinates(e) for e in cfg["edges"])
        np.testing.assert_array_equal(corr.evaluate(*args),packed_reference(cfg,args,components,algorithm.startswith("float32")))
    else:
        with pytest.raises(RuntimeError): corr.evaluate(np.array([1.,np.nan]),1.)
    with ThreadPoolExecutor(4) as pool:
        result=list(pool.map(lambda _:corr.evaluate(*coords),range(8)))
    for a in result: np.testing.assert_array_equal(a,result[0])


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("packed", (False,True))
def test_native_contract_strides_capacity_lifetime(algorithm,packed):
    cfg,_=fixture("fixed20x20",-7.25)
    name=algorithm if packed else algorithm+"_batch"
    probe=Kernel(json.dumps(feature_payload(cfg,name,3,packed)),str(library()))
    base=np.linspace(-4.,8.,66,dtype=np.float64)
    for x in (base[::2],base[::-2],np.broadcast_to(base[10],(33,))):
        for y in (base[1::2],1.):
            ns,actual=probe.run([x,y],33,capacity=33*(3 if packed else 1)+7)
            expected=packed_reference(cfg,(x,y),3,algorithm.startswith("float32")) if packed else numpy_reference(cfg,(x,y),algorithm.startswith("float32"))
            np.testing.assert_array_equal(actual,expected)
            assert ns>0
    assert probe.run([base[:0],1.],0)[1].shape==((0,3) if packed else (0,))
    with pytest.raises((RuntimeError,ValueError)): probe.run([base[:3],1.],3,null_output=True)
    for args,n,capacity in (([base[:3],1.],3,0),([base[:3]],3,None),([base[:2],1.],3,None),([base[:3].astype(np.int64),1.],3,None),([base[:0],1],0,None)):
        with pytest.raises((RuntimeError,ValueError)): probe.run(args,n,capacity=capacity)


@pytest.mark.parametrize("algorithm",ALGORITHMS)
def test_reject_packed_shape_and_scalar_confusion(algorithm):
    cfg,_=fixture("fixed64")
    import correctionlib
    from histogram_nodes import register_feature_nodes
    register_feature_nodes()
    data=feature_payload(cfg,algorithm,2,True)
    for mutation in ("content","missing_shape","wrong_shape","scalar_node"):
        bad=copy.deepcopy(data); corr=bad["corrections"][0]
        if mutation=="content":corr["data"]["config"]["content"].pop()
        if mutation=="missing_shape":corr["data"].pop("output_shape")
        if mutation=="wrong_shape":corr["data"]["output_shape"]=[3]
        if mutation=="scalar_node":corr["data"]["type"]="study.hist."+algorithm
        with pytest.raises((RuntimeError,ValueError)):correctionlib.CorrectionSet.from_string(json.dumps(bad))


@pytest.mark.parametrize("algorithm",ALGORITHMS)
def test_packed_beneath_transform_fallback(algorithm):
    import correctionlib
    from histogram_nodes import register_feature_nodes
    register_feature_nodes()
    cfg,_=fixture("fixed64")
    data=feature_payload(cfg,algorithm,3,True)
    corr=data["corrections"][0]
    corr["data"]={"nodetype":"transform","input":"x",
                  "rule":{"nodetype":"formula","expression":"x*2","parser":"TFormula","variables":["x"]},
                  "content":corr["data"]}
    node=correctionlib.CorrectionSet.from_string(json.dumps(data))["scale_0"]
    x=np.linspace(-2.,2.,101)
    np.testing.assert_array_equal(node.evaluate(x),packed_reference(cfg,(2*x,),3,algorithm.startswith("float32")))
