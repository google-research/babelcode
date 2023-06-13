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
"""Testing code generation in each language."""
import pytest

# Because of how pytest fixtures work, this error will be incorrectly triggered,
# so disable it for the file here. Pytest Fixture docs:
# https://docs.pytest.org/en/6.2.x/fixture.html
# pylint:disable=redefined-outer-name
from babelcode import data_types
from babelcode import schema_parsing
from tests import utils as testing_utils

SchemaType = schema_parsing.SchemaType


@pytest.fixture()
def sample_schema():
  """Sample schema fixture."""
  yield {
      'arg0':
          SchemaType.from_generic_type_string('list<list<string>>'),
      'arg1':
          SchemaType.from_generic_type_string('boolean'),
      data_types.EXPECTED_KEY_NAME:
          SchemaType.from_generic_type_string('integer'),
  }


@pytest.mark.parametrize('lang_name', testing_utils.LANGS_TO_TEST)
class TestLanguageGeneration(testing_utils.BaseLanguageTestingClass):
  """Test that the code generation in each language is correct."""

  def _setup_conversion_test(self, lang_name, convert_type):
    """Helper function to do common actions to setup a conversion test."""
    self._setup_test(lang_name)
    self.type_spec = self.get_primitive_data(convert_type)

  def assert_convert_method_correct(self, convert_type, input_val, output_val):
    """Assert that a conversion method is correct."""
    underlying_type = SchemaType(convert_type)
    convert_fn = self.literal_translator.convert_primitive_fn
    assert convert_fn(underlying_type, input_val) == output_val

  @pytest.mark.parametrize('convert_type', schema_parsing.PRIMITIVE_TYPES)
  def test_convert_primitive(self, lang_name, convert_type):
    """Test converting each primitive type."""
    self._setup_conversion_test(lang_name, convert_type)
    self.assert_convert_method_correct(convert_type, self.type_spec['input'],
                                       self.type_spec['output'])

  @pytest.mark.parametrize('convert_type', schema_parsing.PRIMITIVE_WITH_NULL)
  def test_convert_primitive_null_value(self, lang_name, convert_type):
    """Test that converting the primitives that can be null are correct."""
    self._setup_conversion_test(lang_name, convert_type)
    self.assert_convert_method_correct(convert_type, None,
                                       self.type_spec['null_output'])

  @pytest.mark.parametrize('type_test', ['list', 'set'])
  @pytest.mark.parametrize('convert_type', schema_parsing.PRIMITIVE_TYPES)
  def test_convert_array_style_type(self, lang_name, type_test, convert_type):
    """Test that converting list is correct for each primitive."""
    self._setup_conversion_test(lang_name, convert_type)

    input_val = self.type_spec['input']
    template_dict = self.lang_spec['data_structures_literals']

    if type_test == 'list':
      arg_type = SchemaType.from_generic_type_string(
          f'list<list<{convert_type}>>')
      input_value = [[input_val, input_val], [input_val]]
      expected = template_dict['nested_list']
    else:
      arg_type = SchemaType.from_generic_type_string(f'set<{convert_type}>')
      input_value = [input_val]
      expected = template_dict['set']
    schema = self.parse_lang_schema({'arg0': arg_type})

    result = self.literal_translator.convert_array_like_type(
        schema['arg0'], input_value, type_test == 'set')
    expected = expected.replace('TYPE_VAL_1', self.type_spec['output'])

    type_name_to_replace = schema['arg0'].lang_type

    if lang_name in ['CSharp', 'Typescript']:
      type_name_to_replace = schema['arg0'].elements[0].lang_type

    expected = expected.replace('TYPE_NAME_1', type_name_to_replace)
    assert result == expected

  @pytest.mark.parametrize('convert_type', schema_parsing.PRIMITIVE_TYPES)
  def test_convert_map(self, lang_name, convert_type):
    """Test that converting map is correct for each primitive."""
    self._setup_conversion_test(lang_name, convert_type)

    input_val = self.type_spec['input']
    schema = self.parse_lang_schema({
        'arg0':
            SchemaType.from_generic_type_string(
                f'map<string;list<{convert_type}>>')
    })

    result = self.literal_translator.convert_map(
        schema['arg0'], {'key_value': [input_val, input_val]})

    map_template = self.lang_spec['data_structures_literals']['nested_map']
    expected = map_template.replace('TYPE_VAL_1', self.type_spec['output'])

    key_value = self.literal_translator.convert_primitive_fn(
        SchemaType(type_str='string'), 'key_value')
    expected = expected.replace('KEY_VAL_1', key_value)
    expected = expected.replace(
        'KEY_TYPE_1', self.lang_spec['primitives']['string']['type_name'])

    type_name_to_replace = schema['arg0'].lang_type

    if lang_name in ['CSharp', 'Go', 'Typescript']:
      type_name_to_replace = schema['arg0'].elements[0].lang_type

    expected = expected.replace('TYPE_NAME_1', type_name_to_replace)
    assert result == expected

  def test_string_correctly_escaped(self, lang_name):
    """Tests that language specific escaping works."""
    self._setup_test(lang_name)

    assert self.literal_translator
