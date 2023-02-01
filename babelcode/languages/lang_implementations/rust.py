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

"""Rust Specific Classes and Functions."""
import pathlib
from typing import Callable, Dict, List, Optional

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.languages import language

SchemaMapType = schema_parsing.SchemaMapType
SchemaType = schema_parsing.SchemaType
SchemaValueType = schema_parsing.SchemaValueType


class RustLiteralTranslator(translation.LiteralTranslator):
  """The Rust generator."""

  def format_list(self, generic_type: SchemaType,
                  list_values: List[str]) -> str:
    """Formats a list for Rust."""
    _ = generic_type
    return f'Vec::from([{", ".join(list_values)}])'

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]):
    """Formats a map for Rust."""
    _ = key_type
    _ = value_type
    entry_str = '[' + ', '.join(entries) + ']'
    return f'HashMap::from({entry_str})'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a map entry for Rust."""
    return f'({key}, {value})'

  def format_set(self, generic_type: SchemaType, set_values: List[str]) -> str:
    """Formats a set for Rust."""
    _ = generic_type
    return f'Vec::from([{", ".join(set_values)}]).into_iter().collect()'


def make_commands(file_path: pathlib.Path) -> List[data_types.Command]:
  """Makes the command to run a Rust source file.

  Args:
    file_path: The path to the file to run.

  Returns:
    The list of commands to run.
  """
  executable_name = f'./{file_path.stem}.exe'
  return [
      data_types.Command(['rustc', file_path.name, '-o', executable_name]),
      data_types.Command([executable_name])
  ]


def _convert_string(value: SchemaValueType,
                    wrap_char: str = '"',
                    escape_fn: Optional[Callable[[str], str]] = None) -> str:
  """Converts a string to Rust specific format."""
  value = translation.convert_string(value, wrap_char, escape_fn=escape_fn)
  return f'{value}.to_string()'


class RustPromptTranslator(translation.PromptTranslator):
  """The Rust prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The Rust words to replace."""
    return {
        'vector': ['vec', 'list'],
        'set': ['dict', 'dictionary', 'dictionaries'],
    }

  @property
  def signature_template(self) -> str:
    """The Rust signature template."""
    return '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        'pub fn {{entry_fn_name}}({{signature}}) -> {{return_type}} {'
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Cleans a docstring for Rust."""
    return docstring.replace('///', '\\/\\/\\/')

  def format_docstring_for_lang(self, docstring: str) -> str:
    """Formats a docstring for Rust."""
    out = []
    for l in docstring.splitlines():
      out.append(f'/// {l}')
    return '\n'.join(out)

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature argument to Rust."""
    _ = use_type_annotation
    return f'{arg_name}: {arg_type.lang_type}'

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to Rust."""
    _ = use_type_annotation
    return return_type.lang_type


language.LanguageRegistry.register_language(
    language.Language(
        name='Rust',
        file_ext='rs',
        literal_translator_cls=RustLiteralTranslator,
        command_fn=make_commands,
        primitive_conversion_mapping={'string': _convert_string},
        prompt_translator_cls=RustPromptTranslator,
        naming_convention=utils.NamingConvention.SNAKE_CASE))
