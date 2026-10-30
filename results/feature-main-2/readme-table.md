At 100,000 items, **Python lookup and rescaling**, median of seven rounds in milliseconds:

| Table | Built-in native batch | Unrolled scalar fallback | Unrolled native batch | Arithmetic native batch |
|---|---:|---:|---:|---:|
| fixed64 | 3.230 | 1.156 | 0.878 | 0.872 |
| uneven64 | 2.947 | 1.220 | 0.911 | 0.887 |
| fixed20x20 | 5.047 | 1.472 | 1.051 | 2.101 |
| uneven20x20 | 4.667 | 1.458 | 1.080 | 1.428 |

For fixed20x20, native batching improves the same unrolled scalar-output node
from **1.472 ms to 1.051 ms (1.40x)**. For 16 factors per item, 16 independent
unrolled native-batch corrections take **22.722 ms**, versus **2.591 ms** for
one packed unrolled correction: **8.77x**, including the different allocation
and stacking paths described below. Retained ranges are 22.454–25.229 ms and
2.382–2.954 ms respectively. The built-in packed16 control takes 7.758 ms.

In the separate C++ kernel scope, fixed20x20 unrolled scalar fallback takes
**1.334 ms**, native batch **0.961 ms**, and packed16 **1.095 ms**. These are
different output workloads; the last number is throughput evidence, not a
native packed-versus-independent16 speedup. Arithmetic and float32 do not
consistently outperform the double unrolled node.

The accepted campaign contains **4,636 timing rows**, **37,088 raw rounds**
and **467,660,288 exact comparisons**. The first attempt failed during a
Windows-mounted filesystem checkpoint; its [partial evidence](../feature-main/FAILED.txt)
is explicitly excluded. The accepted retry records on Linux before copying
final evidence into the checkout.
