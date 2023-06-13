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
"""Base implementations of language functionality."""
import dataclasses
import pathlib
from typing import Any, Callable, Dict, List, Optional

from absl import logging

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils

__all__ = ['Language', 'LanguageRegistry']
BASE_TEMPLATE_DIRECTORY = utils.PROJECT_ROOT.joinpath('templates')

SchemaType = schema_parsing.SchemaType
SchemaValueType = schema_parsing.SchemaValueType
SchemaMapType = schema_parsing.SchemaMapType
DEFAULT_TEMPLATES = {
    'MAIN': 'main.txt',
    'EVALUATION': 'evaluation.txt',
    'HEADER': 'header.txt'
}


@dataclasses.dataclass(frozen=True)
class Language:
  """The base language class.

  Attributes:
    name: The name of the language.
    file_ext: The string file extension used by this language.
    template_mapping: The mapping of template names to their file name. This
      MUST have a'MAIN' entry.
    literal_translator_cls: The LiteralTranslator class for this language.
    command_fn: The callable that takes in a filepath and returns the list of
      string commands to run for this language.
    primitive_conversion_mapping: The overwrites needed for language specific
      primitive to code conversions. If you add an override to the map, then the
      value must be a callable that takes in a schema type and corresponding
      value, then returns the language specific code to convert it to the
      literal code.
    prompt_translator_cls: The prompt translator class for this language.
    naming_convention: The naming convention to use for this language.
    escape_fn: Callable that takes in a string and replaces language specific
      characters with their escaped versions.
  """
  name: str
  file_ext: str
  literal_translator_cls: translation.LiteralTranslator
  command_fn: Callable[[pathlib.Path], List[data_types.Command]]
  primitive_conversion_mapping: Dict[str, Callable[[SchemaValueType], str]]
  prompt_translator_cls: translation.PromptTranslator
  naming_convention: utils.NamingConvention = utils.NamingConvention.SNAKE_CASE
  template_mapping: Dict[str, str] = dataclasses.field(default_factory=dict)
  escape_fn: Optional[Callable[[str], str]] = None

  def __post_init__(self):
    """Adds default templates to the template mapping if they do not exist."""
    for k, v in DEFAULT_TEMPLATES.items():
      if k not in self.template_mapping:
        self.template_mapping[k] = v

  def __str__(self) -> str:
    """String representation of the language."""
    return self.name

  def make_primitive_translator(self) -> Callable[[SchemaType, Any], str]:
    """Initializes and returns the primitive translator function."""
    logging.info('Making primitive translator for %s', self.name)
    return translation.make_primitive_translator(
        type_specific_overrides=self.primitive_conversion_mapping,
        escape_fn=self.escape_fn)

  def make_literal_translator(self) -> translation.LiteralTranslator:
    """Initializes and returns the literal translator class."""
    logging.info('Making literal translator for %s', self.name)
    return self.literal_translator_cls(
        lang_name=self.name,
        naming_convention=self.naming_convention,
        convert_primitive_fn=self.make_primitive_translator())

  def make_template_map(self) -> Dict[str, pathlib.Path]:
    """Returns the template mapping with the full paths."""
    logging.info('Making template map for %s', self.name)
    lang_template_dir = BASE_TEMPLATE_DIRECTORY.joinpath(self.name)
    out = {}
    for name, fn in self.template_mapping.items():
      out[name] = lang_template_dir.joinpath(fn)
    return out

  def make_prompt_translator(self) -> translation.PromptTranslator:
    """Initializes the prompt translator class."""
    logging.info('Making prompt translator for %s', self.name)
    return self.prompt_translator_cls(self.name, self.naming_convention,
                                      self.escape_fn)


class LanguageRegistry:
  """Language registry for mapping language names to their objects."""
  _REGISTRY = {}
  _FILE_EXT_TO_LANG = {}

  @classmethod
  def register_language(cls, language: Language) -> None:
    """Registers a language under the language's name."""
    cls._REGISTRY[language.name] = language
    cls._FILE_EXT_TO_LANG[language.file_ext] = language.name

  @classmethod
  def get_language(cls, language: str) -> Language:
    """Gets the language from a name."""
    return cls._REGISTRY[language]

  @classmethod
  def list_languages(cls) -> List[str]:
    """Lists the registered languages."""
    return list(cls._REGISTRY)

  @classmethod
  def get_lang_from_ext(cls, file_ext: str) -> Language:
    """Gets the language based on the file extension."""
    return cls._REGISTRY[cls._FILE_EXT_TO_LANG[file_ext]]
