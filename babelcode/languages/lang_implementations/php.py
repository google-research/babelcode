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
"""PHP Specific Classes and Functions."""
import functools
from typing import Dict, List

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.languages import language

SchemaType = schema_parsing.SchemaType
SchemaMapType = schema_parsing.SchemaMapType
SchemaValueType = schema_parsing.SchemaValueType


class PHPLiteralTranslator(translation.LiteralTranslator):
  """The PHP generator."""

  def format_list(self, generic_type: SchemaType,
                  list_values: List[str]) -> str:
    _ = generic_type
    return f'array({", ".join(list_values)})'

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]):
    _ = key_type
    _ = value_type
    return f'array({", ".join(entries)})'

  def format_map_entry(self, key_type: str, value: str):
    return f'{key_type} => {value}'

  def format_set(self, generic_type: SchemaType, set_values: List[str]):
    _ = generic_type
    return 'array(' + ', '.join(map(lambda v: f'{v} => true', set_values)) + ')'


class PHPPromptTranslator(translation.PromptTranslator):
  """The PHP prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    return {
        'array': ['vector', 'list'],
        'array': ['map', 'dict', 'dictionary', 'dictionaries'],
    }

  @property
  def signature_template(self) -> str:
    return '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        'function {{entry_fn_name}}({{signature}}) {'
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    return translation.escape_cpp_like_comment_chars(docstring)

  def format_docstring_for_lang(self, docstring: str) -> str:
    out = ['/**']
    for line in docstring.splitlines(False):
      prefix = '* '
      out.append(f'{prefix}{line}')
    out.append('*/')
    return '\n'.join(out)

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    return f'${arg_name}'

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    _ = use_type_annotation
    return return_type.lang_type

  def translate_argument_name_to_lang(self, arg_name: str) -> str:
    return f'${arg_name}'


def convert_string(v, wrap_char='"'):
  v = translation.convert_string(v, wrap_char=wrap_char)
  return v.replace('$', '\\$')


convert_char = functools.partial(convert_string, wrap_char='\'')

language.LanguageRegistry.register_language(
    language.Language(
        name='PHP',
        file_ext='php',
        literal_translator_cls=PHPLiteralTranslator,
        command_fn=lambda fp: [data_types.Command(['php', fp.name])],
        primitive_conversion_mapping={},
        prompt_translator_cls=PHPPromptTranslator,
        naming_convention=utils.NamingConvention.CAMEL_CASE,
        escape_fn=lambda s: s.replace('$', '\\$')))
