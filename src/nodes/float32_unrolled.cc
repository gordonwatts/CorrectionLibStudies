#include "table.h"
namespace study {
struct Float32Unrolled {
  static size_t find(const Axis<float>& a,float x) {
    if (a.n>32) return a.tree(x);
    size_t k=0;
    k += size_t(!(x<a.padded[k+16]))*16;
    k += size_t(!(x<a.padded[k+8]))*8;
    k += size_t(!(x<a.padded[k+4]))*4;
    k += size_t(!(x<a.padded[k+2]))*2;
    k += size_t(!(x<a.padded[k+1]));
    return std::min(k,a.n-1);
  }
};
void register_float32_unrolled(PluginRegistry& r) { add<Float32Unrolled,float>(r,"study.hist.float32_unrolled"); }
}
