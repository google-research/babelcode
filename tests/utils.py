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

"""Testing Utilities."""
import pathlib
from typing import Dict

from babelcode import code_generator
from babelcode import languages
from babelcode import schema_parsing
from babelcode import utils
import pytest  # pylint: disable=unused-import
import yaml

# Comment this out and replace with [LANG_NAME] to test a single language.
LANGS_TO_TEST = schema_parsing.LanguageSchemaSpecRegistry.list_languages()
# LANGS_TO_TEST = ['Python']

CODE_DIR = pathlib.Path(utils.FIXTURES_PATH, 'language_data')

# Define these shortcuts for ease of use.
DATA_STRUCTURES = [
    'TYPE_NAME_1[]',
    'list<list<TYPE_NAME_1>>',
    'map<TYPE_NAME_1;TYPE_NAME_1>',
    'set<TYPE_NAME_1>',
]


class LanguageSpec:
  """A testing specification for a language.

  This helper class defines the different testing specs for setting up
  automated testing for each language.

  Attributes:
    name: The name of the language.
    lang_dir: The directory where this languages specific features are stored.
    testing_spec: The testing specification of inputs and outputs.
    func_template_path: The path to the template function to use for testing.
  """

  def __init__(self, name: str):
    """Initializes the language spec.

    Args:
      name: The name of the language.
    """
    self.name = name
    self.lang_dir = CODE_DIR / self.name
    self.testing_spec = yaml.load(
        self.lang_dir.joinpath('spec.yaml').open(), yaml.Loader
    )
    self.func_template_path = self.lang_dir / 'func_template.txt'

  def __repr__(self) -> str:
    """Gets the name of the language."""
    return self.name

  def __getitem__(self, key: str) -> Dict[str, schema_parsing.SchemaValueType]:
    """Gets the testing specification for key."""
    return self.testing_spec[key]

  def get(
      self, key: str, default_value: schema_parsing.SchemaValueType
  ) -> schema_parsing.SchemaValueType:
    """Gets the testing specification for key and with value."""
    return self.testing_spec.get(key, default_value)

LANGUAGE_SPECS = {l: LanguageSpec(name=l) for l in LANGS_TO_TEST}


class BaseLanguageTestingClass:
  """Base class for language specific tests."""

  def _setup_test(self, lang_name):
    """Performs setup for the language test.

    Args:
      lang_name: The name of the language.
    """
    self.lang_spec = LANGUAGE_SPECS[lang_name]
    self.lang_name = lang_name
    try:
      self.lang = languages.LanguageRegistry.get_language(lang_name)
      self.literal_translator = self.lang.make_literal_translator()

    except:
      self.lang = None
      self.literal_translator = None
    try:
      self.template_map = code_generator.load_template_map(
          self.lang.make_template_map()
      )
    except:
      self.template_map = None
    self.schema_spec = schema_parsing.LanguageSchemaSpecRegistry.get_lang_spec(
        self.lang_name
    )

  def get_primitive_data(self, convert_type: str) -> Dict[str, str]:
    """Gets the primitive language specification for a generic."""
    return self.lang_spec['primitives'][convert_type]

  def parse_lang_schema(
      self, schema: schema_parsing.SchemaMapType
  ) -> schema_parsing.SchemaMapType:
    """Parses the language types from the schema."""
    return schema_parsing.parse_language_schema(self.schema_spec, schema)
