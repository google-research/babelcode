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
"""C# Specific Classes and Functions."""

import pathlib
from typing import Callable, Dict, List

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.languages import language

SchemaType = schema_parsing.SchemaType


class CSharpLiteralTranslator(translation.LiteralTranslator):
  """The C# generator."""

  def format_list(self, generic_type: SchemaType,
                  list_values: List[str]) -> str:
    """Convert the list of values to the code to initialize the list.

    Args:
      generic_type: The underlying schema type for the list.
      list_values: The list of code for each element.

    Returns:
      The code to initialize an array object in the current language.
    """
    return (f'new List<{generic_type.elements[0].lang_type}>' + '{' +
            ', '.join(list_values) + '}')

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]) -> str:
    """Format the map with keys and entries to the code to initialize the map.

    We include the `key_type` and `value_type` for languages that require them
    to initialize the map(i.e. Golang).

    Args:
      key_type: The SchemaType of the key_type.
      value_type: The SchemaType of the value.
      entries: The list of code to initialize the entries.

    Returns:
      The code to initialize an map object in the current language.
    """
    type_str = f'new Dictionary<{key_type.lang_type}, {value_type.lang_type}>'
    return type_str + '{' + ', '.join(entries) + '}'

  def format_map_entry(self, key: str, value: str) -> str:
    """Format a single map entry to the literal code.

    Args:
      key: The code to initialize the key_type.
      value: The code to initialize the value.

    Returns:
      The code to make the single entry.
    """
    return '{' + key + ', ' + value + '}'

  def format_set(self, generic_type: SchemaType, set_values: List[str]):
    return (f'new HashSet<{generic_type.elements[0].lang_type}>' + '{' +
            ', '.join(set_values) + '}')


def make_argument_signature(schema: Dict[str, SchemaType],
                            input_order: List[str]) -> str:
  """Make the argument signature for the language.

  Args:
    schema: The mapping of variables to their types.
    input_order: The order of variables for the arguments.

  Returns:
    The string argument signature for the language.
  """
  return ', '.join([f'{schema[v].lang_type} {v}' for v in input_order])


class CSharpPromptTranslator(translation.PromptTranslator):
  """The C# prompt translator."""

  def __init__(
      self,
      lang_name: str,
      naming_convention: utils.NamingConvention,
      escape_fn: Callable,
  ):
    _ = lang_name
    super().__init__('C#', naming_convention, escape_fn)

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    return {
        'list': ['array', 'vector'],
        'dictionary': ['map'],
    }

  @property
  def signature_template(self) -> str:
    return '\n'.join([
        'class {{entry_cls_name}} {',
        '{% if docstring is not none -%}{{docstring}}{%- endif %}',
        '    public {{return_type}} {{entry_fn_name}}({{signature}}) {',
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    return translation.escape_cpp_like_comment_chars(docstring)

  def format_docstring_for_lang(self, docstring: str) -> str:
    return '    ' + translation.format_cpp_like_docstring(docstring,
                                                          join_seq='\n    ')

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    _ = use_type_annotation
    return f'{arg_type.lang_type} {arg_name}'

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    _ = use_type_annotation
    return return_type.lang_type


def make_commands(file_path: pathlib.Path) -> List[data_types.Command]:
  """Makes the command to run a C# source file.

  Args:
    file_path: The path to the file to run.

  Returns:
    The list of commands to run.
  """

  return [
      data_types.Command(
          [
              'mono-csc',
              '-r:System.Web.dll',
              '-r:System.Web.Extensions.dll',
              file_path.name,
              '-o',
              'main.exe',
          ],
          timeout=10,
      ),
      data_types.Command(['mono', 'main.exe']),
  ]


language.LanguageRegistry.register_language(
    language.Language(
        name='CSharp',
        file_ext='cs',
        literal_translator_cls=CSharpLiteralTranslator,
        command_fn=make_commands,
        primitive_conversion_mapping={
            'float': lambda v: translation.convert_float(v, 'f'),
            'double': lambda v: translation.convert_float(v, 'm'),
        },
        prompt_translator_cls=CSharpPromptTranslator,
        naming_convention=utils.NamingConvention.PASCAL_CASE,
    ))
