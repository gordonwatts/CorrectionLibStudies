#include "table.h"
namespace study {
struct Float32Arithmetic {
  static size_t find(const Axis<float>& a,float x) {
    // x and stored thresholds are float32; Axis chose thresholds by rounding
    // original float64 edges upward. Try arithmetic only when Axis found
    // approximately equal widths AND a finite, positive float32 inverse width.
    if (!a.uniform) return a.tree(x);
    // Deal with out-of-range coordinates, infinities, and NaN before casting
    // a floating-point estimate to an integer. Equality at the top is overflow.
    if (x<a.edges.front()) return 0;
    if (!(x<a.edges.back())) return a.n-1;
    // Estimate the bin in float32, then clamp BEFORE integer conversion.
    // This keeps even an overflowing intermediate estimate safe to convert.
    float estimate=(x-a.edges.front())*a.scale;
    estimate=std::max(0.f,std::min(float(a.n-1),estimate));
    size_t k=static_cast<size_t>(estimate);
    // Float32 arithmetic and rounded thresholds need not agree exactly near
    // a boundary. Repair using the actual thresholds: move left if below the
    // candidate bin, or right if the next bin's lower edge has been reached.
    // Equality moves right, just as in the float64 version.
    while (k>0 && x<a.edges[k]) --k;
    while (k<a.n-1 && !(x<a.edges[k+1])) ++k;
    return k;
  }
};
void register_float32_arithmetic(PluginRegistry& r) { add<Float32Arithmetic,float>(r,"study.hist.float32_arithmetic"); }
}
