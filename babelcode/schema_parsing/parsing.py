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

"""Functions for parsing schemas."""
from typing import Dict, List, Tuple

from babelcode import data_types
from babelcode.schema_parsing import languages
from babelcode.schema_parsing import schema_type
from babelcode.schema_parsing import utils

SchemaType = schema_type.SchemaType
LanguageSchemaSpec = languages.LanguageSchemaSpec
SchemaMapType = utils.SchemaMapType


def parse_language_schema(
    language_spec: LanguageSchemaSpec, generic_schema: SchemaMapType
) -> SchemaMapType:
  """Parses the generic schema into a language specific one.

  Args:
    language_spec: The language specific schema specification.
    generic_schema: The mapping of argument name to the SchemaType object
      without the language type set.

  Raises:
    utils.SchemaTypeError: A SchemaType is not supported in the current language

  Returns:
    The mapping of argument name to the schema types, now with the language
    type set.
  """

  # Helper function for recursing.
  def convert_schema_type(s_type: SchemaType) -> SchemaType:
    if s_type.is_leaf():
      if s_type.type_str not in language_spec.primitive_lang_map:
        raise utils.SchemaTypeError(
            f'Leaf type "{s_type.type_str}" is not supported by'
            f' {language_spec.name}'
        )
      s_type.lang_type = language_spec.primitive_lang_map[s_type.type_str]

    else:
      s_type.elements = list(map(convert_schema_type, s_type.elements))

      if s_type.type_str in ['list', 'set']:
        if s_type.type_str == 'list':
          format_fn = language_spec.format_list_type
        else:
          format_fn = language_spec.format_set_type
        s_type.lang_type = format_fn(s_type.elements[0].lang_type)
      elif s_type.type_str == 'map':
        s_type.key_type = convert_schema_type(s_type.key_type)
        key_type = s_type.key_type.lang_type
        value_type = s_type.elements[0].lang_type
        s_type.lang_type = language_spec.format_map_type(key_type, value_type)
      else:
        raise utils.SchemaTypeError(
            f'{s_type} is not supported by {language_spec.name}'
        )
    return s_type

  for name in generic_schema:
    generic_schema[name] = convert_schema_type(generic_schema[name])

  return generic_schema


def parse_schema_and_input_order(
    language_spec: LanguageSchemaSpec, raw_schema: List[Dict[str, str]]
) -> Tuple[SchemaMapType, List[str]]:
  """Parses out the generic and the raw schema from a raw schema.

  Args:
    language_spec: The language schema spec to use.
    raw_schema: The raw schema.

  Returns:
    The schema and the input order.

  Raises:
    data_types.IOPairError: if there is an error with parsing the schema.
  """
  schema = {}
  param_ordering = []
  for var_dict in raw_schema['params']:
    name = var_dict['name']
    param_ordering.append(name)
    schema[name] = SchemaType.from_generic_type_string(var_dict['type'])
  schema[data_types.EXPECTED_KEY_NAME] = SchemaType.from_generic_type_string(
      raw_schema['return']['type']
  )
  schema = parse_language_schema(language_spec, schema)

  # Validate that the language schema has been updated to be correct, this
  # should never happen and we only check for this as a sanity check.
  missing_types = list(
      filter(lambda t: schema[t].lang_type == 'NOT_SET', schema)
  )
  if missing_types:
    raise data_types.IOPairError(
        f'{missing_types} are missing a language type.'
    )

  return schema, param_ordering
