#include "table.h"
namespace study {
struct Tree {
  template<class T> static size_t find(const Axis<T>& a,T x) {
    // The same helper supplies the fallback for the other search nodes.
    return a.tree(x);
  }
};
void register_tree(PluginRegistry& r) { add<Tree>(r,"study.hist.tree"); }
}
