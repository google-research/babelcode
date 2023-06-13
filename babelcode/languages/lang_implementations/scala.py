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
"""Scala Specific classes and functions."""

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
  """Makes the Scala commands to run source code."""
  return [
      data_types.Command(['scalac', '-d', 'evaluation.jar', file_path.name],
                         timeout=15),
      data_types.Command(
          ['scala', '-d', 'evaluation.jar', 'QuestionEvaluator'],),
  ]


class ScalaLiteralTranslator(translation.LiteralTranslator):
  """The Scala generator."""

  def format_list(self, generic_type: SchemaType,
                  list_values: List[str]) -> str:
    """Formats a list for Scala."""
    _ = generic_type
    return f'List({", ".join(list_values)})'

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]):
    """Formats a map for Scala."""
    _ = key_type, value_type
    return f'HashMap({", ".join(entries)})'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a map entry for Scala."""
    return f'{key} -> {value}'

  def format_set(self, generic_type: SchemaType, set_values: List[str]) -> str:
    """Formats a set for Scala."""
    return f'HashSet({", ".join(set_values)})'


class ScalaPromptTranslator(translation.PromptTranslator):
  """The Scala prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The Scala words to replace."""
    return {
        'array': ['vector'],
        'map': ['dict', 'dictionary', 'dictionaries'],
    }

  @property
  def signature_template(self) -> str:
    """The Scala signature template."""
    return '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        'def {{entry_fn_name}}({{signature}}){{return_type}} = {',
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Cleans a docstring for Scala."""
    return translation.escape_cpp_like_comment_chars(docstring)

  def format_docstring_for_lang(self, docstring: str) -> str:
    return translation.format_cpp_like_docstring(docstring)

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature argument to Scala."""
    _ = use_type_annotation
    return f'{arg_name}: {arg_type.lang_type}'

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to Scala."""
    if use_type_annotation:
      return f': {return_type.lang_type}'
    return ''


language.LanguageRegistry.register_language(
    language.Language(
        name='Scala',
        file_ext='scala',
        literal_translator_cls=ScalaLiteralTranslator,
        command_fn=make_commands,
        primitive_conversion_mapping={
            'float': lambda v: translation.convert_float(v, 'F'),
            'long': lambda v: f'{v}L',
        },
        prompt_translator_cls=ScalaPromptTranslator,
        naming_convention=utils.NamingConvention.CAMEL_CASE,
        escape_fn=lambda s: s,
    ))
