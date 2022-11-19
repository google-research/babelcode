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

"""Haskell Specific Classes and Functions."""

import pathlib
from typing import Dict, List

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.languages import language

SchemaType = schema_parsing.SchemaType
SchemaMapType = schema_parsing.SchemaMapType


class HaskellLiteralTranslator(translation.LiteralTranslator):
  """The Haskell generator."""

  def format_list(self, generic_type: SchemaType,
                  list_values: List[str]) -> str:
    """Formats a list for Haskell."""
    _ = generic_type
    return f'[{", ".join(list_values)}]'

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]) -> str:
    """Formats a map for Haskell."""
    _ = key_type
    _ = value_type
    return f'Map.fromList [{", ".join(entries)}]'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a map entry for Haskell."""
    return f'({key}, {value})'

  def format_set(self, generic_type: SchemaType, set_values: List[str]) -> str:
    """Formats a set for Haskell."""
    _ = generic_type
    return f'Set.fromList [{", ".join(set_values)}]'


def make_commands(file_path: pathlib.Path) -> List[data_types.Command]:
  """Makes the command to run a Haskell source file.

  Args:
    file_path: The path to the file to run.

  Returns:
    The list of commands to run.
  """
  return [
      data_types.Command(['ghc', '-o', 'main.exe', file_path.name]),
      data_types.Command(['./main.exe'])
  ]


class HaskellPromptTranslator(translation.PromptTranslator):
  """The Haskell prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The Haskell prompt translator."""
    return {
        'list': ['vector', 'array'],
        'map': ['dict', 'dictionary', 'dictionaries'],
    }

  @property
  def signature_template(self) -> str:
    """The Haskell signature template."""
    return '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        '{{entry_fn_name}} :: {{signature}} -> {{return_type}}',
        '{{entry_fn_name}} {{params|join(" ")}} = '
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Cleans the docstring for Haskell."""
    return docstring.replace('--', '\\-\\-')

  def format_docstring_for_lang(self, docstring: str) -> str:
    """Formats a docstring for Haskell."""
    out = []
    for i, line in enumerate(docstring.splitlines(False)):
      if i == 0:
        prefix = '-- |'
      else:
        prefix = '--'
      out.append(f'{prefix} {line}')
    return '\n'.join(out)

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature return to Haskell."""
    _ = arg_name
    _ = use_type_annotation
    return f'{arg_type.lang_type}'

  def format_signature(self, signature_args: List[str]) -> str:
    """Formats the signature for Haskell."""
    return ' -> '.join(signature_args)

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to Haskell."""
    _ = use_type_annotation
    return return_type.lang_type

  def translate_argument_name_to_lang(self, arg_name: str) -> str:
    return utils.format_str_with_convention(utils.NamingConvention.SNAKE_CASE,
                                            arg_name)


language.LanguageRegistry.register_language(
    language.Language(
        name='Haskell',
        file_ext='hs',
        literal_translator_cls=HaskellLiteralTranslator,
        command_fn=make_commands,
        primitive_conversion_mapping={'boolean': str},
        prompt_translator_cls=HaskellPromptTranslator,
        naming_convention=utils.NamingConvention.CAMEL_CASE))
