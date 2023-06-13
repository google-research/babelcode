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
from typing import Any, List

import pytest
from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils

SchemaType = schema_parsing.SchemaType


class DummyLiteralTranslator(translation.LiteralTranslator):
  """Dummy LiteralTranslator for testing."""

  def format_list(self, generic_type: SchemaType,
                  list_values: List[Any]) -> str:
    """Format the list of values to the code to initialize the list.

    Args:
      generic_type: The underlying schema type for the list.
      list_values: The list of strings that are the literal initialization code
        for each element of the list.

    Returns:
      The code to initialize a list object in the current language.
    """
    return f'({generic_type.to_generic()}, list[{", ".join(list_values)}])'

  def format_set(self, generic_type: SchemaType, set_values: List[str]) -> str:
    """Format the list of values to the code to initialize the set.

    Args:
      generic_type: The underlying schema type for the list.
      set_values: The list of strings that are the literal initialization code
        for each element of the set.

    Returns:
      The code to initialize a set object in the current language.
    """
    # Some languages require the generic_type to create the set.
    return f'({generic_type.to_generic()}, set[{", ".join(set_values)}])'

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]) -> str:
    """Format the map with keys and entries to the code to initialize the map.

    We include the `key_type` and `value_type` for languages that require them
    to initialize the map(i.e. Golang).

    Args:
      key_type: The SchemaType of the key_type.
      value_type: The SchemaType of the value.
      entries: The list of code to initialize the entries.

    Returns:
      The code to initialize an map object in the current language.
    """
    return (f'({key_type.to_generic()}, {value_type.to_generic()},'
            f' {", ".join(entries)})')

  def format_map_entry(self, key: str, value: str) -> str:
    """Format a single map entry to the literal code.

    Args:
      key: The code to initialize the key.
      value: The code to initialize the value.

    Returns:
      The code to make the single entry.
    """
    return f'[{key}|{value}]'


class TestLiteralTranslator:

  def setup_method(self):
    """Setup for each test."""
    self.literal_translator = DummyLiteralTranslator(
        'Testing',
        naming_convention=utils.NamingConvention.CAMEL_CASE,
        convert_primitive_fn=translation.make_primitive_translator({}),
    )

  def test_generate_test_case_literals(self):
    """Test the generate test case literals function."""
    input_tc = {
        'idx': '0',
        'inputs': {
            'arg0': 1,
            'arg2': 'Hello World\n'
        },
        'outputs': 1e-2,
    }

    schema = {
        'arg0': SchemaType('integer'),
        'arg2': SchemaType('string'),
        data_types.EXPECTED_KEY_NAME: SchemaType('float'),
    }

    input_order = ['arg2', 'arg0']

    result = self.literal_translator.generate_test_case_literals(
        '1', input_tc, schema, input_order)

    assert result == {
        'idx': '0',
        'inputs': ['"Hello World\\n"', '1'],
        'outputs': '0.01',
    }

  def test_convert_primitive_to_literal(self):
    """Test the convert primitive to literal."""
    generic_type = SchemaType('boolean')
    result = self.literal_translator.convert_var_to_literal(generic_type, False)
    assert result == 'false'

  @pytest.mark.parametrize('type_str', ['set', 'list'])
  def test_convert_array_like_to_literal(self, type_str):
    """Test converting array like datastructures to literal code."""
    generic_type = SchemaType.from_generic_type_string(f'{type_str}<integer>')
    input_values = [1, 2, 1]
    result = self.literal_translator.convert_var_to_literal(
        generic_type, input_values)
    expected_values = input_values
    if type_str == 'set':
      expected_values = set(input_values)

    expected_values = ', '.join(map(str, expected_values))
    expected = f'({generic_type.to_generic()}, {type_str}[{expected_values}])'
    assert result == expected

  def test_convert_map_to_literal(self):
    """Test converting maps to literal code."""
    generic_type = SchemaType.from_generic_type_string('map<string;integer>')
    input_values = {'1': 1, '2': 2}
    result = self.literal_translator.convert_var_to_literal(
        generic_type, input_values)

    expected_value = '["1"|1], ["2"|2]'

    expected = '(string, integer, ' + expected_value + ')'
    assert result == expected

  def test_convert_list_of_sets(self):
    """Test list of sets."""
    generic_type = SchemaType.from_generic_type_string('list<set<integer>>')
    input_values = [[1, 2]]

    expected = '(list<set<integer>>, list[(set<integer>, set[1, 2])])'
    result = self.literal_translator.convert_var_to_literal(
        generic_type, input_values)
    assert result == expected
