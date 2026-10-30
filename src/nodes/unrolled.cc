#include "table.h"
namespace study {
struct Unrolled {
  template<class T> static size_t find(const Axis<T>& a,T x) {
    // Five binary choices can distinguish 32 bins. Larger axes need the
    // general tree; smaller ones use +infinity padding prepared by Axis.
    if (a.n>32) return a.tree(x);
    size_t k=0;
    // Write the tree's jumps out explicitly, removing the loop over jump
    // sizes. Reaching edge 16 adds 16 to k; the next comparison then tries
    // edge k+8 within the chosen half, followed by jumps of 4, 2, and 1.
    // A comparison contributes either its jump or zero. Equality moves right.
    k += size_t(!(x<a.padded[k+16]))*16;
    k += size_t(!(x<a.padded[k+8]))*8;
    k += size_t(!(x<a.padded[k+4]))*4;
    k += size_t(!(x<a.padded[k+2]))*2;
    k += size_t(!(x<a.padded[k+1]));
    // Even a one-bin axis takes all five steps. Clamp any candidate reached
    // through padding (possible for +infinity or NaN) to the last real bin.
    return std::min(k,a.n-1);
  }
};
void register_unrolled(PluginRegistry& r) { add<Unrolled>(r,"study.hist.unrolled"); }
}
