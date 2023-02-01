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

"""Testing each schema parser in each language."""
from babelcode import schema_parsing
from babelcode import data_types
from tests import utils as testing_utils
import pytest

SchemaType = schema_parsing.SchemaType


@pytest.mark.parametrize('lang_name', testing_utils.LANGS_TO_TEST)
class TestLanguageSchemaParsing(testing_utils.BaseLanguageTestingClass):
  """Testing each schema parser in each language."""

  def assert_parse_lang_schema_correct_basic(
      self, convert_type: str, expected_schema_type: SchemaType
  ):
    """Assertion that the basic SchemaTypes are correct.

    Args:
      convert_type: The input type string to convert to a SchemaType.
      expected_schema_type: The expected schema type.
    """

    input_schema_type = SchemaType.from_generic_type_string(convert_type)

    raw_schema = {
        'arg0': input_schema_type,
        'arg1': input_schema_type,
        data_types.EXPECTED_KEY_NAME: input_schema_type,
    }
    result_schema = schema_parsing.parse_language_schema(
        self.schema_spec, raw_schema
    )

    assert result_schema == {
        'arg0': expected_schema_type,
        'arg1': expected_schema_type,
        data_types.EXPECTED_KEY_NAME: expected_schema_type,
    }

  @pytest.mark.parametrize('convert_type', schema_parsing.PRIMITIVE_TYPES)
  def test_parse_lang_schema_primitives(
      self, lang_name: str, convert_type: str
  ):
    """Test that the primitives by themselves are parsed correctly."""
    self._setup_test(lang_name)
    expected_output = self.lang_spec['primitives'][convert_type]['type_name']

    expected_schema_type = SchemaType.from_generic_type_string(convert_type)
    expected_schema_type.lang_type = expected_output

    self.assert_parse_lang_schema_correct_basic(
        convert_type, expected_schema_type
    )

  @pytest.mark.parametrize('convert_type', ['string', 'integer', 'boolean'])
  @pytest.mark.parametrize('ds_type', testing_utils.DATA_STRUCTURES)
  def test_make_lang_schema_data_structures(
      self, lang_name: str, convert_type: str, ds_type: str
  ):
    """Test that the data structures with primitive types are correct."""
    self._setup_test(lang_name)
    io_spec = self.get_primitive_data(convert_type)
    target_type = io_spec['type_name']
    expected_ds_type_dict = self.lang_spec['data_structures_schema'][ds_type]

    def update_expected_lang_types(s_type, lang_type_dict) -> SchemaType:
      s_type.lang_type = lang_type_dict['expected'].replace(
          'TYPE_NAME_1', target_type
      )
      s_type.lang_type = s_type.lang_type.replace('TYPE_NAME_2', target_type)
      if 'elements' in lang_type_dict:
        print(s_type)
        s_type.elements = [
            update_expected_lang_types(s_type.elements[i], elem_type)
            for i, elem_type in enumerate(lang_type_dict['elements'])
        ]
      if 'key_type' in lang_type_dict:
        s_type.key_type = update_expected_lang_types(
            s_type.key_type, lang_type_dict['key_type']
        )
      return s_type

    ds_type = ds_type.replace('TYPE_NAME_1', convert_type)
    ds_type = ds_type.replace('TYPE_NAME_2', convert_type)
    expected_schema_type = SchemaType.from_generic_type_string(ds_type)
    expected_schema_type = update_expected_lang_types(
        expected_schema_type, expected_ds_type_dict
    )

    if 'map' in ds_type and convert_type == 'integer' and lang_name == 'R':
      with pytest.raises(schema_parsing.SchemaTypeError):
        input_schema_type = SchemaType.from_generic_type_string(ds_type.replace('TYPE_NAME_1', convert_type))

        raw_schema = {
            'arg0': input_schema_type,
            'arg1': input_schema_type,
            data_types.EXPECTED_KEY_NAME: input_schema_type,
        }
        schema_parsing.parse_language_schema(
            self.schema_spec, raw_schema
        )
    else:
      self.assert_parse_lang_schema_correct_basic(
          convert_type=ds_type.replace('TYPE_NAME_1', convert_type),
          expected_schema_type=expected_schema_type,
      )
