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

"""Utilities Module."""
from pathlib import Path

from babelcode.utils.metric_utils import write_to_tb_writer
from babelcode.utils.file_utils import *
from babelcode.utils.naming_convention import format_str_with_convention
from babelcode.utils.naming_convention import NamingConvention
from babelcode.utils.utilities import convert_timedelta_to_milliseconds
from babelcode.utils.utilities import format_timedelta_str
from babelcode.utils.utilities import set_seed
from babelcode.utils.utilities import TestValueType

PROJECT_ROOT = (Path(__file__) / ".." / ".." / "..").resolve()
FIXTURES_PATH = PROJECT_ROOT / "test_fixtures"

TEMP_EXECUTION_PATH=PROJECT_ROOT/'tmp_execution_results'