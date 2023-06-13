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
"""Implementation of the primitive translator functions."""

import functools
import logging
import re
from typing import Callable, Dict, Optional

from absl import logging

from babelcode import data_types
from babelcode import schema_parsing

SchemaType = schema_parsing.SchemaType
SchemaValueType = schema_parsing.SchemaValueType
ConvertFunctionType = Callable[[SchemaValueType], str]


def convert_string(value: SchemaValueType,
                   wrap_char: str = '"',
                   escape_fn: Optional[Callable[[str], str]] = None) -> str:
  """Converts a string to a language in a generic manner.

  This function is declared outside of the make_primitive_converter_func so that
  other language implementations can make use of it if they only need to make
  minor changes.

  Args:
      value: The value to convert.
      wrap_char: the char to wrap the result in.
      escape_fn: Callable that takes in a string and replaces language specific
        characters with "\\{CHARACTER}".

  Returns:
      The string code for the literal value of the value in a given
      language.
  """
  if value is not None:
    # Replace characters that could cause issues when generating the literal
    # tests.
    str_value = f'{repr(str(value))[1:-1]}'
  else:
    return f'{wrap_char}{wrap_char}'

  str_value = str_value.replace(wrap_char, '\\' + wrap_char)

  # Some languages (Go for example) do not natively support \' in strings, so
  # instead, replace those escaped characters with the unescaped version.
  if wrap_char == '"':
    str_value = str_value.replace('\\\'', '\'')
  else:
    str_value = str_value.replace('\\"', '"')
  if escape_fn is not None:
    str_value = escape_fn(str_value)

  return f'{wrap_char}{str_value}{wrap_char}'


def convert_float(value: SchemaValueType, suffix: str = '') -> str:
  """Converts a value to a float string with special handling of ints.

  Args:
      value (SchemaValueType): The value to convert.
      suffix: The suffix to add at the end of the converted float.

  Returns:
      The float as a string.
  """

  if isinstance(value, int):
    value = float(value)

  return f'{str(value)}{suffix}'


def make_primitive_translator(
    type_specific_overrides: Dict[str, ConvertFunctionType],  # pytype:ignore,
    escape_fn: Optional[Callable[[str], str]] = None  # pytype: ignore
) -> Callable[[SchemaType, SchemaValueType], str]:
  """Creates the callable that will serve as the primitive converter.

  Args:
      type_specific_overrides: Any overrides for a specific primitive type.
      escape_fn: The escape function to use for converting strings.

  Returns:
      Callable[[SchemaType, SchemaValueType], str]: The primitive converter
      callable to use.
  """
  logging.info('Making primitive translator...')
  if escape_fn is not None:
    logging.info('Escape function will be used.')
  else:
    logging.info('No escape function passed.')

  def generic_convert(value: SchemaValueType) -> str:
    """Generic conversion function to convert a value to the literal string.

    Args:
        value: The value to convert.

    Returns:
        The string code for the literal value of the value in a given
        language.
    """
    return str(value)

  convert_mapping = {}

  string_converter = functools.partial(convert_string, escape_fn=escape_fn)
  char_converter = functools.partial(convert_string,
                                     wrap_char='\'',
                                     escape_fn=escape_fn)
  special_default_conversions = {
      'string': string_converter,
      'character': char_converter,
      'boolean': lambda t: 'true' if t else 'false',
      'float': convert_float,
      'double': convert_float
  }
  for generic in schema_parsing.PRIMITIVE_TYPES:
    # Check if it is a generic
    if generic in type_specific_overrides:
      logging.info('Override found for "%s"', generic)
      convert_mapping[generic] = type_specific_overrides[generic]
    else:
      logging.info('Using default "%s" converter', generic)
      convert_mapping[generic] = special_default_conversions.get(
          generic, generic_convert)

  def primitive_converter(schema: SchemaType, value: SchemaValueType) -> str:
    if schema.type_str not in convert_mapping:
      raise data_types.IOPairError(
          f'{schema.type_str} is not a valid primitive')

    return convert_mapping[schema.type_str](value)

  return primitive_converter
