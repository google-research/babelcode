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

"""Classes and Functions for SchemaTypes."""
import dataclasses
import json
from typing import List, Optional, Sequence

from absl import logging

from babelcode.schema_parsing import utils


def _split_tuple_children(child_type_str: str) -> List[str]:
  """Helper function to split the children elements for a tuple.


  Args:
      child_type_str: The generic children string. From a generic tuple string,
        this is `tuple<CHILDREN TYPE STRING>`. Each child element is split by
        `|`.

  Raises:
    utils.SchemaTypeError: If the schema type is malformed.

  Returns:
      The list of unparsed generic type strings for each child element of a
      tuple. This helper function does not convert these generic type strings
      into `SchemaType` objects, only tokenizes the inputed child type
      string.
  """
  out = []
  current_element_characters = []
  # Counter for the number of open '<' characters
  num_open = 0
  for character in child_type_str:

    if character == '|' and num_open == 0:
      out.append(''.join(current_element_characters))
      current_element_characters = []

    else:
      if character == '<':
        num_open += 1
      elif character == '>':
        num_open -= 1
        if num_open < 0:
          raise utils.SchemaTypeError(
              f'{child_type_str} has uneven ">" characters')
      current_element_characters.append(character)
  if num_open != 0:
    raise utils.SchemaTypeError(f'{child_type_str} has uneven ">" characters')
  if current_element_characters:
    out.append(''.join(current_element_characters))
  return out


@dataclasses.dataclass
class SchemaType:
  """Generic representation of a type either used in the arguments or returns of a question.

  For every question, the solution must have both inputs and an output. To
  enable translation of these test cases to multiple languages, we need a
  generic representation. The `SchemaType` class fufills this need. A generic
  type string can either be a leaf (i.e. int, str) or have 'children'
  elements (i.e. list of lists, map). A types children are contained wrapped
  with `<>`. For the a `map`, the format of the generic type string is
  `map<TYPE OF KEYS;TYPE OF VALUES>. As `tuple` can have multiple types for
  its children, the format of the generic type string is
  `tuple<TYPE OF ELEMENT 1, TYPE OF ELEMENT 2...>`. `list` and `set` both
  follow the grammar of `TYPE NAME<TYPE OF ELEMENTS>`.

  Attributes:
    type_str: The generic string representing the type of this node.
    lang_type: The language specific type string.
    elements: The types of the children elements for all data structure types.
    key_type: The type of the key values for a map. Only map types are allowed
      to have this value.
  """
  type_str: str
  lang_type: str = 'NOT_SET'
  elements: List['SchemaType'] = dataclasses.field(default_factory=list)
  key_type: Optional['SchemaType'] = None

  def __post_init__(self):
    """Performs simple validation after the class is initialized."""
    if self.key_type is not None and not self.elements:
      raise utils.SchemaTypeError('key_type is set without a value_type')

    if self.type_str in utils.PRIMITIVE_DATA_STRUCTURES and not self.elements:
      logging.error('Data structure type "%s" does not have proper values',
                    self.type_str)
      raise utils.SchemaTypeError('data structure type must have a value')

  def is_leaf(self) -> bool:
    """Is the type a leaf.

    Returns:
        bool: True if there are no children elements. Else False.
    """
    # Using bool(self.elements) does not work and only explicitly checking
    # length is 0 works.
    return len(self.elements) == 0  # pylint: disable=g-explicit-length-test

  @classmethod
  def from_generic_type_string(cls, type_str: str) -> 'SchemaType':
    """Converts a generic type string to a SchemaType.

    Args:
      type_str: The generic type string

    Raises:
      utils.SchemaTypeError: If there is a grammar error with the schema type
      string.
      ValueError: If an unexpected error occurs.

    Returns:
      The parsed SchemaType Object.
    """

    open_count = type_str.count('<')
    if open_count != type_str.count('>'):
      raise utils.SchemaTypeError(
          f'"{type_str}" does not have same number of <>')
    if '[]' in type_str:
      if open_count != 0:
        raise utils.SchemaTypeError(f'"{type_str}" has both [] and <>')

      return cls(type_str='list',
                 elements=[
                     cls.from_generic_type_string(type_str.replace('[]', '', 1))
                 ])

    if open_count == 0:
      out = cls(type_str=type_str)
      if not out.is_leaf():
        raise ValueError(f'{out} had an error')
      return out

    # We are looking for the format TYPE_NAME<...>, split on first < then
    # rejoin and remove the last > character.
    type_name, *children_types = type_str.split('<')
    children_types = '<'.join(children_types)
    if children_types[-1] != '>':
      raise utils.SchemaTypeError(f'{children_types} has extra after last >')
    children_types = children_types[:-1]

    # If it is a map, it must have key and value types.
    if type_name == 'map':
      try:
        key_value, value = children_types.split(';', 1)
      except ValueError as e:
        raise utils.SchemaTypeError(
            f'Expected map to be in the form map<TYPE_1;TYPE_2>, but got {type_str}'
        ) from e
      return cls(type_str=type_name,
                 key_type=cls.from_generic_type_string(key_value),
                 elements=[cls.from_generic_type_string(value)])

    # Tuples must be handled by themselves as they can have multiple children
    # types (and even more nested types). Therefore we must handle them
    # separately than other default data types.
    elif type_name == 'tuple':
      # Split the children types by |
      all_children = _split_tuple_children(children_types)
      logging.debug('Found "tuple" in string "%s" with children=%s', type_str,
                    all_children)
      # If all of the tuple elements are of the same type, convert them to a
      # list of one type to support more languages.
      if len(set(all_children)) == 1:
        logging.debug('Children are of same type, converting to list.')
        return cls(type_str='list',
                   elements=[cls.from_generic_type_string(all_children[0])])

      return cls(type_str=type_name,
                 elements=list(map(cls.from_generic_type_string, all_children)))

    # If not a special type, make the type from the children types string.
    else:
      return cls(type_str=type_name,
                 elements=[cls.from_generic_type_string(children_types)])

  def to_generic(self) -> str:
    """Converts the SchemaType to a generic string."""
    generic_elements = [e.to_generic() for e in self.elements]
    if self.type_str in ['list', 'tuple', 'set']:
      delim = '|' if self.type_str == 'tuple' else ','
      return f'{self.type_str}<{delim.join(generic_elements)}>'
    elif self.type_str == 'map':
      return f'map<{self.key_type.to_generic()};{generic_elements[0]}>'
    else:
      return self.type_str

  @classmethod
  def copy(cls, original: 'SchemaType') -> 'SchemaType':
    """Copy a SchemaType.

    Args:
      original: The original type to copy.

    Returns:
      The copy of the original.
    """

    new_elts = [SchemaType.copy(elt) for elt in original.elements]
    if original.key_type is not None:
      new_key = SchemaType.copy(original.key_type)
    else:
      new_key = None
    return cls(original.type_str,
               original.lang_type,
               elements=new_elts,
               key_type=new_key)

  @property
  def depth(self) -> int:
    """Maximum depth for the type."""
    if self.is_leaf():
      return 0

    max_depth_of_subtree = 0
    for v in self.elements:
      max_depth_of_subtree = max(max_depth_of_subtree, v.depth)

    # Add 1 as this node must have descendants.
    return max_depth_of_subtree + 1

  def pprint(self) -> str:
    return json.dumps(dataclasses.asdict(self), indent=True)


