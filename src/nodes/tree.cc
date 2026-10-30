#include "table.h"
namespace study {
struct Tree {
  template<class T> static size_t find(const Axis<T>& a,T x) {
    // This is the general search for any supported axis length: repeatedly
    // halve a jump through padded bin edges, using each comparison to update
    // the candidate bin. Axis::tree in table.h explains the steps and padding.
    // Reuse that same implementation when another node needs a fallback.
    return a.tree(x);
  }
};
void register_tree(PluginRegistry& r) { add<Tree>(r,"study.hist.tree"); }
}
