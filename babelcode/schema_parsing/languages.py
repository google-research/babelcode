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

"""Implementations for each language's schema specification."""

import dataclasses
from typing import Callable, Dict, List
from babelcode.schema_parsing import utils


@dataclasses.dataclass
class LanguageSchemaSpec:
  """Specification for a language specific schema.

  Attributes:
    name: Name to register this spec under.
    primitive_lang_map: The dictionary mapping the primitive types defined in
      the `schema_parsing.py` file to the corresponding type in the current
      language.
    format_list_type: A callable that takes in a single string that represents
      the type of the elements of the list. Returns the list type string for a
      list with the element types.
    format_map_type: A callable that takes in `key_type` and `value_type`
      strings and returns the language type for a map.
    format_set_type: A callable that takes in a single string that represents
      the type of the elements of the set. Returns the set type string for a
      list with the element types.
  """

  name: str
  primitive_lang_map: Dict[str, str]
  format_list_type: Callable[[str], str]
  format_map_type: Callable[[str, str], str]
  format_set_type: Callable[[str], str]


class LanguageSchemaSpecRegistry:
  """The registry of language specifications."""

  _REGISTRY = {}

  @classmethod
  def register_language(
      cls, language_spec: LanguageSchemaSpec, allow_overwrite: bool = False
  ):
    """Registers a language specification.

    Args:
      language_spec: The language specification to register.
      allow_overwrite: Allow overwriting existing registered.

    Raises:
      KeyError: The language specification is already registered.
    """
    if language_spec.name in cls._REGISTRY and not allow_overwrite:
      raise KeyError(f'{language_spec.name} already registered')
    cls._REGISTRY[language_spec.name] = language_spec

  @classmethod
  def get_lang_spec(cls, language: str) -> LanguageSchemaSpec:
    """Gets the language specification."""
    return cls._REGISTRY[language]

  @classmethod
  def list_languages(cls) -> List[str]:
    """Lists the registered languages."""
    return list(cls._REGISTRY)


################################################################
# Language Schema Spec methods.                                #
################################################################
def make_cpp_spec() -> LanguageSchemaSpec:
  """Makes the C++ schema spec."""

  primitive_map = {
      'boolean': 'bool',
      'integer': 'int',
      'character': 'char',
      'float': 'float',
      'double': 'double',
      'long': 'long long',
      'string': 'string',
  }
  return LanguageSchemaSpec(
      name='C++',
      primitive_lang_map=primitive_map,
      format_list_type=lambda t: f'vector<{t}>',
      format_map_type=lambda k, v: f'map<{k},{v}>',
      format_set_type=lambda t: f'set<{t}>',
  )


def make_go_spec() -> LanguageSchemaSpec:
  """Makes golang spec."""
  primitive_map = {
      'boolean': 'bool',
      'integer': 'int',
      'character': 'char',
      'float': 'float64',
      'double': 'float64',
      'long': 'int64',
      'string': 'string',
  }
  return LanguageSchemaSpec(
      name='Go',
      primitive_lang_map=primitive_map,
      format_list_type=lambda t: f'[]{t}',
      format_map_type=lambda k, v: f'map[{k}]{v}',
      format_set_type=lambda t: f'map[{t}]bool',
  )


def make_java_spec() -> LanguageSchemaSpec:
  """Makes java spec."""
  primitive_map = {
      'boolean': 'Boolean',
      'integer': 'Integer',
      'character': 'Character',
      'float': 'Float',
      'double': 'Double',
      'long': 'Long',
      'string': 'String',
  }
  return LanguageSchemaSpec(
      name='Java',
      primitive_lang_map=primitive_map,
      format_list_type=lambda t: f'ArrayList<{t}>',
      format_map_type=lambda k, v: f'Map<{k}, {v}>',
      format_set_type=lambda t: f'HashSet<{t}>',
  )


