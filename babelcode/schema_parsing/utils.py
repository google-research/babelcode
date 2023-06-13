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
"""Utilities for schema parsing."""
from typing import Mapping, Sequence, Union

from babelcode import utils

PRIMITIVE_TYPES = [
    'string', 'integer', 'boolean', 'float', 'double', 'character', 'long'
]
PRIMITIVE_WITH_NULL = ['string', 'character']
PRIMITIVE_DATA_STRUCTURES = ['list', 'map', 'tuple', 'set']

RECONCILABLE_TYPES = {
    'float': {'double'},
    'integer': {'long', 'float', 'double'},
    'long': {'double'},
    'character': {'string'}
}

GENERIC_TO_PYTHON_TYPE = {
    'list': list,
    'integer': int,
    'long': int,
    'float': float,
    'double': float,
    'boolean': bool,
    'string': str,
    # Internally, sets are kept as lists due to the fact that JSON does not
    # support sets. It is signifgantly easier to keep them as lists in the
    # framework so that we can use indexing on them and list specific methods.
    # This cuts down on the amount of code and special functions needed to
    # handle the two.
    'set': list,
    'map': dict,
    'tuple': tuple,
    'character': str
}


def allows_null(type_str: str) -> bool:
  """Is the type string allowed to be NULL."""
  return type_str in PRIMITIVE_WITH_NULL + PRIMITIVE_DATA_STRUCTURES


class SchemaTypeError(Exception):
  """Error raised when a SchemaType is not valid."""


SchemaValueType = Union[str, int, float, bool, Sequence['SchemaValueType'],
                        Mapping[Union[str, int], 'SchemaValueType']]
SchemaMapType = Mapping[str, SchemaValueType]
