"""Run from the repository root after sourcing feature-environment.sh."""
import correctionlib
import numpy as np

from histogram_nodes.feature_workloads import feature_load
from histogram_nodes.workloads import fixture

config,_=fixture("fixed20x20")
scalar=feature_load(config,"unrolled")["scale_0"]
batch=feature_load(config,"unrolled_batch")["scale_0"]
x=np.array([0.,1.,2.])
np.testing.assert_array_equal(scalar.evaluate(x,1.),batch.evaluate(x,1.))
print("one scalar result:",batch.evaluate(1.,1.))
print("three scalar results:",batch.evaluate(x,1.))

packed=correctionlib.CorrectionSet.from_file("examples/packed-histogram.json")["three_factors"]
np.testing.assert_array_equal(packed.evaluate(np.array([.25,1.25])),[[1.,1.1,1.2],[2.,2.1,2.2]])
print("one row of three components:",packed.evaluate(.25))
print("two rows of three components:",packed.evaluate(np.array([.25,1.25])))
