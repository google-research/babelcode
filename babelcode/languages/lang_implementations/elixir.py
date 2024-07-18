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
"""Elixir Specific Classes and Functions."""

from typing import Dict, List

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.languages import language

SchemaType = schema_parsing.SchemaType

class ElixirLiteralTranslator(translation.LiteralTranslator):
  """The Elixir generator."""

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]) -> str:
    """Formats a map for Elixir."""
    _ = value_type
    _ = key_type
    return '%{' + ', '.join(entries) + '}'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a map entry for Elixir."""
    return f'{key} => {value}'

  def format_set(self, generic_type: SchemaType, set_values: List[str]) -> str:
    """Formats a set for Elixir."""
    _ = generic_type
    return f'MapSet.new([{", ".join(set_values)}])'


class ElixirPromptTranslator(translation.PromptTranslator):
  """The Elixir prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The Elixir words to replace."""
    return {
        'list': ['vector', 'list'],
        'map': ['dict', 'dictionary', 'dictionaries'],
    }

  @property
  def signature_template(self) -> str:
    """The Elixir signature template."""
    return "defmodule {{entry_cls_name}} do\n" + '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        '  def {{entry_fn_name}}({{signature}}) do',
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Translates a docstring for Elixir."""
    return translation.escape_triple_quotes(docstring)

  def format_docstring_for_lang(self, docstring: str) -> str:
    """Formats a docstring for Elixir."""
    return f'"""\n{docstring}\n"""'

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature argument to Elixir."""
    return arg_name

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to Elixir."""
    _ = use_type_annotation
    return ''

language.LanguageRegistry.register_lanuage(
    language.Language(
        name='Elixir',
        file_ext='exs',
        literal_translator_cls=ElixirLiteralTranslator,
        command_fn=lambda fp: [data_types.Command(['elixir', fp.name])],
        primitive_conversion_mapping={},
        prompt_translator_cls=ElixirPromptTranslator,
        naming_convention=utils.NamingConvention.SNAKE_CASE))
