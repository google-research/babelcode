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

"""Golang Specific Classes and Functions."""

import pathlib
from typing import Any, Dict, List

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.languages import language

SchemaType = schema_parsing.SchemaType


class GoLiteralTranslator(translation.LiteralTranslator):
  """The Golang generator."""

  def format_list(self, generic_type: SchemaType,
                  list_values: List[str]) -> str:
    """Formats a list for Golang."""
    _ = generic_type
    return '{' + ', '.join(list_values) + '}'

  def convert_array_like_type(self, generic_type: SchemaType,
                              list_value: List[Any],
                              use_format_set: bool) -> str:
    """Converts an array like with the Golang specific formatting."""
    result = super().convert_array_like_type(generic_type, list_value,
                                             use_format_set)
    return f'{generic_type.lang_type}{result}'

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]) -> str:
    """Formats a map for Golang."""
    entry_str = '{' + ', '.join(entries) + '}'
    return f'map[{key_type.lang_type}]{value_type.lang_type}{entry_str}'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a map entry for Golang."""
    return f'{key}: {value}'

  def format_set(self, generic_type: SchemaType, set_values: List[str]) -> str:
    """Formats a set for Golang."""
    _ = generic_type
    return '{' + ', '.join(map(lambda v: f'{v}: true', set_values)) + '}'


def make_commands(file_path: pathlib.Path) -> List[data_types.Command]:
  """Makes the command to run a Golang source file.

  Args:
    file_path: The path to the file to run.

  Returns:
    The list of commands to run.
  """
  return [
      data_types.Command(['go', 'build', '-o', 'main.exe', file_path.name]),
      data_types.Command(['./main.exe'])
  ]


class GoPromptTranslator(translation.PromptTranslator):
  """The Golang prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The Golang words to replace."""
    return {
        'array': ['vector', 'list'],
        'map': ['dict', 'dictionary', 'dictionaries'],
    }

  @property
  def signature_template(self) -> str:
    """The Golang signature template."""
    return '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        'func {{entry_fn_name}}({{signature}}) {{return_type}} {'
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Translates a docstring for Golang."""
    return docstring.replace('//', '\\/\\/')

  def format_docstring_for_lang(self, docstring: str) -> str:
    """Formats a docstring for Golang."""
    out = []
    for line in docstring.splitlines(False):
      out.append(f'// {line}')
    return '\n'.join(out)

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature argument to Golang."""
    _ = use_type_annotation
    return f'{arg_name} {arg_type.lang_type}'

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to Golang."""
    _ = use_type_annotation
    return return_type.lang_type


language.LanguageRegistry.register_language(
    language.Language(
        name='Go',
        file_ext='go',
        literal_translator_cls=GoLiteralTranslator,
        command_fn=make_commands,
        primitive_conversion_mapping={},
        prompt_translator_cls=GoPromptTranslator,
        naming_convention=utils.NamingConvention.CAMEL_CASE))
