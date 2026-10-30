#include "table.h"
namespace study {
struct Float32Arithmetic {
  static size_t find(const Axis<float>& a,float x) {
    if (!a.uniform) return a.tree(x);
    if (x<a.edges.front()) return 0;
    if (!(x<a.edges.back())) return a.n-1;
    float estimate=(x-a.edges.front())*a.scale;
    estimate=std::max(0.f,std::min(float(a.n-1),estimate));
    size_t k=static_cast<size_t>(estimate);
    while (k>0 && x<a.edges[k]) --k;
    while (k<a.n-1 && !(x<a.edges[k+1])) ++k;
    return k;
  }
};
void register_float32_arithmetic(PluginRegistry& r) { add<Float32Arithmetic,float>(r,"study.hist.float32_arithmetic"); }
}
