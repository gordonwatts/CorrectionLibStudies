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
  std::vector<T> edges, padded;
  size_t n, power = 1;
  T scale = 0;
  bool uniform;

  explicit Axis(const std::vector<double>& original) : n(original.size()-1) {
    for (double edge : original) {
      T threshold = narrow<T>(edge);
      // A representable float x >= original edge iff x >= ceil_float(edge).
      if constexpr (std::is_same_v<T, float>) {
        if (static_cast<double>(threshold) < edge)
          threshold = std::nextafter(threshold, std::numeric_limits<T>::infinity());
      }
      edges.push_back(threshold);
    }
    while (power < n) power *= 2;
    padded.assign(std::max(size_t(32),power), std::numeric_limits<T>::infinity());
    std::copy_n(edges.begin(), n, padded.begin());
    double width = (original.back()-original.front())/n;
    uniform = std::isfinite(width) && width > 0;
    for (size_t i=1; i<n; ++i)
      uniform &= std::abs(original[i]-(original.front()+i*width)) <=
        64*std::numeric_limits<double>::epsilon()*std::max({1.,std::abs(original[i]),std::abs(original.back()-original.front())});
    T span = edges.back()-edges.front();
    scale = T(n)/span;
    uniform &= std::isfinite(span) && span > 0 && std::isfinite(scale) && scale > 0;
  }

  size_t tree(T x) const {
    size_t k=0;
    for (size_t step=power/2; step; step/=2) k += size_t(!(x < padded[k+step]))*step;
    return std::min(k,n-1);
  }

};

// Policy is defined separately in each node source; shared code fixes all other
// numerical choices, flow handling, and row-major content indexing.
template<class Policy, class T=double> class Histogram final : public PluginNode {
  std::vector<size_t> inputs_;
  std::vector<Axis<T>> axes_;
  std::vector<T> content_;
  int flow_;
  T fallback_;
public:
  explicit Histogram(const ParsedTable& p) : inputs_(p.inputs), flow_(p.flow), fallback_(narrow<T>(p.fallback)) {
    for (const auto& edges : p.edges) axes_.emplace_back(edges);
    for (double v : p.content) {
      T converted=narrow<T>(v);
      if (!std::isfinite(converted)) throw std::runtime_error("content not finite in selected precision");
      content_.push_back(converted);
    }
    if (!std::isfinite(fallback_)) throw std::runtime_error("fallback not finite in selected precision");
  }
  double evaluate(const std::vector<Variable::Type>& values) const override {
    size_t flat=0;
    for (size_t d=0; d<axes_.size(); ++d) {
      const T x=narrow<T>(std::get<double>(values.at(inputs_[d])));
      const auto& a=axes_[d];
      const bool outside=x<a.edges.front() || !(x<a.edges.back());
      if (outside && flow_==1) return static_cast<double>(fallback_);
      if (outside && flow_==2) throw std::runtime_error("coordinate outside histogram");
      flat=flat*a.n+Policy::find(a,x);
    }
    return static_cast<double>(content_[flat]);
  }
};

template<class Policy, class T=double> void add(PluginRegistry& registry, const char* type) {
  registry.register_node(type,1,[](const PluginConfig& config, const PluginContext& ctx) {
    return std::make_shared<Histogram<Policy,T>>(parse(config,ctx));
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
