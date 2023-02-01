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
rm -rf "data/parsed_datasets/${DATASET_NAME}.jsonl"
python convert_dataset.py --dataset_name="$DATASET_NAME" --input_path="$DATASET_LOCATION"

bash scripts/validate_dataset.sh "${DATASET_NAME}" "${DATASET_LOCATION}"
