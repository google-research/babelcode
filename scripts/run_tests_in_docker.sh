# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#!/bin/bash
# Run pytest tests inside of the docker image
set -e
PYTEST_ARGUMENTS=();
SPECIFIC_TEST="NONE";
SPECIFIC_FILE="tests/"
WITH_COVERAGE=0
while getopts "k:f:c" opt; do
  case $opt in
    k) SPECIFIC_TEST="${OPTARG}"
    ;;
    f) SPECIFIC_FILE="${OPTARG}"
    echo "Only running tests in \"${SPECIFIC_FILE}\""
    ;;
    c) WITH_COVERAGE=1
    echo "Running with coverage."
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
    exit 1
    ;;
  esac

  case $OPTARG in
    -*) echo "Option $opt needs a valid argument"
    exit 1
    ;;
  esac
done


if [[ "${SPECIFIC_TEST}" != "NONE" ]]
then
  echo "Running Specific test: ${SPECIFIC_TEST}"
  PYTEST_ARGUMENTS+="-k ${SPECIFIC_TEST}"
fi


echo "Building Image"
docker build -t pl-execution-framework:latest .

if [[ "${WITH_COVERAGE}" == "1" ]]
then 
  docker run -e ALLOW_EXECUTION=true pl-execution-framework:latest \
    sh scripts/coverage_tests.sh "${PYTEST_ARGUMENTS[@]} ${SPECIFIC_FILE}"
else

  docker run -e ALLOW_EXECUTION=true pl-execution-framework:latest \
    pytest -vv ${SPECIFIC_FILE} "${PYTEST_ARGUMENTS[@]}"
fi