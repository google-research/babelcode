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
"""Lua Specific Classes and Functions."""
from typing import Dict, List

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.languages import language

SchemaType = schema_parsing.SchemaType
SchemaMapType = schema_parsing.SchemaMapType
SchemaValueType = schema_parsing.SchemaValueType


class LuaLiteralTranslator(translation.LiteralTranslator):
  """The Lua generator."""

  def format_list(self, generic_type: SchemaType,
                  list_values: List[str]) -> str:
    """Formats a list for Lua."""
    _ = generic_type
    return '{' + ', '.join(list_values) + '}'

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]) -> str:
    """Formats a map for Lua."""
    _ = key_type
    _ = value_type
    return '{' + ', '.join(entries) + '}'

  def format_map_entry(self, key_type: str, value: str) -> str:
    """Formats a map entry for Lua."""
    return f'[{key_type}]={value}'

  def format_set(self, generic_type: SchemaType, set_values: List[str]) -> str:
    """Formats a set for Lua."""
    _ = generic_type
    return '{' + ', '.join(map(lambda v: f'[{v}]=true', set_values)) + '}'


class LuaPromptTranslator(translation.PromptTranslator):
  """The Lua prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The Lua words to replace."""
    return {
        'array': ['vector', 'list'],
        'table': ['map', 'dict', 'dictionary', 'dictionaries'],
    }

  @property
  def signature_template(self) -> str:
    """The Lua signature template."""
    return '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        'function {{entry_fn_name}}({{signature}})'
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Cleans a docstring for Lua."""
    return docstring.replace('--', '\\-\\-')

  def format_docstring_for_lang(self, docstring: str) -> str:
    """Formats a docstring for Lua."""
    out = []
    for line in docstring.splitlines(False):
      out.append(f'-- {line}')
    return '\n'.join(out)

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature argument to Lua."""
    _ = arg_type
    _ = use_type_annotation
    return arg_name

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to Lua."""
    _ = use_type_annotation
    return return_type.lang_type


language.LanguageRegistry.register_language(
    language.Language(
        name='Lua',
        file_ext='lua',
        literal_translator_cls=LuaLiteralTranslator,
        command_fn=lambda fp: [data_types.Command(['lua', fp.name])],
        primitive_conversion_mapping={},
        prompt_translator_cls=LuaPromptTranslator,
        naming_convention=utils.NamingConvention.SNAKE_CASE))
