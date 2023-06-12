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

#! /bin/bash
# Script to evaluate the predictions by running the full pipeline.

CONFIG_PATH=$1
OUTPUT_DIR_NAME=$2
PRED_PATH=$3
PRED_FILE=$(basename "${PRED_PATH}")
TEST_CODE_PATH=$4
shift 4

OTHER_ARGS=( "$@" )

echo "Building Image"

echo "CFG={$CONFIG_PATH}"
echo "PREDICTION_PATH=predictions/${PRED_FILE}"
echo "OUTPUT_DIR_NAME=${OUTPUT_DIR_NAME}"
echo "Other Arguments='${OTHER_ARGS[@]}'"
mkdir -p tmp
cp "${PRED_PATH}" "tmp/${PRED_FILE}"


docker build -t babelcode:latest .

docker run -v "$(pwd)/tmp":"$(pwd)/tmp":z -e ALLOW_EXECUTION=true \
  babelcode:latest \
  python evaluate_predictions.py \
  "${OTHER_ARGS[@]}" \
  --gin_file="${CONFIG_PATH}" --experiment_name="${OUTPUT_DIR_NAME}" \
  --predictions="tmp/${PRED_FILE}" --output_path="$(pwd)/tmp" \
  --test_code="${TEST_CODE_PATH}" \
  --overwrite
  

cp -r "tmp/${OUTPUT_DIR_NAME}" "eval_output/"
rm -rf tmp