def validate_correct_type(
    schema_type: SchemaType,
    value: utils.SchemaValueType,
    chain: Optional[List[str]] = None) -> utils.SchemaValueType:
  """Validates that a value has the correct underlying value from the schema.

  Args:
      schema_type: The type to validate against.
      value: The value to test against.
      chain: The chain calling this, for debugging. Defaults to None.

  Raises:
      utils.SchemaTypeError: The value is not valid for the given type.

  Returns:
    The value with the correct type.
  """

  def check_iterable_only_has_single_type(
      value: Sequence[utils.SchemaValueType]):
    if len(set(type(v).__name__ for v in value)) > 1:
      raise utils.SchemaTypeError(
          f'{schema_type.type_str} does not support multiple element types.')

  chain = chain or []

  expected_type = utils.GENERIC_TO_PYTHON_TYPE.get(schema_type.type_str, None)
  if expected_type is None:
    raise utils.SchemaTypeError(f'Unknown type {schema_type.type_str}')

  # Some types (i.e. integer, float) do not support having null values in some
  # languages. To standardize across all languages, we explicitly do not allow
  # these cases to be None.
  type_allows_null = utils.allows_null(schema_type.type_str)
  if not type_allows_null and value is None:
    logging.info('Got %s from %s', type(value).__name__, value)
    logging.info('Chain is %s', chain)
    raise utils.SchemaTypeError(f'{schema_type.type_str} does not support null')
  # If the type allows null values, and the value is None, set to the empty
  # type for simplified type validation.
  elif value is None and type_allows_null:
    value = expected_type()

  if not isinstance(value, expected_type):
    # For later translation, we need to ensure that the value is a pure float
    # so we convert it to a float.
    if expected_type == float and isinstance(value, int):
      value = float(value)
    else:
      logging.info('Found has mismatched types')
      logging.info('Expected %s', schema_type)
      logging.info('Got %s from %s', expected_type.__name__, value)
      logging.info('Chain is %s', chain)
      raise utils.SchemaTypeError(
          f'Value is not of type {expected_type.__name__}')

  if schema_type.type_str in ['list', 'set']:
    # Sets and lists are represented internally as a list due to JSON.
    new_values = []
    for v in value:
      new_values.append(
          validate_correct_type(schema_type.elements[0], v,
                                [*chain, schema_type.type_str]))

    value = new_values
    check_iterable_only_has_single_type(value)

  elif schema_type.type_str == 'map':

    # Make sure the values in the map are the correct types.
    for k, v in value.items():
      value[k] = validate_correct_type(schema_type.elements[0], v,
                                       [*chain, schema_type.type_str])

    # Because the question data is parsed from a raw json line, it needs to
    # conform to json standards and thus, keys cannot be ints. Therefore, all
    # we do in this section is that we check that the keys are strings and that,
    # if the expected type is an int, that it can be converted to an int.
    new_key_map = {}
    expected_key_type = utils.GENERIC_TO_PYTHON_TYPE[
        schema_type.key_type.type_str]
    for k in value.keys():
      if not isinstance(k, (str, int)):
        logging.error('Chain is %s', ', '.join(chain))
        logging.error('Raw value is %s', k)
        raise utils.SchemaTypeError('Raw key is not a string or int')

      if expected_key_type == int:
        # Make sure it can be cast to int
        try:
          new_key = int(k)
        except ValueError as e:

          logging.error('Chain is %s', ', '.join(chain))
          logging.error('Raw value is %s', k)
          raise utils.SchemaTypeError(
              'Key is expected to be an int, but could not convert the string to int.'
          ) from e
      else:
        # Not an int, so no need to worry about casting.
        new_key = str(k)

      # Check for duplicate keys after the type conversion.
      if new_key in new_key_map:
        raise utils.SchemaTypeError(f'Duplicate key {new_key} found in value')
      new_key_map[new_key] = k

    # Go through and update the keys.
    for new_key, old_key in new_key_map.items():
      value[new_key] = value.pop(old_key)

    check_iterable_only_has_single_type(list(value.values()))
    check_iterable_only_has_single_type(list(value.keys()))

  return value


