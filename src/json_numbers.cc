// Validation helper only: reproduce the host's JSON -> double conversion.
// No lookup, batching, or timed evaluation is implemented here.
#include <pybind11/pybind11.h>
#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <stdexcept>

PYBIND11_MODULE(_json_numbers, module) {
  module.def("parsed_numbers", [](const std::string& text) {
    rapidjson::Document doc;
    doc.Parse<rapidjson::kParseNanAndInfFlag>(text.c_str());
    if (doc.HasParseError()) throw std::runtime_error("invalid validation JSON");
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    doc.Accept(writer);
    return std::string(buffer.GetString(),buffer.GetSize());
  });
}
