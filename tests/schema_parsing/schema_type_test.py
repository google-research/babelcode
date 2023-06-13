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
"""Tests for non-language code generator functionality."""
import copy
from typing import Any, Dict, Optional, Union

from babelcode import schema_parsing
from babelcode import data_types
import pytest

SchemaType = schema_parsing.SchemaType

# Define these test cases up here to not clutter up the parameterization.
SCHEMA_TYPE_TCS = {}
SCHEMA_TYPE_TCS['primitive'] = {
    'str': 'integer',
    'schema': SchemaType(type_str='integer'),
}
SCHEMA_TYPE_TCS['primitive_ds_single'] = {
    'str':
        'string[]',
    'schema':
        SchemaType(type_str='list', elements=[SchemaType(type_str='string')]),
}

SCHEMA_TYPE_TCS['primitive_nested_ds'] = {
    'str':
        'list<tuple<boolean>>',
    'schema':
        SchemaType(
            type_str='list',
            elements=[SchemaType('list', elements=[SchemaType('boolean')])],
        ),
}
SCHEMA_TYPE_TCS['double_brace'] = {
    'str':
        'integer[][]',
    'schema':
        SchemaType(
            type_str='list',
            elements=[SchemaType('list', elements=[SchemaType('integer')])],
        ),
}
SCHEMA_TYPE_TCS['map_nested_list'] = {
    'str':
        'map<string;list<integer>>',
    'schema':
        SchemaType(
            type_str='map',
            key_type=SchemaType('string'),
            elements=[
                SchemaType(type_str='list', elements=[SchemaType('integer')])
            ],
        ),
}
SCHEMA_TYPE_TCS['nested_tuple'] = {
    'str':
        'tuple<tuple<string|string>|tuple<integer>>',
    'schema':
        SchemaType(
            type_str='tuple',
            elements=[
                SchemaType(
                    type_str='list',
                    elements=[
                        SchemaType('string'),
                    ],
                ),
                SchemaType(type_str='list', elements=[SchemaType('integer')]),
            ],
        ),
}


class TestSchemaType:

  @pytest.mark.parametrize('schema_name', list(SCHEMA_TYPE_TCS))
  def test_from_generic_type_str(self, schema_name: str):
    """Test parsing the generic type strings."""
    input_str = SCHEMA_TYPE_TCS[schema_name]['str']
    expected = SCHEMA_TYPE_TCS[schema_name]['schema']
    result = SchemaType.from_generic_type_string(input_str)
    assert result == expected

  def test_depth(self):
    """Test getting depth of schema type."""
    schema_type = SchemaType.from_generic_type_string(
        'map<string;list<integer>>')
    assert schema_type.depth == 2


@pytest.mark.parametrize(
    ['left', 'right', 'expected_str'],
    [
        ['float', 'double', 'double'],
        ['integer', 'double', 'double'],
        ['float', 'integer', 'float'],
        ['integer', 'long', 'long'],
        ['long', 'double', 'double'],
        ['list<double>', 'list<float>', 'list<double>'],
        ['map<string;float>', 'map<string;double>', 'map<string;double>'],
        ['tuple<float|double>', 'tuple<double|float>', 'list<double>'],
        ['string', 'integer', None],
        ['string', 'character', 'string'],
        ['list<character>', 'list<string>', 'list<string>'],
    ],
)
def test_reconcile_type(left: str, right: str, expected_str: Optional[str]):
  """Test reconciliation of types."""
  left = SchemaType.from_generic_type_string(left)
  right = SchemaType.from_generic_type_string(right)
  result = schema_parsing.reconcile_type(left, right)
  if expected_str is not None:
    assert result.to_generic() == expected_str
    expected = SchemaType.from_generic_type_string(expected_str)
  else:
    expected = None

  assert result == expected


