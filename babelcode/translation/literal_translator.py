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
"""Implementation of the base class for translating objects to literal code representation.
"""
import json
from typing import Any, Callable, Dict, List

from absl import logging

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import utils

SchemaType = schema_parsing.SchemaType
NamingConvention = utils.NamingConvention


class LiteralTranslator:
  """Base class for translating literals to specific languages."""

  def __init__(self, lang_name: str, naming_convention: utils.NamingConvention,
               convert_primitive_fn: Callable[[SchemaType, Any], str]):
    self.lang_name = lang_name
    self.naming_convention = naming_convention
    self.convert_primitive_fn = convert_primitive_fn

  def generate_test_case_literals(self, qid: str, io_pair: Dict[str, Any],
                                  underlying_schema: Dict[str, Any],
                                  input_order: List[str]) -> Dict[str, Any]:
    """Generates the code to initialize each argument and expected value for a test case.

    Args:
        qid: The question ID
        io_pair: The IO pair to generate for.
        underlying_schema: The parsed RAW schema to use.
        input_order: The ordering of the parameter input.

    Returns:
        A dictionary with the idx, inputs, and the expected literal.
    """

    def convert_with_exception_handling(arg_name, generic_type, value):
      try:
        return self.convert_var_to_literal(generic_type=generic_type,
                                           value=value)

      # We want to provide extra debugging info when there is an error raised
      # so that we can figure out what caused it.
      except Exception as e:
        logging.debug('Argument "%s" from %s had unexpected error %s', arg_name,
                      qid, e)
        logging.debug('IO Pair is %s', json.dumps(io_pair))
        logging.debug('Underlying schema is %s', underlying_schema)
        raise e

    input_literals = []
    for var in input_order:
      var_type = underlying_schema[var]
      var_value = schema_parsing.validate_correct_type(
          var_type, io_pair['inputs'].get(var))
      input_literals.append(
          convert_with_exception_handling(var, var_type, var_value))

    expected_literal = convert_with_exception_handling(
        data_types.EXPECTED_KEY_NAME,
        generic_type=underlying_schema[data_types.EXPECTED_KEY_NAME],
        value=io_pair['outputs'])

    return {
        'idx': io_pair['idx'],
        'inputs': input_literals,
        'outputs': expected_literal
    }

  ################################################################
  # Functions to that subclasses will likely need to override.   #
  ################################################################

  def format_list(self, generic_type: SchemaType,
                  list_values: List[Any]) -> str:
    """Formats the list of values to the code to initialize the list.

    Args:
      generic_type: The underlying schema type for the list.
      list_values: The list of strings that are the literal initialization code
        for each element of the list.

    Returns:
      The code to initialize a list object in the current language.
    """
    # Some languages require the generic_type to initialize the list.
    _ = generic_type

    return f'[{", ".join(list_values)}]'

  def format_set(self, generic_type: SchemaType, set_values: List[str]) -> str:
    """Formats the list of values to the code to initialize the set.

    Args:
      generic_type: The underlying schema type for the list.
      set_values: The list of strings that are the literal initialization code
        for each element of the set.

    Returns:
      The code to initialize a set object in the current language.
    """
    # Some languages require the generic_type to create the set.
    _ = generic_type
    return f'set([{", ".join(set_values)}])'

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]) -> str:
    """Formats the map with keys and entries to the code to initialize the map.

    We include the `key_type` and `value_type` for languages that require them
    to initialize the map(i.e. Golang).

    Args:
      key_type: The SchemaType of the key_type.
      value_type: The SchemaType of the value.
      entries: The list of code to initialize the entries.

    Returns:
      The code to initialize an map object in the current language.
    """
    # Some languages require either or both of the types for the keys and
    # values.
    _ = key_type
    _ = value_type
    return '{' + ', '.join(entries) + '}'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a single map entry to the literal code.

    Args:
      key: The code to initialize the key.
      value: The code to initialize the value.

    Returns:
      The code to make the single entry.
    """
    return f'{key}: {value}'

  ################################################################
  # Functions to convert values to their literal representation. #
  ################################################################

  def convert_var_to_literal(self, generic_type: SchemaType, value: Any) -> str:
    """Converts a variable to its literal string representation.

    Args:
        generic_type: The generic schema type of the variable.
        value: The value of the variable.

    Returns:
        The literal string in the respective language.

    Raises:
        IOPairError if the generic_type is not supported or the value
        is none and the type does not support it.
    """
    # If the type is a leaf type, then we convert directly to a literal.
    if (generic_type.type_str in schema_parsing.PRIMITIVE_TYPES
        or generic_type.is_leaf()):

      # Convert the value to null instead of empty.
      if schema_parsing.allows_null(generic_type.type_str) and not value:
        value = None

      return self.convert_primitive_fn(generic_type, value)

    if generic_type.type_str in ['list', 'set']:
      return self.convert_array_like_type(generic_type, value,
                                          generic_type.type_str == 'set')
    elif generic_type.type_str == 'map':
      return self.convert_map(generic_type, value)
    else:
      raise data_types.IOPairError(
          f'{generic_type} is not a supported type by {self.lang_name}')

  def convert_array_like_type(self, generic_type: SchemaType, nested_value: Any,
                              use_format_set: bool) -> str:
    """Converts a list to a string in a language.

    Args:
      generic_type: The underlying type of the object.
      nested_value: The nested object to convert.
      use_format_set: Use the format set method.

    Raises:
      data_types.QuestionValidationError: Error occurred in conversion
      data_types.IOPairError: Error with the IO pair.

    Returns:
        The nested object literal string.
    """
    format_fn = self.format_list
    target_type = 'list'
    if use_format_set:
      target_type = 'set'
      format_fn = self.format_set
      try:
        # Convert the list of values to a set to remove duplicates, then back
        # to list. We do the second conversion so we only need 1 function to
        # handle both types.
        nested_value = list(set(nested_value)) if nested_value else set()
      except TypeError as e:
        raise data_types.QuestionValidationError(
            'Could not convert nested values to set') from e

    def convert_nested(current_type, nested_list):

      if current_type.type_str != target_type:
        return self.convert_var_to_literal(current_type, nested_list)
      if not current_type.elements:
        raise data_types.IOPairError(
            f'{current_type} does not have child but {nested_list} is nested')
      out = []
      for v in nested_list:
        out.append(convert_nested(current_type.elements[0], v))

      return format_fn(current_type, out)

    if not nested_value:
      return format_fn(generic_type, [])

    return convert_nested(generic_type, nested_value)

  def convert_map(self, generic_type: SchemaType, map_value: Dict[Any,
                                                                  Any]) -> str:
    """Converts a dictionary to the language specific map code.

    Args:
        generic_type: The generic_type of the map.
        map_value: The raw dict value.

    Raises:
      data_types.IOPairError: Error with the IO pair.

    Returns:
      The string with the literal code.
    """

    # Format the empty dict value specifically
    if not map_value:
      return self.format_map(generic_type.key_type, generic_type.elements[0],
                             [])

    if not generic_type.elements:
      raise data_types.IOPairError(
          f'{generic_type} does not have type value but {map_value} is nested')

    if generic_type.key_type is None:
      raise data_types.IOPairError(
          f'{generic_type} does not have key_type value but {map_value} is nested'
      )
    entries = []
    for key_type, value in map_value.items():
      # Get the string values for the key_type and value to make the entry
      key_str = self.convert_var_to_literal(
          generic_type.key_type,  # type: ignore
          key_type)
      value_str = self.convert_var_to_literal(generic_type.elements[0], value)
      entries.append(self.format_map_entry(key_str, value_str))

    return self.format_map(generic_type.key_type, generic_type.elements[0],
                           entries)
