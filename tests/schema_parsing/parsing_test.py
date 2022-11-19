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

"""Tests for the SchemaType class and functionality."""

# Because of how pytest fixtures work, this error will be incorrectly triggered,
# so disable it for the file here. Pytest Fixture docs:
# https://docs.pytest.org/en/6.2.x/fixture.html
# pylint:disable=redefined-outer-name

from typing import Any, Dict

from babelcode import schema_parsing
import pytest

PRIMITIVE_MAP = {
    'boolean': 'Bool',
    'integer': 'Int',
    'character': 'Char',
    'float': 'Float',
    'double': 'Double',
    'long': 'Long',
    'string': 'String'
}


@pytest.fixture(scope='module')
def lang_spec():
  """Dummy specifications for testing."""

  yield schema_parsing.LanguageSchemaSpec(
      name='Testing',
      primitive_lang_map=PRIMITIVE_MAP,
      format_list_type=lambda t: f'vector({t})',
      format_map_type=lambda k, v: f'map({k},{v})',
      format_set_type=lambda t: f'set({t})')


# Use the Any type here as depth is not known.
def make_schema_type(
    type_str: str, language_type: Dict[str, Any]) -> schema_parsing.SchemaType:
  """Helper function to make the schema type."""
  schema_type = schema_parsing.SchemaType.from_generic_type_string(type_str)

  # Helper function to recursively set the language type.
  def recurse_set_lang_type(
      current_type: schema_parsing.SchemaType,
      lang_type: Dict[str, Any]) -> schema_parsing.SchemaType:
    current_type.lang_type = lang_type['expected']
    if 'elements' in lang_type:
      for i, element in enumerate(lang_type['elements']):
        current_type.elements[i] = recurse_set_lang_type(
            current_type.elements[i], element)

    if 'key_type' in lang_type:
      current_type.key_type = recurse_set_lang_type(current_type.key_type,
                                                    lang_type['key_type'])

    return current_type

  return recurse_set_lang_type(schema_type, language_type)


@pytest.mark.parametrize(['input_type', 'expected'],
                         list(PRIMITIVE_MAP.items()))
def test_parse_schema_and_input_order_primitives(
    input_type: str, expected: str,
    lang_spec: schema_parsing.LanguageSchemaSpec):
  """Test that parsing the schema for primitives."""
  input_schema = [{
      'name': 'arg0',
      'type': input_type
  }, {
      'name': 'expected',
      'type': input_type
  }]

  parsed_schema, input_order = schema_parsing.parse_schema_and_input_order(
      lang_spec, input_schema)

  expected_schema = {
      'arg0': make_schema_type(input_type, {'expected': expected}),
      'expected': make_schema_type(input_type, {'expected': expected})
  }
  assert parsed_schema == expected_schema
  assert input_order == ['arg0']


# Define these up here for ease of use.
LIST_LANG_TYPE = {
    'expected': 'vector(String)',
    'elements': [{
        'expected': 'String'
    }]
}

LIST_MAP_LANG_TYPE = {
    'expected':
        'vector(map(String,Int))',
    'elements': [{
        'expected': 'map(String,Int)',
        'elements': [{
            'expected': 'Int'
        }],
        'key_type': {
            'expected': 'String'
        }
    }]
}

SET_LANG_TYPE = {
    'expected': 'set(String)',
    'elements': [{
        'expected': 'String'
    }]
}


@pytest.mark.parametrize(['input_type', 'expected'],
                         [['list<string>', LIST_LANG_TYPE],
                          ['list<map<string;integer>>', LIST_MAP_LANG_TYPE],
                          ['set<string>', SET_LANG_TYPE]],
                         ids=['list', 'list_map', 'set'])
def test_parse_schema_and_input_order_data_structures(input_type, expected,
                                                      lang_spec):
  """Test that parsing the schema for data structures."""
  input_schema = [{
      'name': 'arg0',
      'type': input_type
  }, {
      'name': 'expected',
      'type': input_type
  }]

  parsed_schema, input_order = schema_parsing.parse_schema_and_input_order(
      lang_spec, input_schema)

  expected_schema = {
      'arg0': make_schema_type(input_type, expected),
      'expected': make_schema_type(input_type, expected)
  }
  assert parsed_schema == expected_schema
  assert input_order == ['arg0']


def test_parse_schema_and_input_order_mixed_types(lang_spec):
  """Test that parsing the schema when there are multiple types."""
  input_schema = [{
      'name': 'arg0',
      'type': 'map<string;boolean>'
  }, {
      'name': 'arg1',
      'type': 'long'
  }, {
      'name': 'expected',
      'type': 'float'
  }]

  parsed_schema, input_order = schema_parsing.parse_schema_and_input_order(
      lang_spec, input_schema)
  expected_schema = {
      'arg0':
          make_schema_type(
              'map<string;boolean>', {
                  'expected': 'map(String,Bool)',
                  'key_type': {
                      'expected': 'String'
                  },
                  'elements': [{
                      'expected': 'Bool'
                  }]
              }),
      'arg1':
          make_schema_type('long', {'expected': 'Long'}),
      'expected':
          make_schema_type('float', {'expected': 'Float'}),
  }
  assert parsed_schema == expected_schema
  assert input_order == ['arg0', 'arg1']


def test_parse_schema_and_input_order_unsupported(lang_spec):
  """Test that an error is raised when an unsupported type is passed."""
  input_schema = [{
      'name': 'arg0',
      'type': 'tuple<string|integer>'
  }, {
      'name': 'expected',
      'type': 'long'
  }]

  with pytest.raises(schema_parsing.SchemaTypeError):
    _ = schema_parsing.parse_schema_and_input_order(lang_spec, input_schema)
