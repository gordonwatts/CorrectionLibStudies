#include "table.h"
extern "C" int correctionlib_plugin_api_version() { return correction::plugin_api_version; }
extern "C" const char* correctionlib_plugin_build_id() { return correction::plugin_build_id().c_str(); }
extern "C" void correctionlib_register_nodes_v4(correction::PluginRegistry& registry) {
  study::register_binary(registry);
  study::register_linear(registry);
  study::register_tree(registry);
  study::register_unrolled(registry);
  study::register_arithmetic(registry);
  study::register_float32_unrolled(registry);
  study::register_float32_arithmetic(registry);
}
