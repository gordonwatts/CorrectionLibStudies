#include "table.h"
namespace study {
struct Linear {
  template<class T> static size_t find(const Axis<T>& a,T x) {
    size_t k=0;
    while (k+1<a.n && !(x<a.edges[k+1])) ++k;
    return k;
  }
};
void register_linear(PluginRegistry& r) { add<Linear>(r,"study.hist.linear"); }
}
