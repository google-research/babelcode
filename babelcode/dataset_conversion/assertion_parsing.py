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
"""Functions for parsing assertion statements."""

import ast
# Python AST library has a visitor class to recursively traverse the tree. To do
# this you need to override the visit_NODE NAME functions. These cause a pylint
# error but there is no way around it.
# pylint: disable=invalid-name

import re
from typing import List, Tuple, Union

from absl import logging

from babelcode import schema_parsing
from babelcode.dataset_conversion import utils

DOUBLE_REGEX = re.compile(r'.[0-9]{7,}')
UNSUPPORTED_TYPES = (
    ast.Assign,
    ast.With,
    ast.For,
    ast.While,
    ast.FunctionDef,
    ast.ClassDef,
    ast.AnnAssign,
    ast.ListComp,
    ast.Lambda,
    ast.DictComp,
    ast.GeneratorExp,
)


def _write_error_logs(node, msg):
  """Write logging messages for when raising an error.

  Args:
      node: The ast node the error occurred at.
      msg: The message of the error.
  """
  source_code = utils.convert_to_source(node)
  logging.error('Test case error: "%s"', msg)
  logging.debug('Source code=%s', source_code)
  logging.debug('AST Tree for error was %s', ast.dump(node))


class LiteralParsingError(Exception):
  """Error for if a literal is not parsable."""


