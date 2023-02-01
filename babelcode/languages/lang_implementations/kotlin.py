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

"""Kotlin Specific classes and functions."""

import pathlib
from typing import Dict, List

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.languages import language

SchemaMapType = schema_parsing.SchemaMapType
SchemaType = schema_parsing.SchemaType
SchemaValueType = schema_parsing.SchemaValueType


def make_commands(file_path: pathlib.Path) -> List[data_types.Command]:
  """Makes the kotlin commands to run source code."""
  return [
      data_types.Command(
          ['kotlinc', '-script', file_path.name, '-no-reflect', '-nowarn'],
          timeout=30),
      # data_types.Command(['java', '-jar', 'solution.jar'], timeout=15)
  ]


class KotlinLiteralTranslator(translation.LiteralTranslator):
  """The Kotlin generator."""

  def format_list(self, generic_type: SchemaType,
                  list_values: List[str]) -> str:
    """Formats a list for Kotlin."""
    _ = generic_type
    return f'arrayListOf({", ".join(list_values)})'

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]):
    """Formats a map for Kotlin."""
    _ = key_type, value_type
    return f'mapOf({", ".join(entries)})'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a map entry for Kotlin."""
    return f'{key} to {value}'

  def format_set(self, generic_type: SchemaType, set_values: List[str]) -> str:
    """Formats a set for Kotlin."""
    return f'hashSetOf({", ".join(set_values)})'


class KotlinPromptTranslator(translation.PromptTranslator):
  """The Kotlin prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The Kotlin words to replace."""
    return {
        'array': ['vector', 'list'],
        'map': ['dict', 'dictionary', 'dictionaries'],
    }

  @property
  def signature_template(self) -> str:
    """The Kotlin signature template."""
    return '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        'fun {{entry_fn_name}}({{signature}}): {{return_type}} {'
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Cleans a docstring for Kotlin."""
    return translation.escape_cpp_like_comment_chars(docstring)

  def format_docstring_for_lang(self, docstring: str) -> str:
    return translation.format_cpp_like_docstring(docstring)

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature argument to Kotlin."""
    _ = use_type_annotation
    return f'{arg_name}: {arg_type.lang_type}'

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to Kotlin."""
    _ = use_type_annotation
    return return_type.lang_type


language.LanguageRegistry.register_language(
    language.Language(
        name='Kotlin',
        file_ext='kts',
        literal_translator_cls=KotlinLiteralTranslator,
        command_fn=make_commands,
        primitive_conversion_mapping={
            'float': lambda v: translation.convert_float(v, 'f')
        },
        prompt_translator_cls=KotlinPromptTranslator,
        naming_convention=utils.NamingConvention.CAMEL_CASE,
        escape_fn=lambda s: s.replace('$', '\\$')))
