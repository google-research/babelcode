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

"""General Utilities that are not large enough to warrant their own file."""
import datetime
import random
from typing import Mapping, Sequence, Union

import numpy as np

TestValueType = Union[
    str,
    int,
    float,
    bool,
    Sequence['TestValueType'],
    Mapping[Union[str, int], 'TestValueType'],
]


def set_seed(seed):
  random.seed(seed)
  np.random.seed(seed)


def convert_timedelta_to_milliseconds(delta: datetime.timedelta) -> float:
  """Converts a timedelta to milliseconds.

  Args:
    delta: the time delta

  Returns:
    The milliseconds.
  """

  return delta.total_seconds() * 1000


def format_timedelta_str(td: datetime.timedelta) -> str:
  """Formats a timedelta into a readable string."""
  hours, remainder = divmod(td.total_seconds(), 3600)
  minutes, seconds = divmod(remainder, 60)
  return '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))
