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
"""Javascript Specific Classes and Functions."""

from typing import Dict, List

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.languages import language

SchemaType = schema_parsing.SchemaType


class JSLiteralTranslator(translation.LiteralTranslator):
  """The Javascript generator."""

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]) -> str:
    """Formats a map for Javascript."""
    _ = value_type
    _ = key_type
    return '{' + ', '.join(entries) + '}'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a map entry for Javascript."""
    return f'{key}: {value}'

  def format_set(self, generic_type: SchemaType, set_values: List[str]) -> str:
    """Formats a set for Javascript."""
    _ = generic_type
    return f'new Set([{", ".join(set_values)}])'


class JSPromptTranslator(translation.PromptTranslator):
  """The Javascript prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The Javascript words to replace."""
    return {
        'array': ['vector', 'list'],
        'map': ['dict', 'dictionary', 'dictionaries'],
    }

  @property
  def signature_template(self) -> str:
    """The Javascript signature template."""
    return '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        'function {{entry_fn_name}}({{signature}}) {'
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Translates a docstring for Javascript."""
    return translation.escape_cpp_like_comment_chars(docstring)

  def format_docstring_for_lang(self, docstring: str) -> str:
    """Formats a docstring for Javascript."""
    return translation.format_cpp_like_docstring(docstring)

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature argument to Javascript."""
    return arg_name

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to Javascript."""
    _ = use_type_annotation
    return f': {return_type.lang_type}'


language.LanguageRegistry.register_language(
    language.Language(
        name='Javascript',
        file_ext='js',
        literal_translator_cls=JSLiteralTranslator,
        command_fn=lambda fp: [data_types.Command(['node', fp.name])],
        primitive_conversion_mapping={},
        prompt_translator_cls=JSPromptTranslator,
        naming_convention=utils.NamingConvention.CAMEL_CASE))
