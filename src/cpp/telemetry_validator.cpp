#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <regex>
#include <set>
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
  bool has_value{};
  std::string parse_error;
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

struct JsonValue {
  std::string text;
  bool is_string{};
};

struct JsonObjectResult {
  std::map<std::string, JsonValue> fields;
  std::string error;
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

void skip_space(const std::string &line, std::size_t &position) {
  while (position < line.size() &&
         (line[position] == ' ' || line[position] == '\t' || line[position] == '\r' ||
          line[position] == '\n')) {
    ++position;
  }
}

std::optional<std::string> parse_string(const std::string &line, std::size_t &position) {
  if (position >= line.size() || line[position] != '"') {
    return std::nullopt;
  }

  ++position;
  std::string parsed;
  while (position < line.size()) {
    const char current = line[position++];
    if (current == '"') {
      return parsed;
    }

    if (current != '\\') {
      parsed += current;
      continue;
    }

    if (position >= line.size()) {
      return std::nullopt;
    }

    const char escaped = line[position++];
    switch (escaped) {
    case '"':
    case '\\':
    case '/':
      parsed += escaped;
      break;
    case 'b':
      parsed += '\b';
      break;
    case 'f':
      parsed += '\f';
      break;
    case 'n':
      parsed += '\n';
      break;
    case 'r':
      parsed += '\r';
      break;
    case 't':
      parsed += '\t';
      break;
    default:
      return std::nullopt;
    }
  }

  return std::nullopt;
}

std::string trim_copy(const std::string &value) {
  std::size_t start = 0;
  while (start < value.size() &&
         (value[start] == ' ' || value[start] == '\t' || value[start] == '\r' ||
          value[start] == '\n')) {
    ++start;
  }

  std::size_t end = value.size();
  while (end > start && (value[end - 1] == ' ' || value[end - 1] == '\t' ||
                         value[end - 1] == '\r' || value[end - 1] == '\n')) {
    --end;
  }

  return value.substr(start, end - start);
}

JsonObjectResult parse_flat_json_object(const std::string &line) {
  JsonObjectResult result;
  std::size_t position = 0;
  skip_space(line, position);

  if (position >= line.size() || line[position] != '{') {
    result.error = "invalid JSON object";
    return result;
  }
  ++position;

  while (position < line.size()) {
    skip_space(line, position);
    if (position < line.size() && line[position] == '}') {
      ++position;
      skip_space(line, position);
      if (position != line.size()) {
        result.error = "unexpected content after JSON object";
      }
      return result;
    }

    auto key = parse_string(line, position);
    if (!key.has_value()) {
      result.error = "expected string field name";
      return result;
    }

    skip_space(line, position);
    if (position >= line.size() || line[position] != ':') {
      result.error = "expected ':' after field name";
      return result;
    }
    ++position;
    skip_space(line, position);

    if (position >= line.size()) {
      result.error = "expected field value";
      return result;
    }

    JsonValue value;
    if (line[position] == '"') {
      auto parsed = parse_string(line, position);
      if (!parsed.has_value()) {
        result.error = "invalid JSON string value";
        return result;
      }
      value = {*parsed, true};
    } else if (line[position] == '{' || line[position] == '[') {
      result.error = "nested JSON values are not supported";
      return result;
    } else {
      const std::size_t start = position;
      while (position < line.size() && line[position] != ',' && line[position] != '}') {
        ++position;
      }
      value = {trim_copy(line.substr(start, position - start)), false};
      if (value.text.empty()) {
        result.error = "expected field value";
        return result;
      }
    }
    result.fields[*key] = value;

    skip_space(line, position);
    if (position >= line.size()) {
      result.error = "unterminated JSON object";
      return result;
    }
    if (line[position] == ',') {
      ++position;
      continue;
    }
    if (line[position] == '}') {
      continue;
    }

    result.error = "expected ',' or '}' after field value";
    return result;
  }

  result.error = "unterminated JSON object";
  return result;
}

std::string get_string_field(
    const std::map<std::string, JsonValue> &fields,
    const std::string &field) {
  const auto found = fields.find(field);
  if (found == fields.end() || !found->second.is_string) {
    return "";
  }
  return found->second.text;
}

TelemetryRecord parse_record(const std::string &line, int line_number) {
  TelemetryRecord record;
  record.line_number = line_number;

  const auto parsed = parse_flat_json_object(line);
  if (!parsed.error.empty()) {
    record.parse_error = parsed.error;
    return record;
  }

  record.session_id = get_string_field(parsed.fields, "session_id");
  record.timestamp = get_string_field(parsed.fields, "timestamp");
  record.vehicle_id = get_string_field(parsed.fields, "vehicle_id");
  record.signal = get_string_field(parsed.fields, "signal");

  const auto value = parsed.fields.find("value");
  if (value != parsed.fields.end()) {
    record.value_text = value->second.text;
    record.has_value = true;
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
  if (!record.parse_error.empty()) {
    return {{record.line_number, "record", record.parse_error}};
  }

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

  if (!record.has_value) {
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