class LiteralParser(ast.NodeVisitor):
  """Visitor for parsing literal objects in python.

  Attributes:
    depth: The current depth.
    schema_type: The current schematype.
    value: The current value
  """

  def __init__(self):
    """Initializes the visitor."""
    self.depth = 0
    self.schema_type = None
    self.value = None

  def _make_error(self, node: ast.AST, msg: str) -> LiteralParsingError:
    """Writes debugging information and creates the error.

    Args:
      node: The current AST Node.
      msg: The message to send.

    Returns:
      The LiteralParsingError to raise.
    """
    _write_error_logs(node, msg)
    logging.debug('value=%s', self.value)
    logging.debug('schema_type=%s', self.schema_type)
    logging.debug('depth=%d', self.depth)
    return LiteralParsingError(msg)

  def set_attributes(self, value: schema_parsing.SchemaValueType,
                     schema_type: str, depth: int):
    """Sets the class attributes for recursion.

    Args:
        value: The new self.value.
        schema_type: The new self.schema_type.
        depth: The new self.depth.
    """
    self.depth = depth
    self.schema_type = schema_type
    self.value = value

  def validate_types(self, schema_types: List[str]) -> str:
    """Validates that only a single type was found.

    Args:
        schema_types (List[str]): List of types found.

    Raises:
        LiteralParsingError: If there are more than one schema type.

    Returns:
        str: The single schema type found.
    """

    # Clean types for equivalent numeric types.
    consolidate_type_found = False

    for v in schema_types:
      for t in ['long', 'integer', 'float', 'double', 'string', 'character']:
        if t in v:
          consolidate_type_found = True
          break

    if consolidate_type_found:
      consolidated_schema_types = []
      for t in schema_types:
        new_type = schema_parsing.SchemaType.from_generic_type_string(t)
        if not consolidated_schema_types:
          consolidated_schema_types.append(new_type)
          continue
        to_keep = []
        for other in consolidated_schema_types:
          result = schema_parsing.reconcile_type(new_type, other)
          if result is not None:
            new_type = result
          else:
            to_keep.append(other)
        del consolidated_schema_types
        consolidated_schema_types = [*to_keep, new_type]

      schema_types = list(
          map(lambda t: t.to_generic(), consolidated_schema_types))
    unique_types = len(set(schema_types))

    # No types found, then it must be null.
    if unique_types == 0:
      return 'null'

    # We expect 1 unique type per literal value node.
    elif unique_types != 1:
      raise LiteralParsingError(f'Expecting one type, got {unique_types}')

    return schema_types[0]

  def visit_Constant(self, node: ast.Constant):
    """Handles the constant node.

    Args:
        node (ast.Constant): The constant/literal node.

    Raises:
        LiteralParsingError: If the type of the node's value is not a primitive.
    """
    self.value = node.value
    self.schema_type = type(self.value).__name__
    if self.value is None:
      self.schema_type = 'null'
      return
    if self.schema_type not in utils.PRIMITIVE_TYPES_TO_GENERIC:
      raise LiteralParsingError(
          f'{self.schema_type} is a constant but not a primitive')
    self.schema_type = utils.PRIMITIVE_TYPES_TO_GENERIC[self.schema_type]

    # Check for doubles here.
    if self.schema_type == 'float':
      self.value = float(self.value)
      if DOUBLE_REGEX.search(str(self.value)):
        self.schema_type = 'double'
    elif self.schema_type == 'integer':
      if len(str(self.value)) > 9:
        self.schema_type = 'long'

    # Check for single character values.
    if self.schema_type == 'string':
      if len(self.value) == 1:
        self.schema_type = 'character'

  def _get_children(self, children_nodes: List[ast.AST],
                    starting_depth: int) -> Tuple[List[str], List[str], int]:
    """Gets the children types, values, and maximum depth of a given node.

    Args:
      children_nodes: The children nodes to traverse.
      starting_depth: The starting depth.

    Returns:
      The values found, the schema types found, and the max depth.
    """
    children_types = []
    children_values = []
    max_depth = starting_depth
    for child in children_nodes:
      self.depth = starting_depth
      self.visit(child)
      schema_type = schema_parsing.SchemaType.from_generic_type_string(
          self.schema_type)
      has_equal_type = False
      type_to_replace = None

      for i, (k, v) in enumerate(children_types):
        if (schema_parsing.is_generic_equal(schema_type, v)
            and not schema_type.is_leaf()):
          null_in_either = 'null' in k and 'null' not in self.schema_type
          if null_in_either and 'tuple' not in self.schema_type:
            type_to_replace = i

          break

      if type_to_replace is not None:
        children_types[type_to_replace] = (self.schema_type, schema_type)
      elif not has_equal_type:
        children_types.append((self.schema_type, schema_type))
      children_values.append(self.value)
      max_depth = max(self.depth, max_depth)

    return children_values, [v[0] for v in children_types], max_depth

  def _handle_list(self, node: Union[ast.List, ast.Set], type_name: str):
    """Parses a list or set node.

    Args:
        node (Union[ast.List,ast.Set]): The node to parse
        type_name (str): The type calling this function
    """
    # Lists and Sets have the same attributes to query, so we can do
    # those in one swoop.
    self.depth += 1
    children_values, children_types, max_depth = self._get_children(
        node.elts, self.depth)
    type_found = self.validate_types(children_types)

    # Need to map the list of children values to floats to match the type.
    if type_found in ['float', 'double']:
      children_values = list(map(float, children_values))

    self.set_attributes(
        depth=max_depth,
        schema_type=f'{type_name}<{type_found}>',
        value=children_values,
    )

  def visit_List(self, node: ast.List) -> None:
    """Handles the list node.

    Args:
      node: The list node to parse.
    """
    self._handle_list(node, 'list')

  def visit_Set(self, node: ast.Set) -> None:
    """Handles the set node.

    Args:
      node: The current node.
    """
    self._handle_list(node, 'set')

  def visit_Dict(self, node: ast.Dict) -> None:
    """Handles the dict node.

    Args:
      node: The dictionary node.

    Raises:
      LiteralParsingError: If there are parsing issues with the dictionary.
    """
    self.depth += 1
    depth = self.depth
    key_values, key_type, _ = self._get_children(node.keys, depth)
    key_type = self.validate_types(key_type)
    if key_type == 'character':
      key_type = 'string'
    elif key_type not in ['integer', 'string', 'boolean']:
      # In the case a dictionary is actually an empty set
      if key_type == 'null':
        self.set_attributes(value={}, schema_type='set<null>', depth=depth)
        return

      raise self._make_error(node,
                             f'Dictionary keys cannot be of type {key_type}')

    children_values, children_type, max_depth = self._get_children(
        node.values, depth)
    children_type = self.validate_types(children_type)
    if len(children_values) != len(key_values):
      raise LiteralParsingError(
          'Dicts require the keys and children values have the same length.')

    # Need to map the list of children values to floats to match the type.
    if children_type in ['float', 'double']:
      children_values = list(map(float, children_values))

    schema = f'map<{key_type};{children_type}>'
    self.set_attributes(
        value={
            k: v for k, v in zip(key_values, children_values)
        },
        schema_type=schema,
        depth=max_depth,
    )

  def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
    """Handles the unary op node.

    Args:
      node: The unary operation node.

    Raises:
      LiteralParsingError: if there was an error trying to apply the unary
      operation to the value.
    """
    depth = self.depth
    children_value, children_type, max_depth = self._get_children(
        [node.operand], depth)

    children_type = self.validate_types(children_type)
    if len(children_value) != 1:
      logging.warning('Found unary op with more than 1 child value')
      logging.debug('source code: %s', utils.convert_to_source(node))
    children_value = children_value[0]
    if isinstance(node.op, ast.USub):
      try:
        children_value = -1 * children_value
      except ValueError as e:
        raise self._make_error(node, 'Could not apply -1 * node') from e
    elif isinstance(node.op, ast.Not):
      children_value = not children_value
      children_type = 'boolean'
    else:
      raise self._make_error(node,
                             f'Unsupported unary op {type(node.op).__name__}')
    self.set_attributes(children_value, children_type, max_depth)

  def visit_Tuple(self, node: ast.Tuple) -> None:
    """Handles the tuple node.

    Args:
      node: The tuple node to parse.
    """
    self.depth += 1
    children_values, children_types, max_depth = self._get_children(
        node.elts, self.depth)

    if children_types:
      child_type_str = '|'.join(children_types)
    else:
      child_type_str = 'null'
      self.value = []

    schema_type = f'tuple<{child_type_str}>'
    self.set_attributes(children_values, schema_type, max_depth)

  def generic_visit(self, node: ast.AST) -> None:
    """Raises an error for unsupported ast types.

    Args:
      node: The current node.

    Raises:
      LiteralParsingError: If this function is called, it means an unsupported
      type was encountered.
    """
    # Save the node source for debugging.
    raise self._make_error(node, f'{type(node).__name__} is not supported')


