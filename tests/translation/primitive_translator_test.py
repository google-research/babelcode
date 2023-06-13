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
"""Tests for primitive_translator."""

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
import pytest

SchemaType = schema_parsing.SchemaType

GENERIC_TO_IO = {
    'integer': (1, '1'),
    'boolean': (True, 'true'),
    'float': (1.0, '1.0'),
    'string': ('Test string', '"Test string"'),
    'character': ('t', "'t'"),
    'double': (1.0, '1.0'),
    'long': (1, '1'),
}


@pytest.mark.parametrize(['generic', 'value', 'expected'],
                         [(k, v[0], v[1]) for k, v in GENERIC_TO_IO.items()],
                         ids=list(GENERIC_TO_IO))
def test_make_primitive_translator_defaults(
    generic: str, value: schema_parsing.SchemaValueType, expected: str):
  """Test the default conversions of the primitive converter."""
  primitive_fn = translation.make_primitive_translator({})

  result = primitive_fn(SchemaType(generic), value)
  assert result == expected


@pytest.mark.parametrize(['generic', 'value'],
                         [(k, v[0]) for k, v in GENERIC_TO_IO.items()],
                         ids=list(GENERIC_TO_IO))
def test_make_primitive_translator_overrides(
    generic: str, value: schema_parsing.SchemaValueType):
  """Test that override the conversion method only changes the specified type.
  """
  override_fn = lambda v: f'{type(v).__name__} ==> {v}'
  primitive_fn = translation.make_primitive_translator({generic: override_fn})
  result = primitive_fn(SchemaType(generic), value)
  assert result == override_fn(value)

  for k, v in GENERIC_TO_IO.items():
    if k == generic:
      continue
    assert primitive_fn(
        SchemaType(k),
        v[0]) == v[1], f'{k} was overridden when it should not have been.'


def test_make_primitive_translator_not_supported():
  """Test that an error is raised for unsupported primitives."""
  primitive_fn = translation.make_primitive_translator({})
  with pytest.raises(data_types.IOPairError):
    _ = primitive_fn(SchemaType('unsupported'), 1)


@pytest.mark.parametrize('input_value', [1, 2.45, 0.22])
def test_convert_float(input_value):
  """Tests the convert float method."""
  expected = str(float(input_value))

  assert translation.convert_float(input_value) == expected

  suffix = 'f'
  assert translation.convert_float(input_value, suffix) == f'{expected}{suffix}'
