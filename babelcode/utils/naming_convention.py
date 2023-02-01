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

"""Naming convention to support conversions to different styles."""
import enum
import re
from typing import List, Tuple


class NamingConvention(enum.Enum):
  """Enum for holding thee valid naming conventions."""
  SNAKE_CASE = 'SNAKE_CASE'
  CAMEL_CASE = 'CAMEL_CASE'
  PASCAL_CASE = 'PASCAL_CASE'


ALLOWED_NAMING_CONVENTIONS = {v.value: v for v in NamingConvention}


def _tokenize_name(name: str) -> List[str]:
  """Tokenizes a name by splitting on different casing and underscores.

  Args:
    name: The name to tokenize.

  Returns:
    The list of tokens found.
  """
  tokens = re.sub(r'((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z])|(?<=_)[a-zA-Z0-9])',
                  r' \1', name).split()

  return [t.replace('_', '') for t in tokens]


def convert_to_snake(tokens: List[str]) -> str:
  """Converts name to snake_case.

  Args:
    tokens: The tokens of the name.

  Returns:
    The name in snake_case.
  """
  return '_'.join(map(lambda t: t.lower(), tokens))


def _get_first_and_remaining_tokens(tokens: List[str]) -> Tuple[str, List[str]]:
  """Gets the first token and list of remaining."""
  first, *remaining = tokens
  if not first:
    first, *remaining = remaining
  return first, remaining


def convert_to_camel(tokens: List[str]) -> str:
  """Converts a name to camelCase.

  Args:
    tokens: The tokens of the name.

  Returns:
    The name in camelCase.
  """
  first, remaining = _get_first_and_remaining_tokens(tokens)
  if not remaining:
    return first.lower()

  return ''.join([first.lower(), *map(str.title, remaining)])


def convert_to_pascal(tokens: List[str]) -> str:
  """Converts a name to PascalCase.

  Args:
    tokens: The tokens of the name.

  Returns:
    The name in PascalCase.
  """
  first, remaining = _get_first_and_remaining_tokens(tokens)
  if not remaining:
    return first.title()

  return ''.join([first.title(), *map(str.title, remaining)])


CONVENTION_TO_CONVERT = {
    NamingConvention.SNAKE_CASE: convert_to_snake,
    NamingConvention.CAMEL_CASE: convert_to_camel,
    NamingConvention.PASCAL_CASE: convert_to_pascal,
}


def format_str_with_convention(convention: NamingConvention, seq: str) -> str:
  """Formats string for a specific convention.

  Args:
      convention (NamingConvention): Convention to use.
      seq (str): The sequence to format.

  Returns:
      The formatted sequence.
  """
  tokens = _tokenize_name(seq)
  convention_fn = CONVENTION_TO_CONVERT[convention]
  return convention_fn(tokens)
