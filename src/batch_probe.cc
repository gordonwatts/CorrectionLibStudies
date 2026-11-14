// Validation/timing adapter only: all searches execute through public C++ core.
#include <correction_plugin.h>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <chrono>
#include <algorithm>
#include <limits>
namespace py=pybind11;
class Kernel {
  correction::Correction::Ref corr_;
public:
  Kernel(const std::string& json, const std::string& library) {
    correction::PluginRegistry registry;
    registry.load_library(library);
    auto set=correction::CorrectionSet::from_string(json.c_str(),registry);
    corr_=set->at("scale_0");
    // Both registry and CorrectionSet die here: the retained correction must own
    // the loaded provider and its state for later calls.
  }
  py::tuple run(py::list args, size_t n, size_t repeats, py::object capacity_arg, bool null_output) const {
    if (!repeats) throw std::runtime_error("repeats must be positive");
    std::vector<correction::BatchInput> inputs;
    for (auto arg:args) {
      if (py::isinstance<py::array>(arg)) {
        auto arr=py::reinterpret_borrow<py::array>(arg);
        if (arr.ndim()!=1) throw std::runtime_error("probe requires 1D columns");
        if (arr.dtype().is(py::dtype::of<double>())) {
          inputs.push_back(correction::BatchInput::reals(static_cast<const double*>(arr.data()),arr.size(),arr.strides(0)/static_cast<py::ssize_t>(sizeof(double))));
        } else if (arr.dtype().is(py::dtype::of<int64_t>())) {
          inputs.push_back(correction::BatchInput::integers(static_cast<const int64_t*>(arr.data()),arr.size(),arr.strides(0)/static_cast<py::ssize_t>(sizeof(int64_t))));
        } else throw std::runtime_error("probe accepts only float64/int64 columns");
      } else if (py::isinstance<py::float_>(arg)) inputs.emplace_back(correction::Variable::Type{py::cast<double>(arg)});
      else if (py::isinstance<py::int_>(arg)) inputs.emplace_back(correction::Variable::Type{py::cast<int64_t>(arg)});
      else inputs.emplace_back(correction::Variable::Type{py::cast<std::string>(arg)});
    }
    size_t s=std::max(size_t(1),corr_->output_size());
    if (n>std::numeric_limits<size_t>::max()/s) throw std::runtime_error("probe size overflow");
    size_t required=n*s;
    size_t capacity=capacity_arg.is_none()?required:py::cast<size_t>(capacity_arg);
    std::vector<double> storage(std::max(required,capacity)+2,-1234567.25);
    double* output=n && !null_output?storage.data()+1:nullptr;
    auto begin=std::chrono::steady_clock::now();
    {
      py::gil_scoped_release release;
      for (size_t r=0;r<repeats;++r) {
        if (corr_->output_size()) corr_->evaluate_batch_array(inputs,n,output,capacity);
        else corr_->evaluate_batch(inputs,n,output,capacity);
      }
    }
    auto elapsed=std::chrono::duration<double,std::nano>(std::chrono::steady_clock::now()-begin).count()/repeats;
    if (storage.front()!=-1234567.25 || storage[required+1]!=-1234567.25)
      throw std::runtime_error("native output overrun");
    py::array_t<double> result(required);
    std::copy_n(storage.data()+1,required,result.mutable_data());
    if (corr_->output_size()) result.resize({static_cast<py::ssize_t>(n),static_cast<py::ssize_t>(s)});
    return py::make_tuple(elapsed,result);
  }
};
PYBIND11_MODULE(_batch_probe,m) {
  py::class_<Kernel>(m,"Kernel")
    .def(py::init<const std::string&,const std::string&>())
    .def("run",&Kernel::run,py::arg("args"),py::arg("n"),py::arg("repeats")=1,py::arg("capacity")=py::none(),py::arg("null_output")=false);
}