@pytest.mark.parametrize(
    ['type_str', 'value'],
    [
        ('list<list<map<string;integer>>>', [[{
            'A': 1
        }]]),
        ('list<integer>', []),
        ('string', ''),
    ],
    ids=['list_list_map', 'null_list', 'empty_string'],
)
def test_validate_correct_type_valid(type_str: str, value: Any):
  """Test basic validation where no changes occur."""
  schema = SchemaType.from_generic_type_string(type_str)

  result = schema_parsing.validate_correct_type(schema, copy.deepcopy(value))
  # Make sure no changes happen
  assert result == value


@pytest.mark.parametrize(
    ['type_str', 'value', 'expected'],
    [
        ('list<integer>', None, []),
        ('map<integer;integer>', {
            '1': 1
        }, {
            1: 1
        }),
        ('double', 1, 1.0),
    ],
    ids=['empty_list', 'cast_int_key', 'int_to_float'],
)
def test_validate_correct_type_conversions(type_str, value, expected):
  """Test validation when the value must be modified."""
  schema = SchemaType.from_generic_type_string(type_str)

  result = schema_parsing.validate_correct_type(schema, copy.deepcopy(value))
  # Make sure no changes happen
  assert result == expected


@pytest.mark.parametrize(
    ['type_str', 'value'],
    [
        ('list<integer,integer>', [1, 1]),
        ('integer', 'String'),
        ('integer', None),
        ('set<integer>', {'hello'}),
        ('map<string;integer>', {
            (1,): 1
        }),
        ('map<string;integer>', {
            'hello': 'hello'
        }),
        ('list<integer>', [1, 'hello']),
    ],
    ids=[
        'multiple_elements',
        'incorrect_type',
        'non_null',
        'set_invalid_element',
        'map_invalid_key',
        'map_invalid_element',
        'list_multiple_types',
    ],
)
def test_validate_correct_type_invalid(type_str: str, value: Any):
  """Test cases where validating types should fail."""
  schema = SchemaType.from_generic_type_string(type_str)
  with pytest.raises(schema_parsing.SchemaTypeError):
    schema_parsing.validate_correct_type(schema, value)


@pytest.mark.parametrize('iterable_type', ['set', 'list'])
def test_validate_correct_type_convert_iterable(iterable_type: str):
  """Test that the value conversion works for lists."""
  type_str = f'{iterable_type}<float>'
  schema = SchemaType.from_generic_type_string(type_str)

  result = schema_parsing.validate_correct_type(schema, [1, 1.0, 2.0, 3])
  assert result == [1.0, 1.0, 2.0, 3.0]


@pytest.mark.parametrize(
    ['key_type', 'expected'],
    [('string', {
        '1': 2.0,
        '3': 4.0
    }), ('integer', {
        1: 2.0,
        3: 4.0
    })],
    ids=['str_keys', 'int_keys'],
)
def test_validate_correct_type_convert_dict(key_type: str,
                                            expected: Dict[Union[str, int],
                                                           Union[int, float]]):
  """Test that the value conversion works for dicts."""
  type_str = f'map<{key_type};float>'
  schema = SchemaType.from_generic_type_string(type_str)

  result = schema_parsing.validate_correct_type(schema, {'1': 2, 3: 4.0})
  assert result == expected


@pytest.mark.parametrize(
    ['left', 'right', 'expected'],
    [
        ['list<null>', 'list<integer>', True],
        ['list<null>', 'list<list<integer>>', True],
        ['map<string;integer>', 'map<integer;string>', False],
        ['integer', 'boolean', False],
        ['map<string;integer>', 'map<string;integer>', True],
        ['tuple<string|integer>', 'tuple<string>', False],
        ['string', 'null', True],
        ['null', 'string', True],
    ],
)
def test_generic_equal(left: str, right: str, expected: bool):
  """Test the generic equivalence function."""
  left = SchemaType.from_generic_type_string(left)
  right = SchemaType.from_generic_type_string(right)
  assert schema_parsing.is_generic_equal(left, right) == expected
  assert schema_parsing.is_generic_equal(right, left) == expected

  # Testing that types are generically equal to themselves.
  assert schema_parsing.is_generic_equal(left, left)
  assert schema_parsing.is_generic_equal(right, right)