def make_js_spec() -> LanguageSchemaSpec:
  """Makes js spec."""
  primitive_map = {
      'boolean': 'Boolean',
      'integer': 'Number',
      'character': 'String',
      'float': 'Number',
      'double': 'Number',
      'long': 'Number',
      'string': 'String',
  }
  return LanguageSchemaSpec(
      name='Javascript',
      primitive_lang_map=primitive_map,
      format_list_type=lambda _: 'Array',
      format_map_type=lambda *_: 'Map',
      format_set_type=lambda _: 'Set',
  )


def make_julia_spec() -> LanguageSchemaSpec:
  """Makes Julia spec."""
  primitive_map = {
      'boolean': 'Bool',
      'integer': 'Int64',
      'character': 'Char',
      'float': 'Float64',
      'double': 'Float64',
      'long': 'Int64',
      'string': 'String',
  }
  return LanguageSchemaSpec(
      name='Julia',
      primitive_lang_map=primitive_map,
      format_list_type=lambda t: 'Vector{' + t + '}',
      format_map_type=lambda k, v: 'Dict{' + k + ', ' + v + '}',
      format_set_type=lambda t: 'Set{' + t + '}',
)


def make_kotlin_spec() -> LanguageSchemaSpec:
  """Makes Kotlin spec."""
  primitive_map = {
      'boolean': 'Boolean',
      'integer': 'Int',
      'character': 'Char',
      'float': 'Float',
      'double': 'Double',
      'long': 'Long',
      'string': 'String',
  }
  return LanguageSchemaSpec(
      name='Kotlin',
      primitive_lang_map=primitive_map,
      format_list_type=lambda t: f'ArrayList<{t}>',
      format_map_type=lambda k, v: f'Map<{k}, {v}>',
      format_set_type=lambda t: f'MutableSet<{t}>',
  )


def make_lua_spec() -> LanguageSchemaSpec:
  """Makes the lua spec."""
  primitive_map = {
      'boolean': 'boolean',
      'integer': 'number',
      'character': 'string',
      'float': 'number',
      'double': 'number',
      'long': 'number',
      'string': 'string',
  }
  return LanguageSchemaSpec(
      name='Lua',
      primitive_lang_map=primitive_map,
      format_list_type=lambda _: 'array',
      format_map_type=lambda *_: 'table',
      format_set_type=lambda _: 'table',
  )


def make_php_spec() -> LanguageSchemaSpec:
  """Makes the PHP spec."""
  primitive_map = {
      'boolean': 'boolean',
      'integer': 'number',
      'character': 'string',
      'float': 'number',
      'double': 'number',
      'long': 'number',
      'string': 'string',
  }
  return LanguageSchemaSpec(
      name='PHP',
      primitive_lang_map=primitive_map,
      format_list_type=lambda _: 'array',
      format_map_type=lambda *_: 'array',
      format_set_type=lambda _: 'array',
  )


def make_python_spec() -> LanguageSchemaSpec:
  """Make the python spec."""
  primitive_map = {
      'boolean': 'bool',
      'integer': 'int',
      'character': 'str',
      'float': 'float',
      'double': 'float',
      'long': 'int',
      'string': 'str',
  }
  return LanguageSchemaSpec(
      name='Python',
      primitive_lang_map=primitive_map,
      format_list_type=lambda t: f'List[{t}]',
      format_map_type=lambda k, v: f'Dict[{k}, {v}]',
      format_set_type=lambda t: f'Set[{t}]',
  )


def make_rust_spec() -> LanguageSchemaSpec:
  """Makes the rust spec."""
  primitive_map = {
      'boolean': 'bool',
      'integer': 'i32',
      'character': 'char',
      'float': 'f32',
      'double': 'f64',
      'long': 'i64',
      'string': 'String',
  }
  return LanguageSchemaSpec(
      name='Rust',
      primitive_lang_map=primitive_map,
      format_list_type=lambda t: f'Vec<{t}>',
      format_map_type=lambda k, v: f'HashMap<{k}, {v}>',
      format_set_type=lambda t: f'HashSet<{t}>',
  )


