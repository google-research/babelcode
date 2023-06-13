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
"""General Utility File."""

import json
import pathlib
from typing import Any, Callable, Dict, Optional

from absl import logging

__all__ = ["setup_logging", "jsonl_file_to_map"]


def setup_logging(file_name: str,
                  debug: bool,
                  log_path: Optional[pathlib.Path] = None):
  """Sets up logging."""
  log_path = log_path or pathlib.Path("logs")
  log_path = log_path.joinpath(file_name)
  log_path.mkdir(parents=True, exist_ok=True)

  if debug:
    logging.set_verbosity(logging.DEBUG)
  else:
    logging.set_verbosity(logging.INFO)

  logging.get_absl_handler().use_absl_log_file(file_name, log_path)


def jsonl_file_to_map(
    file_path: pathlib.Path,
    mapping_fn: Callable[[Dict[str, Any]], str]) -> Dict[str, Dict[str, Any]]:
  """Reads a json lines file to a dictionary mapping.

  Args:
      file_path: The File to read.
      mapping_fn: The key of each line to use as the main key in the dict.

  Returns:
      A dict where each element is `line[mapping_key]=line` where line is
      each line from the file.
  """

  return {mapping_fn(line): line for line in map(json.loads, file_path.open())}
