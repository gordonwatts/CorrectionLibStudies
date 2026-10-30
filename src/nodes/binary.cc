#include "table.h"
namespace study {
struct Binary {
  template<class T> static size_t find(const Axis<T>& a,T x) {
    // upper_bound halves the remaining edge range until it finds the first
    // edge strictly ABOVE x. The bin starts one edge earlier, so an exact
    // edge selects the bin on its right (lower edge included, upper excluded).
    auto it=std::upper_bound(a.edges.begin(),a.edges.end(),x);
    // Below the first edge there is no preceding bin. Above the final edge
    // (also for NaN), cap the result at the last bin. The caller applies flow.
    if (it==a.edges.begin()) return 0;
    return std::min(size_t(it-a.edges.begin()-1),a.n-1);
  }
};
void register_binary(PluginRegistry& r) { add<Binary>(r,"study.hist.binary"); }
}
