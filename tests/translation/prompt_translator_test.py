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

"""Tests for prompt_translator."""
# Because of how pytest fixtures work, this error will be incorrectly triggered,
# so disable it for the file here. Pytest Fixture docs:
# https://docs.pytest.org/en/6.2.x/fixture.html
# pylint:disable=redefined-outer-name

from typing import Dict

import pytest

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils

SchemaMapType = schema_parsing.SchemaMapType
SchemaType = schema_parsing.SchemaType
SchemaValueType = schema_parsing.SchemaValueType
Question = data_types.Question


class DummyPromptTranslator(translation.PromptTranslator):

  @property
  def word_replacement_map(self) -> Dict[str, str]:

    return {'vector': ['list'], 'map': ['dict', 'dictionary', 'dictionaries']}

  @property
  def signature_template(self) -> str:
    return ('{%- if docstring is not none -%}{{docstring~"\n"}}{%-endif-%}' +
            ' def {{entry_cls_name}} {{entry_fn_name}}' +
            '({{signature}}){{return_type}}:{{params|join(", ")}}')

  def clean_docstring_for_lang(self, docstring: str) -> str:
    return docstring.replace('.', '?')

  def translate_entry_function_name(
      self,
      entry_fn_name: str,
  ) -> str:
    return entry_fn_name

  def translate_entry_cls_name(self, entry_cls_name: str) -> str:
    return entry_cls_name

  def format_docstring_for_lang(self, docstring: str) -> str:
    return '| '.join(docstring.splitlines(True)).strip()

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    if use_type_annotation:
      return f'{arg_name}: {arg_type.lang_type}'

    return arg_name

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    if use_type_annotation:
      return f' -> {return_type.lang_type}'
    return ''


@pytest.fixture(scope='module')
def schema():
  yield {
      'arg0': SchemaType('integer', 'Int'),
      'arg1': SchemaType('boolean', 'Bool'),
      data_types.EXPECTED_KEY_NAME: SchemaType('float', 'double')
  }


@pytest.fixture(scope='module')
def input_order():
  yield ['arg1', 'arg0']


class TestPromptTranslator:

  def setup_method(self):
    self.translator = DummyPromptTranslator('testing',
                                            utils.NamingConvention.SNAKE_CASE)

  def test_translate_prompt(self):
    prompt = """This is a test prompt with Lists. Testing for Python?
      It should dict be formatted properly!"""

    result = self.translator.translate_prompt('python', prompt, 'test')

    assert result == """This is a test prompt with Vectors? Testing for Testing?
      It should map be formatted properly!"""

  def test_translate_signature(self, schema, input_order):
    result = self.translator.translate_signature('TEST_FUNCTION', 'SOL', schema,
                                                 input_order, True)
    expected = ('def SOL TEST_FUNCTION(arg1: Bool, arg0: Int) -> double:' +
                'arg1, arg0')
    assert result == expected

  def test_translate_docstring(self, schema, input_order):
    docstring = '\nTest\nTest line 2\n'

    result = self.translator.translate_signature_with_docstring(
        'Python', docstring, 'test', 'sol', schema, input_order, False)

    assert result == ('| Test\n| Test line 2\ndef sol test(arg1, arg0):arg1, '
                      'arg0')