def make_haskell_spec() -> LanguageSchemaSpec:
  """Makes the haskell spec."""
  primitive_map = {
      'boolean': 'Bool',
      'integer': 'Integer',
      'character': 'Char',
      'float': 'Double',
      'double': 'Double',
      'long': 'Integer',
      'string': 'String',
  }
  return LanguageSchemaSpec(
      name='Haskell',
      primitive_lang_map=primitive_map,
      format_list_type=lambda t: f'[{t}]',
      format_map_type=lambda k, v: f'Map.Map {k} {v}',
      format_set_type=lambda t: f'Set.Set {t}',
  )


def make_csharp_spec() -> LanguageSchemaSpec:
  """Makes C# spec."""
  primitive_map = {
      'boolean': 'bool',
      'integer': 'int',
      'character': 'char',
      'float': 'float',
      'double': 'decimal',
      'long': 'long',
      'string': 'string',
  }
  return LanguageSchemaSpec(
      name='CSharp',
      primitive_lang_map=primitive_map,
      format_list_type=lambda t: f'List<{t}>',
      format_map_type=lambda k, v: f'Dictionary<{k}, {v}>',
      format_set_type=lambda t: f'HashSet<{t}>',
  )


def make_typescript_spec() -> LanguageSchemaSpec:
  """Makes Typescript spec."""
  primitive_map = {
      'boolean': 'boolean',
      'integer': 'number',
      'character': 'string',
      'float': 'number',
      'double': 'number',
      'long': 'number',
      'string': 'string',
  }
  return LanguageSchemaSpec(
      name='TypeScript',
      primitive_lang_map=primitive_map,
      format_list_type=lambda k: f'Array<{k}>',
      format_map_type=lambda k, v: f'Record<{k},{v}>',
      format_set_type=lambda v: f'Set<{v}>',
  )


def make_scala_spec() -> LanguageSchemaSpec:
  """Makes Scala spec."""
  primitive_map = {
      'boolean': 'Boolean',
      'integer': 'Int',
      'character': 'Char',
      'float': 'Float',
      'double': 'Double',
      'long': 'Long',
      'string': 'String',
  }
  return LanguageSchemaSpec(
      name='Scala',
      primitive_lang_map=primitive_map,
      format_list_type=lambda k: f'List[{k}]',
      format_map_type=lambda k, v: f'HashMap[{k}, {v}]',
      format_set_type=lambda v: f'HashSet[{v}]',
  )


def make_r_spec() -> LanguageSchemaSpec:
  """Makes R spec."""
  primitive_map = {
      'boolean': 'logical',
      'integer': 'integer',
      'character': 'character',
      'float': 'numeric',
      'double': 'numeric',
      'long': 'integer',
      'string': 'character',
  }

  def convert_map(key, value):
    """R Does not allow integer keys."""
    if key == 'integer':
      raise utils.SchemaTypeError('R does not support integer key values.')
    return f'list[{key}, {value}]'

  return LanguageSchemaSpec(
      name='R',
      primitive_lang_map=primitive_map,
      format_list_type=lambda k: f'list[{k}]',
      format_map_type=convert_map,
      format_set_type=lambda v: f'list[{v}]',
  )


def make_dart_spec() -> LanguageSchemaSpec:
  """Makes dart spec."""
  primitive_map = {
      'boolean': 'bool',
      'integer': 'int',
      'character': 'String',
      'float': 'double',
      'double': 'double',
      'long': 'int',
      'string': 'String',
  }
  return LanguageSchemaSpec(
      name='Dart',
      primitive_lang_map=primitive_map,
      format_list_type=lambda k: f'List<{k}>',
      format_map_type=lambda k, v: f'Map<{k}, {v}>',
      format_set_type=lambda v: f'Set<{v}>',
  )
