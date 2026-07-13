#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <regex>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace {

struct TelemetryRecord {
  int line_number{};
  std::string session_id;
  std::string timestamp;
  std::string vehicle_id;
  std::string signal;
  std::string value_text;
  bool value_is_string{};
};

struct SignalRange {
  double minimum{};
  double maximum{};
};

struct ValidationIssue {
  int line_number{};
  std::string field;
  std::string message;
};

struct Anomaly {
  int line_number{};
  std::string signal;
  std::string message;
};

const std::map<std::string, SignalRange> kSignalRanges = {
    {"battery_voltage", {9.0, 16.0}},
    {"engine_rpm", {0.0, 8000.0}},
    {"vehicle_speed", {0.0, 260.0}},
};

const std::map<std::string, std::map<std::string, std::set<std::string>>> kTransitionRules = {
    {"gear_state",
     {
         {"PARK", {"PARK", "REVERSE", "NEUTRAL"}},
         {"REVERSE", {"REVERSE", "NEUTRAL", "PARK"}},
         {"NEUTRAL", {"NEUTRAL", "DRIVE", "REVERSE", "PARK"}},
         {"DRIVE", {"DRIVE", "NEUTRAL"}},
     }},
    {"ignition_state",
     {
         {"OFF", {"OFF", "ACCESSORY"}},
         {"ACCESSORY", {"ACCESSORY", "ON", "OFF"}},
         {"ON", {"ON", "START", "OFF"}},
         {"START", {"ON"}},
     }},
};

std::optional<std::string> extract_string(const std::string &line, const std::string &field) {
  const std::regex pattern("\"" + field + "\"\\s*:\\s*\"([^\"]*)\"");
  std::smatch match;
  if (!std::regex_search(line, match, pattern)) {
    return std::nullopt;
  }
  return match[1].str();
}

std::optional<std::pair<std::string, bool>> extract_value(const std::string &line) {
  std::smatch string_match;
  const std::regex string_pattern("\"value\"\\s*:\\s*\"([^\"]*)\"");
  if (std::regex_search(line, string_match, string_pattern)) {
    return std::make_pair(string_match[1].str(), true);
  }

  std::smatch scalar_match;
  const std::regex scalar_pattern("\"value\"\\s*:\\s*([^,}\\s]+)");
  if (std::regex_search(line, scalar_match, scalar_pattern)) {
    return std::make_pair(scalar_match[1].str(), false);
  }

  return std::nullopt;
}

TelemetryRecord parse_record(const std::string &line, int line_number) {
  TelemetryRecord record;
  record.line_number = line_number;
  record.session_id = extract_string(line, "session_id").value_or("");
  record.timestamp = extract_string(line, "timestamp").value_or("");
  record.vehicle_id = extract_string(line, "vehicle_id").value_or("");
  record.signal = extract_string(line, "signal").value_or("");

  const auto value = extract_value(line);
  if (value.has_value()) {
    record.value_text = value->first;
    record.value_is_string = value->second;
  }
  return record;
}

bool is_iso8601_utc(const std::string &timestamp) {
  static const std::regex pattern(
      R"(^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$)");
  return std::regex_match(timestamp, pattern);
}

std::optional<double> parse_double(const std::string &value) {
  char *end = nullptr;
  const double parsed = std::strtod(value.c_str(), &end);
  if (end == value.c_str() || *end != '\0') {
    return std::nullopt;
  }
  return parsed;
}

std::vector<ValidationIssue> validate_record(const TelemetryRecord &record) {
  std::vector<ValidationIssue> issues;
  const std::vector<std::pair<std::string, std::string>> required_fields = {
      {"session_id", record.session_id},
      {"timestamp", record.timestamp},
      {"vehicle_id", record.vehicle_id},
      {"signal", record.signal},
  };

  for (const auto &[field, value] : required_fields) {
    if (value.empty()) {
      issues.push_back({record.line_number, field, "required non-empty string"});
    }
  }

  if (record.value_text.empty()) {
    issues.push_back({record.line_number, "value", "required"});
  }

  if (!record.timestamp.empty() && !is_iso8601_utc(record.timestamp)) {
    issues.push_back({record.line_number, "timestamp", "expected ISO-8601 UTC timestamp"});
  }

  return issues;
}

std::string transition_key(const TelemetryRecord &record) {
  return record.session_id + "|" + record.vehicle_id + "|" + record.signal;
}

void analyze_record(
    const TelemetryRecord &record,
    std::map<std::string, std::string> &last_values,
    std::vector<Anomaly> &anomalies) {
  const auto range_it = kSignalRanges.find(record.signal);
  if (range_it != kSignalRanges.end()) {
    const auto numeric_value = parse_double(record.value_text);
    if (!numeric_value.has_value() || *numeric_value < range_it->second.minimum ||
        *numeric_value > range_it->second.maximum) {
      anomalies.push_back(
          {record.line_number, record.signal, record.signal + " outside expected range"});
    }
  }

  const auto key = transition_key(record);
  const auto previous_it = last_values.find(key);
  if (previous_it == last_values.end()) {
    last_values[key] = record.value_text;
    return;
  }

  const std::string previous_value = previous_it->second;
  last_values[key] = record.value_text;

  const auto signal_rules = kTransitionRules.find(record.signal);
  if (signal_rules == kTransitionRules.end()) {
    return;
  }

  const auto next_values = signal_rules->second.find(previous_value);
  if (next_values == signal_rules->second.end()) {
    return;
  }

  if (next_values->second.find(record.value_text) == next_values->second.end()) {
    anomalies.push_back(
        {record.line_number, record.signal,
         "invalid " + record.signal + " transition " + previous_value + " -> " +
             record.value_text});
  }
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 2) {
    std::cerr << "usage: telemetry_validator <telemetry.jsonl>\n";
    return 64;
  }

  std::ifstream input(argv[1]);
  if (!input) {
    std::cerr << "failed to open " << argv[1] << "\n";
    return 66;
  }

  std::vector<ValidationIssue> validation_issues;
  std::vector<Anomaly> anomalies;
  std::map<std::string, std::string> last_values;

  std::string line;
  int line_number = 0;
  int records_seen = 0;
  while (std::getline(input, line)) {
    ++line_number;
    if (line.empty()) {
      continue;
    }

    ++records_seen;
    const auto record = parse_record(line, line_number);
    auto issues = validate_record(record);
    if (!issues.empty()) {
      validation_issues.insert(validation_issues.end(), issues.begin(), issues.end());
      continue;
    }

    analyze_record(record, last_values, anomalies);
  }

  std::cout << "records_seen=" << records_seen << "\n";
  std::cout << "validation_issues=" << validation_issues.size() << "\n";
  std::cout << "anomalies=" << anomalies.size() << "\n";

  for (const auto &issue : validation_issues) {
    std::cout << "validation line=" << issue.line_number << " field=" << issue.field
              << " message=" << issue.message << "\n";
  }

  for (const auto &anomaly : anomalies) {
    std::cout << "anomaly line=" << anomaly.line_number << " signal=" << anomaly.signal
              << " message=" << anomaly.message << "\n";
  }

  if (!validation_issues.empty()) {
    return 1;
  }
  if (!anomalies.empty()) {
    return 2;
  }
  return 0;
}
