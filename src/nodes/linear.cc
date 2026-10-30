#include "table.h"
namespace study {
struct Linear {
  template<class T> static size_t find(const Axis<T>& a,T x) {
    // Start in the first bin and walk right while x has reached the NEXT
    // bin's lower edge. Equality therefore selects the bin on the right.
    // Stop at the last real bin, naturally clamping underflow and overflow.
    // "Not below" sends NaN to the last bin too, as in the other searches.
    size_t k=0;
    while (k+1<a.n && !(x<a.edges[k+1])) ++k;
    return k;
  }
};
void register_linear(PluginRegistry& r) { add<Linear>(r,"study.hist.linear"); }
}
