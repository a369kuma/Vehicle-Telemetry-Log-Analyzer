.PHONY: cpp-validator test check clean

CXX ?= c++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -pedantic -O2

BUILD_DIR := build
CPP_VALIDATOR := $(BUILD_DIR)/telemetry_validator

cpp-validator: $(CPP_VALIDATOR)

$(CPP_VALIDATOR): src/cpp/telemetry_validator.cpp
	mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $< -o $@

test:
	PYTHONPATH=src python3 -m unittest discover -s tests

check: test cpp-validator
	./$(CPP_VALIDATOR) examples/sample_telemetry.jsonl || test $$? -eq 2

clean:
	rm -rf $(BUILD_DIR)