class AssertionToSchemaError(Exception):
  """Error for when parsing schema from an assertion fails."""


class AssertionToSchemaVisitor(ast.NodeVisitor):
  """Node visitor for getting test case values from an assertion."""

  def __init__(self, target_fn_name: str) -> None:
    self.target_fn = target_fn_name
    self.test_cases = {}

    self._input_schema = []
    self._input_arguments = []

  def _make_error(self, node, msg):
    _write_error_logs(node, msg)
    return AssertionToSchemaError(msg)

  def _parse_literal(self, node):
    visitor = LiteralParser()
    visitor.visit(node)
    return visitor.value, visitor.schema_type, visitor.depth

  def visit_Assert(self, node: ast.Assert) -> None:
    """Handles the assertion AST node.

    Args:
      node: The assertion AST node.

    Raises:
      AssertionToSchemaError: If the assertion is not in the `assert f(x) == y`
      format.
    """

    self._input_arguments = []
    self._input_schema = []
    logging.debug('Found new test case at %s', utils.convert_to_source(node))
    test_node = node.test
    # Handling the case of assert f(Arguments) == Value
    if isinstance(test_node, ast.Compare):
      if not isinstance(test_node.ops[0], ast.Eq):
        raise self._make_error(test_node, 'Only == is supported for operators')
      if not isinstance(test_node.left, ast.Call):
        raise self._make_error(
            test_node, 'Only calls on the left side are currently supported')
      self.visit(test_node.left)
      if len(test_node.comparators) != 1:
        raise self._make_error(test_node,
                               'The right hand side must be a single value')

      output, output_type, depth = self._parse_literal(test_node.comparators[0])
      output_schema = (output_type, depth)

    # Handling the case of assert not f(arguments)
    elif isinstance(test_node, ast.UnaryOp):
      if not isinstance(test_node.op, ast.Not):
        raise self._make_error(test_node,
                               'Only "not" is supported for unary operators')
      output = False
      output_schema = ('boolean', 0)
      if not isinstance(test_node.operand, ast.Call):
        raise self._make_error(test_node,
                               'When using "not", the operand must be a call')
      self.visit(test_node.operand)

    # Handling the case of assert f(Arguments)
    elif isinstance(test_node, ast.Call):
      self.visit(test_node)
      output = True

      output_schema = ('boolean', 0)

    else:
      raise self._make_error(
          test_node,
          f'Unexpected type of {type(test_node).__name__} for test call',
      )

    logging.debug('Adding test case with idx=%d', len(self.test_cases))
    logging.debug('Input schema=%s', self._input_schema)
    logging.debug('output schema=%s', output_schema)
    self.test_cases[len(self.test_cases)] = {
        'inputs': self._input_arguments,
        'outputs': output,
        'schema': {
            'params': self._input_schema,
            'returns': output_schema
        },
    }

  def visit_Call(self, node: ast.Call) -> None:
    """Handles the call AST node.

    Args:
      node: The call AST Node.

    Raises:
      AssertionToSchemaError: If the call is not parsable.
    """
    if not isinstance(node.func, ast.Name):
      raise self._make_error(
          node, 'The calling function must be a name (i.e. not an attribute)')

    if node.func.id != self.target_fn:
      for arg_node in node.args:
        self.visit(arg_node)

    if self._input_arguments:
      raise self._make_error(
          node, 'Multiple non-nested function calls are not yet supported')

    for arg_node in node.args:
      arg_value, arg_type, arg_depth = self._parse_literal(arg_node)
      self._input_schema.append((arg_type, arg_depth))
      self._input_arguments.append(arg_value)
    if not self._input_arguments:
      raise self._make_error(node, 'Calls with no arguments are not supported.')

  def generic_visit(self, node: ast.AST):
    """Override the generic visit to restrict what types are allowed.

    Args:
        node (ast.AST): The current Node

    Raises:
        AssertionToSchemaError: Unable to parse the node.
    """
    if isinstance(node, UNSUPPORTED_TYPES):
      logging.warning('"%s" is not a supported type', type(node).__name__)
      logging.debug('source_code: %s', utils.convert_to_source(node))
      return
    if isinstance(node, (ast.Import, ast.ImportFrom)):
      raise AssertionToSchemaError('Imports are not supported')

    # Manually call visit_Assert here so we can catch AssertionToSchemaErrors
    # and print out the calling node's source code for debugging.
    if isinstance(node, ast.Assert):
      try:
        self.visit_Assert(node)
      except AssertionToSchemaError as e:
        logging.debug(
            'Assertion Code that caused error: %s',
            utils.convert_to_source(node),
        )
        raise e
    else:
      super().generic_visit(node)
