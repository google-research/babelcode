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
"""Python3 Specific Classes and Functions."""
from typing import Dict

from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.data_types.command import Command
from babelcode.languages import language

SchemaMapType = schema_parsing.SchemaMapType
SchemaType = schema_parsing.SchemaType
SchemaValueType = schema_parsing.SchemaValueType


class Py3LiteralTranslator(translation.LiteralTranslator):
  """The Python3 generator."""


class Py3PromptTranslator(translation.PromptTranslator):
  """The Python prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The Python words to replace."""
    return {
        'list': ['array', 'vector'],
        'dictionary': ['map'],
    }

  @property
  def signature_template(self) -> str:
    """The Python signature template."""
    return '\n'.join([
        'def {{entry_fn_name}}({{signature}}){{return_type}}:',
        '{%- if docstring is not none -%}{{"\n"~docstring}}{%- endif -%}'
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Translates a docstring for Python."""
    return translation.escape_triple_quotes(docstring)

  def format_docstring_for_lang(self, docstring: str) -> str:
    """Formats a docstring for Python."""
    out = []
    for i, line in enumerate(docstring.splitlines(False)):
      prefix = '    '
      if i == 0:
        prefix += '"""'
      out.append(f'{prefix}{line}')
    out.append('    """')
    return '\n'.join(out)

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature argument to Python."""
    if use_type_annotation:
      return f'{arg_name}: {arg_type.lang_type}'
    return arg_name

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to Python."""
    if use_type_annotation:
      return f' -> {return_type.lang_type}'
    return ''


language.LanguageRegistry.register_language(
    language.Language(
        name='Python',
        file_ext='py',
        literal_translator_cls=Py3LiteralTranslator,
        command_fn=lambda fp: [Command(['python', fp.name], timeout=10)],
        primitive_conversion_mapping={'boolean': str},
        prompt_translator_cls=Py3PromptTranslator,
        naming_convention=utils.NamingConvention.SNAKE_CASE))
