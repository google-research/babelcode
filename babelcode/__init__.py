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
"""Init for main package."""
from babelcode import code_generator
from babelcode import data_types
from babelcode import languages
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.drivers import execute_bc_predictions
from babelcode.drivers import generate_code_for_questions
from babelcode.drivers import generate_prompt_info
from babelcode.drivers import load_progress_from_dir

QUESTION_DATA_KEYS = {
    "test_code", "entry_fn_name", "entry_cls_name", "qid", "language",
    "test_case_ids"
}
