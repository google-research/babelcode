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

"""Java Specific Classes and Functions."""

from typing import Dict, List

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils
from babelcode.languages import language

SchemaType = schema_parsing.SchemaType


class JavaLiteralTranslator(translation.LiteralTranslator):
  """The Java generator."""

  def format_list(self, generic_type: SchemaType,
                  list_values: List[str]) -> str:
    """Formats a list for Java."""
    _ = generic_type
    return f'new ArrayList<>(Arrays.asList({", ".join(list_values)}))'

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]) -> str:
    """Formats a map for Java."""
    _ = key_type, value_type
    return f'Map.ofEntries({", ".join(entries)})'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a single entry for a map."""
    return f'entry({key}, {value})'

  def format_set(self, generic_type: SchemaType, set_values: List[str]):
    """Formats a set for Java."""
    _ = generic_type
    return f'new HashSet<>(Arrays.asList({", ".join(set_values)}))'


class JavaPromptTranslator(translation.PromptTranslator):
  """The Java prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The Java words to replace."""
    return {
        'array': ['vector', 'list'],
        'map': ['dict', 'dictionary', 'dictionaries'],
    }

  @property
  def signature_template(self) -> str:
    """The Java signature template."""
    return '\n'.join([
        'class {{entry_cls_name}} {',
        '{% if docstring is not none -%}{{docstring}}{%- endif %}',
        '    public {{return_type}} {{entry_fn_name}}({{signature}}) {'
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Cleans and translates a docstring for Java."""
    return translation.escape_cpp_like_comment_chars(docstring)

  def format_docstring_for_lang(self, docstring: str) -> str:
    """Formats a docstring for Java."""
    # Manually add in the tab for formatting.
    return '    ' + translation.format_cpp_like_docstring(
        docstring, join_seq='\n    ')

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature argument to Java."""
    _ = use_type_annotation
    return f'{arg_type.lang_type} {arg_name}'

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to Java."""
    _ = use_type_annotation
    return return_type.lang_type


language.LanguageRegistry.register_language(
    language.Language(
        name='Java',
        file_ext='java',
        literal_translator_cls=JavaLiteralTranslator,
        command_fn=lambda fp: [data_types.Command(['java', fp.name],timeout=15)],
        primitive_conversion_mapping={
            'float': lambda v: translation.convert_float(v, 'f'),
            'long': lambda v: f'{v}L'
        },
        prompt_translator_cls=JavaPromptTranslator,
        naming_convention=utils.NamingConvention.CAMEL_CASE))
