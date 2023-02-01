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

"""Command data type."""
import dataclasses
from typing import List, Dict, Any


@dataclasses.dataclass
class Command:
  """The bash command to execute along with the timeout to use with it.

  The command needs to be formatted as a list of arguments for it to work with
  the subprocess shell. For example the command `rm -rf dir` would be passed as
  `["rm","-rf","dir"]`.

  Attributes:
    command: The string command to run.
    timeout: The timeout to use with the command. Defaults to 10.
  """
  command: List[str]
  timeout: int = 10
  
  def to_dict(self) -> Dict[str, Any]:
    """Converts a command to a dict."""
    return dataclasses.asdict(self)
  
  @classmethod
  def from_dict(cls, command_dict:Dict[str,Any]) -> 'Command':
    """Converts a dict to a command."""
    return cls(**command_dict)
