#include "table.h"
namespace study {
struct Arithmetic {
  template<class T> static size_t find(const Axis<T>& a,T x) {
    if (!a.uniform) return a.tree(x);
    if (x<a.edges.front()) return 0;
    if (!(x<a.edges.back())) return a.n-1;
    T estimate=(x-a.edges.front())*a.scale;
    estimate=std::max(T(0),std::min(T(a.n-1),estimate));
    size_t k=static_cast<size_t>(estimate);
    while (k>0 && x<a.edges[k]) --k;
    while (k<a.n-1 && !(x<a.edges[k+1])) ++k;
    return k;
  }
};
void register_arithmetic(PluginRegistry& r) { add<Arithmetic>(r,"study.hist.arithmetic"); }
}
