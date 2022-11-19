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

"""Julia Specific Classes and Functions."""

import functools
from typing import Dict, List

from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.data_types.command import Command
from babelcode.languages import language

SchemaMapType = schema_parsing.SchemaMapType
SchemaType = schema_parsing.SchemaType
SchemaValueType = schema_parsing.SchemaValueType


class JuliaLiteralTranslator(translation.LiteralTranslator):
  """The Julia generator."""

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]) -> str:
    """Formats a map for Julia."""
    if not entries:
      return 'Dict{' + key_type.lang_type + ',' + value_type.lang_type + '}()'
    return f'Dict({"," .join(entries)})'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a single entry for a map."""
    return f'{key} => {value}'

  def format_set(self, generic_type: SchemaType, set_values: List[str]):
    """Formats a set for Julia."""
    if not set_values:
      return generic_type.lang_type + '()'

    return f'Set([{", ".join(set_values)}])'

  def format_list(self, generic_type: SchemaType,
                  list_values: List[str]) -> str:
    """Formats a list for Julia."""
    if not list_values:
      return f'{generic_type.lang_type}(undef,0)'
    return f'[{", ".join(list_values)}]'


class JuliaPromptTranslator(translation.PromptTranslator):
  """The Julia prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The Julia words to replace."""
    return {
        'vector': ['array', 'list'],
        'dictionary': ['map'],
    }

  @property
  def signature_template(self) -> str:
    """The Julia signature template."""
    return '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        'function {{entry_fn_name}}({{signature}}){{return_type}}',
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Cleans and translates a docstring for Julia."""
    return translation.escape_triple_quotes(docstring)

  def format_docstring_for_lang(self, docstring: str) -> str:
    """Formats a docstring for Julia."""
    return f'"""\n{docstring}\n"""'

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature argument to Julia."""
    if use_type_annotation:
      return f'{arg_name}::{arg_type.lang_type}'
    return arg_name

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to Julia."""
    if use_type_annotation:
      return f'::{return_type.lang_type}'
    return ''


language.LanguageRegistry.register_language(
    language.Language(
        name='Julia',
        file_ext='jl',
        literal_translator_cls=JuliaLiteralTranslator,
        command_fn=lambda fp: [Command(['julia', fp.name], timeout=10)],
        primitive_conversion_mapping={},
        prompt_translator_cls=JuliaPromptTranslator,
        naming_convention=utils.NamingConvention.SNAKE_CASE,
        escape_fn=lambda s: s.replace('$', '\\$')))
