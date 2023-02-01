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
# Validate that the solutions for the python dataset pass or, if in a
# language where there are no solutions, that no runtime or compilation errors
# are raised.
DATASET_NAME=$1
DATASET_LOCATION=$2
DEBUG_LANG=${3:-""}
set -e

rm -rf eval_output/VALIDATION
if [[ "${DEBUG_LANG}" != "" ]]; then
  echo "Debugging ${DEBUG_LANG}"
fi

rm -rf "data/problem_code/${DATASET_NAME}"
python generate_test_code.py \
  --gin_file="configs/generate_code.gin" \
  --input="data/parsed_datasets/${DATASET_NAME}.jsonl" \
  --output="data/problem_code/${DATASET_NAME}" --debug_lang="${DEBUG_LANG}"

python scripts/make_validation_preds.py --name="${DATASET_NAME}" \
  --problem_code_path="data/problem_code/${DATASET_NAME}" \
  --output_path="data/validation_preds"

bash scripts/docker_eval.sh configs/validation.gin VALIDATION \
  "data/validation_preds/${DATASET_NAME}.jsonl" \
  "data/problem_code/${DATASET_NAME}" --samples=1 --validation \
  --language="${DEBUG_LANG}"
