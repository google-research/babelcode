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

"""C++ Specific classes and functions."""

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


def make_cpp_commands(file_path: pathlib.Path) -> List[data_types.Command]:
  """Makes the command to run a C++ source file.

  Args:
    file_path: The path to the file to run.

  Returns:
    The list of commands to run.
  """

  return [
      data_types.Command(['g++', file_path.name, '-o', 'main.exe'], timeout=10),
      data_types.Command(['./main.exe'])
  ]


class CPPLiteralTranslator(translation.LiteralTranslator):
  """The C++ generator."""

  def format_list(self, generic_type: SchemaType,
                  list_values: List[str]) -> str:
    """Formats a list for C++."""
    _ = generic_type
    return '{' + ', '.join(list_values) + '}'

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]):
    """Formats a map for C++."""
    _ = key_type
    _ = value_type
    return '{' + ', '.join(entries) + '}'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a map entry for C++."""
    return '{' + f'{key}, {value}' + '}'

  def format_set(self, generic_type: SchemaType, set_values: List[str]) -> str:
    """Formats a set for C++."""
    _ = generic_type
    return '{' + ', '.join(set_values) + '}'


class CPPPromptTranslator(translation.PromptTranslator):
  """The C++ prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The C++ words to replace."""
    return {
        'vector': ['array', 'list'],
        'map': ['dict', 'dictionary', 'dictionaries'],
    }

  @property
  def signature_template(self) -> str:
    """The C++ signature template."""
    return '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        '{{return_type}} {{entry_fn_name}}({{signature}}) {'
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Cleans a docstring for C++."""
    return translation.escape_cpp_like_comment_chars(docstring)

  def format_docstring_for_lang(self, docstring: str) -> str:
    """Formats a docstring for C++."""
    return translation.format_cpp_like_docstring(docstring)

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature argument to C++."""
    _ = use_type_annotation
    return f'{arg_type.lang_type} {arg_name}'

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to C++."""
    _ = use_type_annotation
    return return_type.lang_type


language.LanguageRegistry.register_language(
    language.Language(
        name='C++',
        file_ext='cpp',
        literal_translator_cls=CPPLiteralTranslator,
        command_fn=make_cpp_commands,
        primitive_conversion_mapping={},
        prompt_translator_cls=CPPPromptTranslator,
        naming_convention=utils.NamingConvention.CAMEL_CASE))
