#include "table.h"
namespace study {
struct Arithmetic {
  template<class T> static size_t find(const Axis<T>& a,T x) {
    // Only approximately equal-width axes with a usable inverse width can
    // use an arithmetic estimate. All others keep the general tree search.
    if (!a.uniform) return a.tree(x);
    // Handle endpoints, infinities, and NaN BEFORE any integer conversion.
    // The upper edge is excluded; "not below" includes NaN in overflow.
    if (x<a.edges.front()) return 0;
    if (!(x<a.edges.back())) return a.n-1;
    // Distance from the first edge, measured in bin widths, estimates the
    // bin number. Keep the estimate in range before converting to an integer;
    // truncation then selects the expected bin for nonnegative estimates.
    T estimate=(x-a.edges.front())*a.scale;
    estimate=std::max(T(0),std::min(T(a.n-1),estimate));
    size_t k=static_cast<size_t>(estimate);
    // Floating-point multiplication can put an exact boundary just to either
    // side of an integer. The stored edges remain authoritative: move left
    // while below this bin, or right while at/past the next bin's lower edge.
    // This repair also handles small width differences allowed by Axis.
    while (k>0 && x<a.edges[k]) --k;
    while (k<a.n-1 && !(x<a.edges[k+1])) ++k;
    return k;
  }
};
void register_arithmetic(PluginRegistry& r) { add<Arithmetic>(r,"study.hist.arithmetic"); }
}
