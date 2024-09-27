#!/bin/bash

TARGET_PATH="./lambdas/"

print_header() {
  echo -e "\033[1mRuntime Environment:\033[0m"
  echo -e "\033[1;34m📅 Date:        \033[0m$(date)"
  echo -e "\033[1;34m📂 Repository:  \033[0m$(basename "$(git rev-parse --show-toplevel)")"
  echo -e "\033[1;34m🌿 Branch:      \033[0m$(git rev-parse --abbrev-ref HEAD)"
  echo -e "\033[1;34m🔗 Git Hash:    \033[0m$(git rev-parse --short HEAD)"
  echo
}

run_make() {
  local dir=$1
  make_output=$(make "${dir}" 2>&1)
  echo "$make_output"
}

print_summary() {
  echo -e "\n\033[1m\033[37mSummary of test executions:\033[0m"
  printf "\033[1;34m📂 Total directories: \033[0m%4d\n" "${total_dirs}"
  printf "\033[1;34m🧪 Total tests:       \033[0m%4d\n" "${total_tests}"
  printf "\033[1;32m✅ Successful tests:  \033[0m%4d\n" "${successful_tests}"
  printf "\033[1;31m❌ Failed tests:      \033[0m%4d\n" "${failed_tests}"
  echo -e "\033[1;34m⏱️  Total runtime:    \033[0m${runtime} seconds"
}

print_header

start_time=$(date +%s)

test_dirs=$(find $TARGET_PATH -type d -name tests)
total_dirs=$(echo "$test_dirs" | wc -l)
total_tests=0
successful_tests=0
failed_tests=0

# Loop through each test directory and run tests
for dir in $test_dirs; do
  make_output=$(run_make "$(dirname "$dir")")
  num_tests=$(echo "$make_output" | grep -o 'Ran [0-9]* tests' | awk '{print $2}')
  total_tests=$((total_tests + num_tests))
  if echo "$make_output" | grep -q 'OK'; then
    successful_tests=$((successful_tests + num_tests))
  else
    failed_tests=$((failed_tests + num_tests))
  fi
done

end_time=$(date +%s)
runtime=$((end_time - start_time))

print_summary
