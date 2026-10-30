#include "table.h"
namespace study {
struct Binary {
  template<class T> static size_t find(const Axis<T>& a,T x) {
    auto it=std::upper_bound(a.edges.begin(),a.edges.end(),x);
    if (it==a.edges.begin()) return 0;
    return std::min(size_t(it-a.edges.begin()-1),a.n-1);
  }
};
void register_binary(PluginRegistry& r) { add<Binary>(r,"study.hist.binary"); }
}
