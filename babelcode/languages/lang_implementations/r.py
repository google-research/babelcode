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
"""R Specific Classes and Functions."""
from typing import Dict, List

from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.data_types.command import Command
from babelcode.languages import language

SchemaMapType = schema_parsing.SchemaMapType
SchemaType = schema_parsing.SchemaType
SchemaValueType = schema_parsing.SchemaValueType


class RLiteralTranslator(translation.LiteralTranslator):
  """The R generator."""

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]) -> str:
    """Formats a map for R."""
    _ = key_type
    _ = value_type
    return 'list(' + ', '.join(entries) + ')'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a single entry for a map."""
    return f'{key} = {value}'

  def format_set(self, generic_type: SchemaType, set_values: List[str]):
    """Formats a set for R."""

    _ = generic_type
    return f'list({", ".join(set_values)})'

  def format_list(self, generic_type: SchemaType,
                  list_values: List[str]) -> str:
    """Formats a list for R."""
    _ = generic_type
    return f'list({", ".join(list_values)})'


class RPromptTranslator(translation.PromptTranslator):
  """The R prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The R words to replace."""
    return {
        'list': ['array'],
    }

  @property
  def signature_template(self) -> str:
    """The R signature template."""
    return '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        '{{entry_fn_name}} <- function({{signature}}) {',
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Translates a docstring for R."""
    return docstring

  def format_docstring_for_lang(self, docstring: str) -> str:
    """Formats a docstring for R."""
    return '\n'.join(map(lambda v: f'# {v}', docstring.splitlines(False)))

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature argument to R."""
    _ = use_type_annotation
    return arg_name

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to R."""
    _ = use_type_annotation
    return ''


language.LanguageRegistry.register_language(
    language.Language(
        name='R',
        file_ext='r',
        literal_translator_cls=RLiteralTranslator,
        command_fn=lambda fp: [Command(['Rscript', fp.name], timeout=10)],
        primitive_conversion_mapping={
            'boolean': lambda v: 'TRUE' if v else 'FALSE',
            'integer': lambda v: f'{v}L',
            'long': lambda v: f'{v}L'
        },
        prompt_translator_cls=RPromptTranslator,
        naming_convention=utils.NamingConvention.SNAKE_CASE,
    ))
