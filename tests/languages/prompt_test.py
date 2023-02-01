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

"""Testing code prompt translation in each language."""
# Because of how pytest fixtures work, this error will be incorrectly triggered,
# so disable it for the file here. Pytest Fixture docs:
# https://docs.pytest.org/en/6.2.x/fixture.html
# pylint:disable=redefined-outer-name
from absl import logging
from babelcode import data_types
from babelcode import schema_parsing
import pytest
from tests import utils as testing_utils

SchemaType = schema_parsing.SchemaType


@pytest.mark.parametrize('lang_name', testing_utils.LANGS_TO_TEST)
class TestLanguagePromptTranslation(testing_utils.BaseLanguageTestingClass):

  def _setup_test(self, lang_name):
    super()._setup_test(lang_name)
    self.prompt_translator = self.lang.make_prompt_translator()
    self.prompt_spec = self.lang_spec['prompt_translation']

  def test_format_docstring(self, lang_name):
    """Test that formatting the docstring works."""
    self._setup_test(lang_name)
    input_docstring = 'Test Docstring.\n/**///*/--"""'
    expected = self.prompt_spec['docstring']
    cleaned_docstring = self.prompt_translator.clean_docstring_for_lang(
        input_docstring
    )
    result = self.prompt_translator.format_docstring_for_lang(cleaned_docstring)
    assert result == expected

  def test_signature_argument(self, lang_name):
    """Tests that the translating an argument in signature works."""
    self._setup_test(lang_name)
    type_name = self.lang_spec['primitives']['string']['type_name']

    expected = self.prompt_spec['signature_argument'].replace(
        'TYPE_NAME', type_name
    )
    result = self.prompt_translator.translate_signature_argument_to_lang(
        'arg_name', SchemaType('string', type_name), use_type_annotation=True
    )

    assert result == expected

  def test_return_type(self, lang_name):
    """Tests that the translating the return type in signature works."""
    self._setup_test(lang_name)
    type_name = self.lang_spec['primitives']['string']['type_name']

    expected = self.prompt_spec['return_type'].replace('TYPE_NAME', type_name)
    result = self.prompt_translator.translate_signature_returns_to_lang(
        SchemaType('string', type_name), use_type_annotation=True
    )

    assert result == expected

  def test_argument_name(self, lang_name):
    """Test that translating argument name to language works."""
    self._setup_test(lang_name)
    expected = self.prompt_spec['argument_name']
    result = self.prompt_translator.translate_argument_name_to_lang('arg_name')

    assert result == expected

  def test_signature_with_docstring(self, lang_name):
    """Test that translating signature with the docstring works."""

    self._setup_test(lang_name)
    type_name = self.lang_spec['primitives']['string']['type_name']
    schema = {
        'arg_name': SchemaType('string', type_name),
        data_types.EXPECTED_KEY_NAME: SchemaType('string', type_name),
    }
    input_order = ['arg_name']

    signature = self.prompt_spec['signature_argument'].replace(
        'TYPE_NAME', type_name
    )
    return_type = self.prompt_spec['return_type'].replace(
        'TYPE_NAME', type_name
    )
    docstring = self.prompt_spec['docstring']

    expected = self.prompt_spec['signature_with_docstring']
    expected = expected.replace('SIGNATURE', signature)
    expected = expected.replace('RETURNS', return_type)
    expected = expected.replace('DOCSTRING', docstring.replace('\\', '\\\\'))

    result = self.prompt_translator.translate_signature_with_docstring(
        'Python',
        'Test Docstring.\n/**///*/--"""',
        'test',
        'Solution',
        schema,
        input_order,
        True,
    )
    assert result == expected
