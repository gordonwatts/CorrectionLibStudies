#include "table.h"
#include <rapidjson/document.h>
#include <set>

namespace study {
ParsedTable parse(const PluginConfig& config, const PluginContext& ctx) {
  config.require_keys({"inputs","edges","content","flow"});
  if (ctx.child_count()!=0) throw std::runtime_error("histogram requires no children");
  rapidjson::Document doc;
  // The host has already parsed the payload. Preserve those binary doubles
  // across the SDK's JSON serialization, without a second fast-parse rounding.
  doc.Parse<rapidjson::kParseFullPrecisionFlag>(config.json().c_str());
  if (doc.HasParseError() || !doc.IsObject()) throw std::runtime_error("invalid histogram JSON");
  const auto& inputs=doc["inputs"];
  const auto& edges=doc["edges"];
  const auto& content=doc["content"];
  if (!inputs.IsArray() || inputs.Empty() || inputs.Size()>2 || !edges.IsArray() || edges.Size()!=inputs.Size())
    throw std::runtime_error("one or two named axes required");
  ParsedTable p;
  p.components=std::max(size_t(1),ctx.output_size());
  std::set<std::string> names;
  size_t bins=1;
  for (size_t d=0; d<inputs.Size(); ++d) {
    if (!inputs[d].IsString() || !names.insert(inputs[d].GetString()).second)
      throw std::runtime_error("distinct string inputs required");
    p.inputs.push_back(ctx.input_index(inputs[d].GetString(),Variable::VarType::real));
    const auto& axis=edges[d];
    if (!axis.IsArray() || axis.Size()<2 || axis.Size()>1048577)
      throw std::runtime_error("axis requires 2..1048577 edges");
    std::vector<double> a;
    for (const auto& e : axis.GetArray()) {
      if (!e.IsNumber() || !std::isfinite(e.GetDouble()) || (!a.empty() && !(e.GetDouble()>a.back())))
        throw std::runtime_error("finite strictly increasing edges required");
      a.push_back(e.GetDouble());
    }
    if (bins>1048576/(a.size()-1)) throw std::runtime_error("table exceeds 1048576 bins");
    bins*=a.size()-1;
    p.edges.push_back(std::move(a));
  }
  if (p.components>1048576 || bins>1048576/p.components)
    throw std::runtime_error("table exceeds 1048576 stored components");
  if (!content.IsArray() || content.Size()!=bins*p.components) throw std::runtime_error("content shape mismatch");
  for (const auto& v : content.GetArray()) {
    if (!v.IsNumber() || !std::isfinite(v.GetDouble())) throw std::runtime_error("finite numeric contents required");
    p.content.push_back(v.GetDouble());
  }
  const auto& flow=doc["flow"];
  if (flow.IsNumber() && std::isfinite(flow.GetDouble())) { p.flow=1; p.fallback=flow.GetDouble(); }
  else if (flow.IsString() && std::string(flow.GetString())=="clamp") p.flow=0;
  else if (flow.IsString() && std::string(flow.GetString())=="error") p.flow=2;
  else throw std::runtime_error("flow must be clamp, error, or a finite number");
  return p;
}
} // namespace study
