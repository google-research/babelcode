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

"""TypeScript Specific Classes and Functions."""
import pathlib
from typing import Dict, List

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.languages.language import Language
from babelcode.languages.language import LanguageRegistry

SchemaType = schema_parsing.SchemaType
SchemaValueType = schema_parsing.SchemaTypeError


class TSLiteralTranslator(translation.LiteralTranslator):
  """The TypeScript generator."""

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]) -> str:
    """Formats a map for TypeScript."""
    _ = key_type
    _ = value_type
    return '{' + ', '.join(entries) + '}'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a map entry for TypeScript."""
    return f'{key}: {value}'

  def format_set(self, generic_type: SchemaType, set_values: List[str]) -> str:
    """Formats a set for TypeScript."""
    type_str = generic_type.elements[0].lang_type
    return f'new Set<{type_str}>([{", ".join(set_values)}])'

  def format_list(self, generic_type: SchemaType,
                  list_values: List[SchemaValueType]) -> str:
    """Format an array or TypeScript."""
    _ = generic_type.elements[0].lang_type
    return f'[{", ".join(list_values)}]'


class TSPromptTranslator(translation.PromptTranslator):
  """The TypeScript prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    return {
        'array': ['vector', 'list'],
        'map': ['dict', 'dictionary', 'dictionaries'],
    }

  @property
  def signature_template(self) -> str:
    return '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        'function {{entry_fn_name}}({{signature}}){{return_type}} {'
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    return translation.escape_cpp_like_comment_chars(docstring)

  def format_docstring_for_lang(self, docstring: str) -> str:
    return translation.format_cpp_like_docstring(docstring)

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    _ = use_type_annotation
    return f'{arg_name}: {arg_type.lang_type}'

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    _ = use_type_annotation
    return f': {return_type.lang_type}'


def make_commands(file_path: pathlib.Path) -> List[data_types.Command]:
  """Makes the command to run a TypeScript source file.

  Args:
    file_path: The path to the file to run.

  Returns:
    The list of commands to run.
  """

  return [
      data_types.Command([
          'tsc', '--target', 'es2020', '--lib', 'es5,dom,es2015,es2020',
          file_path.name
      ],
                         timeout=15),
      data_types.Command(['node', f'{file_path.stem}.js'])
  ]


LanguageRegistry.register_language(
    Language(
        name='TypeScript',
        file_ext='ts',
        literal_translator_cls=TSLiteralTranslator,
        command_fn=make_commands,
        primitive_conversion_mapping={},
        prompt_translator_cls=TSPromptTranslator,
        naming_convention=utils.NamingConvention.CAMEL_CASE))
