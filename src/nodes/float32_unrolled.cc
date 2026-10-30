#include "table.h"
namespace study {
struct Float32Unrolled {
  static size_t find(const Axis<float>& a,float x) {
    // Histogram has already rounded x to float32. Axis stores float32 search
    // thresholds rounded upward from the original float64 edges, preserving
    // the original bin decisions for coordinates representable as float32.
    // Five fixed comparisons cover at most 32 bins; larger axes use the tree.
    if (a.n>32) return a.tree(x);
    size_t k=0;
    // Each reached edge adds a jump of 16, 8, 4, 2, or 1 to the candidate bin.
    // Later comparisons are relative to that updated candidate, narrowing the
    // search to the chosen half each time. Equality moves to the bin on the
    // right. The unused positions of a short axis contain +infinity.
    k += size_t(!(x<a.padded[k+16]))*16;
    k += size_t(!(x<a.padded[k+8]))*8;
    k += size_t(!(x<a.padded[k+4]))*4;
    k += size_t(!(x<a.padded[k+2]))*2;
    k += size_t(!(x<a.padded[k+1]));
    // Infinities and NaN can reach padded positions; return a real bin.
    return std::min(k,a.n-1);
  }
};
void register_float32_unrolled(PluginRegistry& r) { add<Float32Unrolled,float>(r,"study.hist.float32_unrolled"); }
}
