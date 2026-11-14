#pragma once
#include <correction_plugin.h>
#include <algorithm>
#include <cmath>
#include <limits>
#include <memory>
#include <stdexcept>
#include <type_traits>
#include <vector>

namespace study {
using correction::PluginConfig;
using correction::PluginContext;
using correction::PluginNode;
using correction::PluginRegistry;
using correction::Variable;

struct ParsedTable {
  std::vector<size_t> inputs;
  std::vector<std::vector<double>> edges;
  std::vector<double> content;
  int flow = 0; // 0 clamp, 1 numeric fallback, 2 error
  double fallback = 0;
  size_t components = 1;
};
ParsedTable parse(const PluginConfig&, const PluginContext&);

// Explicit guards make even extreme finite doubles safe to narrow to float32.
template<class T> T narrow(double value) {
  if constexpr (std::is_same_v<T, float>) {
    if (value > std::numeric_limits<float>::max()) return std::numeric_limits<float>::infinity();
    if (value < -std::numeric_limits<float>::max()) return -std::numeric_limits<float>::infinity();
  }
  return static_cast<T>(value);
}

template<class T> struct Axis {
  // A histogram with n bins has n+1 edges. Keep all of them for flow checks,
  // but give the tree searches a separate array of bin LOWER edges.
  std::vector<T> edges, padded;
  size_t n, power = 1;
  T scale = 0;
  bool uniform;

  explicit Axis(const std::vector<double>& original) : n(original.size()-1) {
    for (double edge : original) {
      T threshold = narrow<T>(edge);
      // Rounding an edge downward could put a float32 coordinate in the bin
      // above its original float64 boundary. Instead use the smallest float32
      // threshold at or above that boundary. For an already-float32 coordinate,
      // crossing this threshold is equivalent to crossing the original edge.
      if constexpr (std::is_same_v<T, float>) {
        if (static_cast<double>(threshold) < edge)
          threshold = std::nextafter(threshold, std::numeric_limits<T>::infinity());
      }
      edges.push_back(threshold);
    }
    // The looped tree needs a power-of-two length; the five-step search needs
    // at least 32 entries. Fill unused positions with +infinity so finite
    // coordinates stay below them. Copy only the n lower edges, not the final
    // upper edge; searches return a bin number, not an edge number.
    while (power < n) power *= 2;
    padded.assign(std::max(size_t(32),power), std::numeric_limits<T>::infinity());
    std::copy_n(edges.begin(), n, padded.begin());
    // Decide whether arithmetic indexing is worth trying from the original
    // float64 edges. Allow small rounding differences from generating equally
    // spaced edges; the search will still repair its estimate against edges.
    double width = (original.back()-original.front())/n;
    uniform = std::isfinite(width) && width > 0;
    for (size_t i=1; i<n; ++i)
      uniform &= std::abs(original[i]-(original.front()+i*width)) <=
        64*std::numeric_limits<double>::epsilon()*std::max({1.,std::abs(original[i]),std::abs(original.back()-original.front())});
    // Recheck in the node's actual precision. Narrowing to float32 can collapse
    // the span or make its inverse nonfinite, requiring the tree fallback.
    T span = edges.back()-edges.front();
    scale = T(n)/span;
    uniform &= std::isfinite(span) && span > 0 && std::isfinite(scale) && scale > 0;
  }

  size_t tree(T x) const {
    // Find the last bin lower edge that x has reached. Start with candidate
    // bin zero. Here power is the smallest power of two covering all bins;
    // try jumps of power/2, power/4, and so on down to one.
    // Each comparison adds either the whole jump or zero, rather than choosing
    // separate left/right code paths. Equality moves right: an edge belongs
    // to the bin starting there. For example, with eight bins, try 4, 2, 1.
    size_t k=0;
    for (size_t step=power/2; step; step/=2) k += size_t(!(x < padded[k+step]))*step;
    // +infinity and NaN can advance into the padding. Map those candidates to
    // the last real bin; the caller has already handled numeric/error flow.
    return std::min(k,n-1);
  }

};

// Policy is defined separately in each node source; shared code fixes all other
// numerical choices, flow handling, and row-major content indexing.
template<class Policy, class T=double, bool Batch=false, bool Packed=false> class Histogram final : public PluginNode {
  std::vector<size_t> inputs_;
  std::vector<Axis<T>> axes_;
  std::vector<T> content_;
  int flow_;
  T fallback_;
  size_t components_;
public:
  explicit Histogram(const ParsedTable& p) : inputs_(p.inputs), flow_(p.flow), fallback_(narrow<T>(p.fallback)), components_(p.components) {
    for (const auto& edges : p.edges) axes_.emplace_back(edges);
    for (double v : p.content) {
      T converted=narrow<T>(v);
      if (!std::isfinite(converted)) throw std::runtime_error("content not finite in selected precision");
      content_.push_back(converted);
    }
    if (!std::isfinite(fallback_)) throw std::runtime_error("fallback not finite in selected precision");
  }
  size_t output_size() const override { return Packed ? components_ : 0; }
  // A fixed array is an explicit payload choice, not several scalar queries.
  void evaluate_array(const std::vector<Variable::Type>& values, double* out, size_t) const override {
    if constexpr (!Packed) throw std::runtime_error("scalar histogram has no array output");
    size_t flat=0;
    for (size_t d=0; d<axes_.size(); ++d) {
      T x=narrow<T>(std::get<double>(values.at(inputs_[d])));
      const auto& a=axes_[d];
      if (x<a.edges.front() || !(x<a.edges.back())) {
        if (flow_==1) { std::fill_n(out,components_,static_cast<double>(fallback_)); return; }
        if (flow_==2) throw std::runtime_error("coordinate outside histogram");
      }
      flat=flat*a.n+Policy::find(a,x);
    }
    for (size_t s=0; s<components_; ++s) out[s]=static_cast<double>(content_[flat*components_+s]);
  }
  void evaluate_batch(const std::vector<correction::BatchInput>& values, size_t n, double* out, size_t capacity) const override {
    if constexpr (Batch && !Packed) batch(values,n,out);
    else PluginNode::evaluate_batch(values,n,out,capacity);
  }
  void evaluate_batch_array(const std::vector<correction::BatchInput>& values, size_t n, double* out, size_t capacity) const override {
    if constexpr (Packed) batch(values,n,out);
    else PluginNode::evaluate_batch_array(values,n,out,capacity);
  }
private:
  // Resolve dimension count and column references once per callback. Public SDK
  // at(row) reads scalar broadcasts and signed strides; no private pointer API.
  void batch(const std::vector<correction::BatchInput>& values, size_t n, double* out) const {
    const auto& xcol=values.at(inputs_[0]);
    const auto& ax=axes_[0];
    if (axes_.size()==1) {
      for (size_t row=0; row<n; ++row) {
        T x=narrow<T>(std::get<double>(xcol.at(row)));
        write(out+row*components_, ax, x, nullptr, T(0));
      }
    } else {
      const auto& ycol=values.at(inputs_[1]);
      const auto& ay=axes_[1];
      for (size_t row=0; row<n; ++row) {
        T x=narrow<T>(std::get<double>(xcol.at(row)));
        T y=narrow<T>(std::get<double>(ycol.at(row)));
        write(out+row*components_, ax, x, &ay, y);
      }
    }
  }
  void write(double* out, const Axis<T>& ax, T x, const Axis<T>* ay, T y) const {
    bool outside=x<ax.edges.front() || !(x<ax.edges.back());
    if (ay) outside |= y<ay->edges.front() || !(y<ay->edges.back());
    if (outside && flow_==1) { std::fill_n(out,components_,static_cast<double>(fallback_)); return; }
    if (outside && flow_==2) throw std::runtime_error("coordinate outside histogram");
    size_t flat=Policy::find(ax,x);
    if (ay) flat=flat*ay->n+Policy::find(*ay,y);
    // Only the explicitly packed provider reuses a search across components.
    for (size_t s=0; s<components_; ++s) out[s]=static_cast<double>(content_[flat*components_+s]);
  }
public:
  double evaluate(const std::vector<Variable::Type>& values) const override {
    if constexpr (Packed) throw std::runtime_error("array histogram requires array evaluation");
    size_t flat=0;
    for (size_t d=0; d<axes_.size(); ++d) {
      // The SDK passes doubles. Float32 nodes round each coordinate here,
      // before either the range check or the choice of bin.
      const T x=narrow<T>(std::get<double>(values.at(inputs_[d])));
      const auto& a=axes_[d];
      // The last edge is excluded. Writing "not below" also treats NaN as
      // overflow, matching the built-in explicit-edge histogram behavior.
      const bool outside=x<a.edges.front() || !(x<a.edges.back());
      if (outside && flow_==1) return static_cast<double>(fallback_);
      if (outside && flow_==2) throw std::runtime_error("coordinate outside histogram");
      // All searches clamp to an endpoint bin. If flow was neither numeric nor
      // error, that is the requested behavior. In 2D, this turns (ix, iy) into
      // ix * number_of_y_bins + iy, so y changes fastest in the content array.
      flat=flat*a.n+Policy::find(a,x);
    }
    return static_cast<double>(content_[flat]);
  }
};

template<class Policy, class T=double> void add(PluginRegistry& registry, const char* type) {
  registry.register_node(type,1,[](const PluginConfig& config, const PluginContext& ctx) {
    if (ctx.output_size()) throw std::runtime_error("scalar histogram requires scalar output");
    return std::make_shared<Histogram<Policy,T>>(parse(config,ctx));
  });
  registry.register_node(std::string(type)+"_batch",1,[](const PluginConfig& config, const PluginContext& ctx) {
    if (ctx.output_size()) throw std::runtime_error("batch histogram requires scalar output");
    return std::make_shared<Histogram<Policy,T,true>>(parse(config,ctx));
  });
  registry.register_node(std::string(type)+"_packed",1,[](const PluginConfig& config, const PluginContext& ctx) {
    if (!ctx.output_size()) throw std::runtime_error("packed histogram requires array output");
    return std::make_shared<Histogram<Policy,T,true,true>>(parse(config,ctx));
  });
}
void register_binary(PluginRegistry&);
void register_linear(PluginRegistry&);
void register_tree(PluginRegistry&);
void register_unrolled(PluginRegistry&);
void register_arithmetic(PluginRegistry&);
void register_float32_unrolled(PluginRegistry&);
void register_float32_arithmetic(PluginRegistry&);
} // namespace study