def is_generic_equal(left: SchemaType, right: SchemaType) -> bool:
  """Check if the generic schemas are equal.

  For two types to be "generically" equal, they must have the same subtree
  string OR either is a leaf node with null as the generic type.

  Args:
    left: left hand schema type
    right: right hand schema type

  Returns:
      True if they are generically equal, otherwise false.
  """

  # Either is a leaf, then only way still equal is if type_str is 'null'
  if left.is_leaf() or right.is_leaf():
    if left.type_str == 'null' or right.type_str == 'null':
      return True
    return left.type_str == right.type_str

  if left.type_str != right.type_str:
    return False

  if left.type_str == 'map':
    # If either key is None, then it does mean there is a bigger issue, but
    # at least they are not equal.
    if left.key_type is None or right.key_type is None:
      return False

    if not is_generic_equal(left.key_type, right.key_type):
      return False

  if len(left.elements) != len(right.elements):
    return False

  for left_elem, right_elem in zip(left.elements, right.elements):
    if not is_generic_equal(left_elem, right_elem):
      return False
  return True


def is_reconcilable(schema_type: SchemaType) -> bool:
  """Can the type be reconciled to fix a difference.

  Args:
    schema_type: The type to check.

  Returns:
      True if it can be otherwise false.
  """
  if schema_type.type_str in utils.RECONCILABLE_TYPES:
    return True
  return False


def reconcile_type(left: SchemaType, right: SchemaType) -> Optional[SchemaType]:
  """Reconcile two types.

  To reconcile two types means to "downgrade" a leaf type if there is a
  collision. For example, we can downgrade a 'float' to a 'double', an
  'integer' to a 'float', or a 'string' to a 'char'.

  Args:
    left: The first SchemaType
    right: The second SchemaType

  Raises:
    utils.SchemaTypeError: If there is an invalid schematype or language types
    are
    set.

  Returns:
    The copy of the new type if reconciled, otherwise None.
  """

  # Do not allow
  if left.lang_type != 'NOT_SET' or right.lang_type != 'NOT_SET':
    raise utils.SchemaTypeError('Cannot reconcile types with a lang type')

  if left.is_leaf() or right.is_leaf():
    # If only one is leaf, return None
    if not left.is_leaf() or not right.is_leaf():
      return None
    if is_reconcilable(left) or is_reconcilable(right):
      left_target_types = utils.RECONCILABLE_TYPES.get(left.type_str, set())
      right_target_types = utils.RECONCILABLE_TYPES.get(right.type_str, set())
      if right.type_str in left_target_types:
        # If the right type is the target, return a copy of it.
        return SchemaType.from_generic_type_string(right.to_generic())
      elif left.type_str in right_target_types:

        # The case where it is reconcilable and other is the old type, return
        # left
        return SchemaType.from_generic_type_string(left.to_generic())

      # Otherwise, neither can be reconciled, return None
      return None

    else:
      return None

  # The data structures are not the same.
  if left.type_str != right.type_str:
    return None

  if len(left.elements) != len(right.elements):
    return None

  if left.key_type != right.key_type:
    return None

  new_elements = []
  for element, other_element in zip(left.elements, right.elements):
    new_element = reconcile_type(element, other_element)
    if new_element is None:
      return None
    new_elements.append(new_element)

  new_type = SchemaType.copy(left)
  new_type.elements = new_elements
  return SchemaType.from_generic_type_string(new_type.to_generic())
