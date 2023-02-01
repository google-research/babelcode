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

"""Functions for converting a question from a dataset to the correct format."""

import ast
import collections
import dataclasses
from typing import Any, Dict, List, Optional, Tuple

from absl import logging

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import utils as bc_utils
from babelcode.dataset_conversion import assertion_parsing
from babelcode.dataset_conversion import utils


# List of reserved keywords across languages, not exhaustive.
PROJECT_ROOT = bc_utils.PROJECT_ROOT
RESERVED_KEYWORDS = frozenset(
    PROJECT_ROOT.joinpath('data', 'reserved_keywords.txt')
    .read_text()
    .splitlines(False)+[data_types.EXPECTED_KEY_NAME]
)


# Define the list of potentially raised errors for use in try except.
POTENTIAL_ERROR_TYPES = (
    utils.AnnotationError,
    assertion_parsing.AssertionToSchemaError,
    data_types.IOPairError,
    assertion_parsing.LiteralParsingError,
    data_types.QuestionValidationError,
    data_types.QuestionParsingError,
)


def _convert_type_annotation_to_schema(type_annotation) -> str:
  """Converts a type annotation string to the generic values.

  Args:
      type_annotation: The node to convert.

  Raises:
    utils.AnnotationError: The type annotation is not valid.

  Returns:
      The generic type string.
  """
  if isinstance(type_annotation, ast.Name):
    if type_annotation.id in utils.PRIMITIVE_TYPES_TO_GENERIC:
      return utils.PRIMITIVE_TYPES_TO_GENERIC[type_annotation.id]
    raise utils.AnnotationError(f'{type_annotation.id} cannot be a leaf node')

  if not isinstance(type_annotation, ast.Subscript):
    raise utils.AnnotationError(
        'type_annotation must be either a Subscript or Name, '
        f'got {type(type_annotation).__name__}'
    )

  # Index can be a tuple or single value.
  value_node = type_annotation.slice
  if isinstance(value_node, ast.Tuple):
    children = value_node.elts
  elif isinstance(value_node, ast.Name):
    children = [value_node]
  else:
    raise utils.AnnotationError('Subscripts must be either a tuple or name')

  children = list(map(_convert_type_annotation_to_schema, children))

  node_name = type_annotation.value.id
  if node_name in utils.PRIMITIVE_TYPES_TO_GENERIC:
    raise utils.AnnotationError('Primitives must be leaf nodes.')
  if node_name == 'Dict':
    if len(children) != 2:
      raise utils.AnnotationError(
          f'Dicts must have 2 children, found {len(children)}'
      )
    node_name = 'map'
    delimiter = ';'
  elif node_name == 'Tuple':
    node_name = 'tuple'
    delimiter = '|'
  else:
    if len(children) != 1:
      raise utils.AnnotationError(
          f'{node_name} must have 1 child, found {len(children)}'
      )

    if node_name in ['List', 'Set']:
      node_name = node_name.lower()
    delimiter = ','

  return f'{node_name}<{delimiter.join(children)}>'


@dataclasses.dataclass
class PotentialType:
  """Dataclass for potential types to clean up code.

  Attributes:
    schema: The schema type.
    generic_str: The generic string for the schema type.
    n: The number of occurrences found.
    depth: The depth of the type.
  """

  schema: schema_parsing.SchemaType
  generic_str: str
  n: int
  depth: int


def _determine_type_to_keep(
    left: PotentialType, right: PotentialType
) -> PotentialType:
  """Determines which of the two potential types to keep.

  Args:
      left (PotentialType): Option 1.
      right (PotentialType): Option 2

  Returns:
      The type who has the most depth and does not have null types.
  """
  replace_potential_type = False
  if left.depth > right.depth:
    replace_potential_type = True
  if 'null' in right.generic_str and left.depth >= right.depth:
    # We only want to keep the deepest type with null
    replace_potential_type = True

  if replace_potential_type:
    left.n = right.n + 1
    return left

  else:
    right.n += 1
    return right


def _get_final_schema_type(
    qid: str, arg_name: str, schema_list: List[PotentialType], found_type: str
):
  """Determines the final generic type for a given argument.

  Args:
      qid (str): The question id.
      arg_name (str): The argument name
      schema_list (List[PotentialType]): The list of schema types found.
      found_type (str): The type found through annotations.

  Raises:
      IOPairError: If there is an unfixable error with either test case.

  Returns:
      The generic test case string to use.
  """
  non_null_schemas = list(
      filter(lambda s: 'null' not in s.generic_str, schema_list)
  )

  if len(non_null_schemas) > 1:
    logging.error(
        'qid=%s Found more than one potential schema type for %s', qid, arg_name
    )
    logging.debug(
        'Schema types found %s', list(map(lambda s: s.generic_str, schema_list))
    )
    logging.debug(
        'qid=%s has inconsistent types used in test cases for %s, %s',
        qid,
        arg_name,
        ','.join([t.generic_str for t in non_null_schemas]),
    )
    raise data_types.IOPairError('Inconsistent Types found')

  if found_type is None:
    if not non_null_schemas:
      logging.error(
          'qid=%s Could not find any schema type for %s', qid, arg_name
      )
      logging.debug('Input types are: %s', [t.generic_str for t in schema_list])
      raise data_types.IOPairError('No Non-Null types found')

    return non_null_schemas[0].generic_str

  else:
    if non_null_schemas:
      found_schema_type = schema_parsing.SchemaType.from_generic_type_string(
          found_type
      )
      potential_schema_type = non_null_schemas[0].schema
      potential_schema_str = non_null_schemas[0].generic_str
      if 'null' in found_type:
        return potential_schema_str

      if not schema_parsing.is_generic_equal(
          potential_schema_type, found_schema_type
      ):
        reconcile_result = schema_parsing.reconcile_type(
            potential_schema_type, found_schema_type
        )
        if reconcile_result is not None:
          new_type = reconcile_result.to_generic()
          logging.debug(
              'Reconciled %s and %s to %s',
              potential_schema_str,
              found_type,
              new_type,
          )
          return new_type
        logging.error(
            (
                'qid=%s has non equal and non reconcilable types. found_type=%s'
                ' != potential_schema_str=%s'
            ),
            qid,
            found_type,
            potential_schema_str,
        )
        raise data_types.IOPairError('Non equal and non reconcilable types')

    return found_type


def _consolidate_type(
    arg_name: str,
    potential_type: PotentialType,
    existing_type_list: List[PotentialType],
):
  """Consolidate a new type into a list of existing types.

  Args:
      arg_name (str): The argument this is for.
      potential_type (PotentialType): The new type.
      existing_type_list (List[PotentialType]): The list of found types.

  Returns:
      The updated list of found types.
  """
  schema_type_str = potential_type.generic_str
  schema = potential_type.schema
  for j, existing_type in enumerate(existing_type_list):
    logging.debug(
        'Evaluating if schema_type_str=%s == existing_type.generic_str=%s',
        schema_type_str,
        existing_type.generic_str,
    )
    if schema_parsing.is_generic_equal(schema, existing_type.schema):
      logging.debug('They are equal, so determining the type to keep.')
      existing_type_list[j] = _determine_type_to_keep(
          potential_type, existing_type
      )
      return existing_type_list
    reconcile_result = schema_parsing.reconcile_type(
        schema, existing_type.schema
    )
    if reconcile_result is not None:
      existing_type_list[j] = PotentialType(
          schema=reconcile_result,
          generic_str=reconcile_result.to_generic(),
          n=potential_type.n + existing_type.n,
          depth=reconcile_result.depth,
      )
      return existing_type_list

  logging.debug(
      'Adding new potential type schema_type_str=%s to arg_name=%s',
      schema_type_str,
      arg_name,
  )
  existing_type_list.append(potential_type)
  return existing_type_list


def consolidate_schema_from_test_cases(
    qid: str,
    test_cases: List[Dict[str, schema_parsing.SchemaValueType]],
    found_args: List[str],
    found_arg_types: Dict[str, Optional[str]],
    return_type: Optional[str],
) -> Tuple[Dict[str, str], str]:
  """Consolidates the schema with the found and parsed types.

  Using the found types from the type annotations and the types parsed from the
  assert statements, we need to consolidate them and get the final types.

  Args:
    qid: The question id this is for.
    test_cases: The list of test cases.
    found_args: The list of arguments found.
    found_arg_types: The types of arguments found from the annotations.
    return_type: The type found for the return type.

  Raises:
    schema_parsing.SchemaTypeError: If there is an error with the schema.
    data_types.IOPairError: If there is an error with the test case.

  Returns:
    The map of argument name to generic type string and the type string of the
    return.
  """
  # Keep track of schema types by argument idx and depth
  arg_schema_types_found = collections.defaultdict(list)
  expected_schema = []
  expected_number_of_args = len(found_args)
  # Keep track of signature as a whole
  for tc_id, tc in test_cases.items():
    logging.debug('Validating tc_id=%s...', tc_id)
    if len(tc['inputs']) != expected_number_of_args:
      logging.error(
          (
              'Test case tc_id=%s of qid=%s did not have the correct number of'
              ' inputs'
          ),
          tc_id,
          qid,
      )
      logging.error(
          'Expected %s, got %d', expected_number_of_args, len(tc['inputs'])
      )
      logging.debug('Expected arguments are %s', found_args)
      logging.debug('Test case is: %s', tc)
      raise data_types.IOPairError('Incorrect number of inputs')

    # Go through the schema and add the types found and their depth
    logging.debug('Parsing the param types')
    for i, (schema_type_str, depth) in enumerate(tc['schema']['params']):
      try:
        schema = schema_parsing.SchemaType.from_generic_type_string(
            schema_type_str
        )
      except schema_parsing.SchemaTypeError as e:
        logging.error(
            'qid=%s tc_id=%s had invalid schema type string schema_type_str=%s',
            qid,
            tc_id,
            schema_type_str,
        )
        logging.error('Message was %s', e)
        raise e

      potential_type = PotentialType(schema, schema_type_str, 1, depth)
      arg_schema_types_found[i] = _consolidate_type(
          found_args[i], potential_type, arg_schema_types_found[i]
      )
    # Add the potential return type to the list of expected schemas.
    logging.debug('Parsing the return type')

    rtr_str = tc['schema']['returns'][0]
    try:
      parsed_schema_type = schema_parsing.SchemaType.from_generic_type_string(
          rtr_str
      )
    except schema_parsing.SchemaTypeError as e:
      logging.error(tc['schema'])
      raise e
    potential_expected_type = PotentialType(
        parsed_schema_type, rtr_str, 1, tc['schema']['returns'][1]
    )
    expected_schema = _consolidate_type(
        data_types.EXPECTED_KEY_NAME, potential_expected_type, expected_schema
    )

  # Go through and assert that only one schema type was found per argument.
  for arg_idx, schemas_found in arg_schema_types_found.items():
    if arg_idx >= len(found_args):
      logging.error(
          'arg_idx=%d is > len(found_args)=%d', arg_idx, len(found_args)
      )
      raise data_types.IOPairError('Found arg idx too large.')

    found_arg_types[found_args[arg_idx]] = _get_final_schema_type(
        qid,
        found_args[arg_idx],
        schemas_found,
        found_arg_types[found_args[arg_idx]],
    )
  return_type = _get_final_schema_type(
      qid, 'return', expected_schema, return_type
  )

  return found_arg_types, return_type


def get_arguments_from_solution(qid, solution, entry_fn_name):
  """Get the names of arguments from a given solution.

  Args:
      qid: The question id this is for.
      solution: The solution to the problem.
      entry_fn_name: The name of the function we are searching for.

  Raises:
      data_types.QuestionValidationError: If there is an error with the
        solution tree.
      data_types.QuestionParsingError: If there was an error parsing the
        question.

  Returns:
      The argument order and any types found through annotations.
  """
  solution_tree = ast.parse(solution)
  target_function = None
  for b in solution_tree.body:
    if isinstance(b, ast.FunctionDef):
      if b.name == entry_fn_name:
        logging.debug(
            'Found target function with entry_fn_name=%s', entry_fn_name
        )
        target_function = b
        break

  # The target function must be present.
  if target_function is None:
    logging.error('Unable to find entry function "%s"', entry_fn_name)
    raise data_types.QuestionValidationError('Unable to find entry function')

  # Default values are not allowed yet
  if target_function.args.defaults:
    raise data_types.QuestionValidationError('Defaults are not supported yet')
  # Get arguments and their types if present
  arg_order = []
  arg_types = {}
  dupe_arg_types = collections.Counter()

  return_type = None
  target_function: ast.FunctionDef
  logging.debug('Looking for annotations...')
  if target_function.returns is not None:
    try:
      return_type = _convert_type_annotation_to_schema(target_function.returns)
      logging.debug('Found return type of "%s"', return_type)
    except utils.AnnotationError as e:
      logging.warning('Failed to parse return annotation for "%s"', qid)
      logging.debug('Return type error was %s', e)

  argument_nodes = target_function.args.args
  if any(
      getattr(target_function.args, v)
      for v in ['posonlyargs', 'vararg', 'kwonlyargs']
  ):
    raise data_types.QuestionValidationError(
        'Unsupported argument types in the solution'
    )

  if not argument_nodes:
    raise data_types.QuestionParsingError('No arguments')
  for arg in argument_nodes:
    arg_name = arg.arg.lower()
    logging.debug(
        'Found argument "%s" at position %d', arg_name, len(arg_order)
    )
    if dupe_arg_types[arg_name] > 0:
      dupe_arg_types[arg_name] += 1
      arg_name = f'{arg_name}{dupe_arg_types[arg_name]}'
    elif arg_name in arg_types:
      arg_types[f'{arg_name}0'] = arg_types.pop(arg_name)

      for i in range(len(arg_order)):
        if arg_order[i] == arg_name:
          arg_order[i] = f'{arg_name}0'
          break

      dupe_arg_types[arg_name] += 1
      arg_name = f'{arg_name}{dupe_arg_types[arg_name]}'
    arg_order.append(arg_name)
    if arg.annotation is not None:
      try:
        arg_types[arg_name] = _convert_type_annotation_to_schema(arg.annotation)
        logging.debug('%s has type %s', arg_name, arg_types[arg_name])
      except utils.AnnotationError as e:
        logging.warning('failed to parse annotation for %s', arg_name)
        logging.debug('Error for %s was %s', arg_name, e)
        arg_types[arg_name] = None

    else:
      arg_types[arg_name] = None

  # Go through and change the argument names if they are a reserved keyword.
  for i, arg in enumerate(arg_order):
    if arg in RESERVED_KEYWORDS:
      logging.info('Changing argument "%s" as it is a reserved keyword', arg)
      new_arg_name = f'{arg}_arg{i}'
      arg_order[i] = new_arg_name
      arg_types[new_arg_name] = arg_types.pop(arg)
      logging.info('New argument name is "%s"', new_arg_name)

  return arg_order, arg_types, return_type


def parse_question_dict(
    qid: str, testing_code: str, solution: str, entry_fn_name: str
) -> Dict[str, Any]:
  """Parse the schema and test cases for a given question.

  First looks at the function specified by `entry_fn_name` to determine the
  argument names and their ordering. Then checks to see if there are
  annotations. If there are no annotations, we then use the raw values in the
  test case to determine the types.

  Args:
      qid (str): The qid of the question
      testing_code (str): The testing code.
      solution (str): The solution.
      entry_fn_name (str): The name of the function in the solution to use for
        gathering both argument names and types.

  Raises:
    IOPairError: The question had an error in the test cases that made it
    impossible to parse.
    QuestionError: If the function defined by entry_fn_name could not be found.

  Returns:
      A dict with the schema, entry points, and the parsed test list.
  """

  # First find and parse the target function body to determine argument name
  # and order. Also check if there are annotations to use for the schema.
  logging.info('Parsing question dict for question "%s"...', qid)
  arg_order, arg_types, return_type = get_arguments_from_solution(
      qid, solution, entry_fn_name
  )

  uses_type_annotation = False
  if any(v is not None for v in arg_types.values()) and arg_types:
    uses_type_annotation = True

  logging.debug('Argument order is %s', arg_order)
  logging.debug('qid=%s has argument types of %s', qid, arg_types)
  visitor = assertion_parsing.AssertionToSchemaVisitor(entry_fn_name)
  try:
    visitor.visit(ast.parse(testing_code))
  except data_types.IOPairError as e:
    logging.error('Failed to parse test cases from qid=%s', qid)
    if str(e) == 'Imports are not supported':
      # Special handling of this error so that we can explicitly mark them for
      # manual fixing.
      logging.error('Imports found in testing code to qid=%s', qid)
      raise data_types.QuestionValidationError(
          'Requires import(s) to generate tests'
      ) from e
    raise e

  if not visitor.test_cases:
    logging.error('qid=%s does not contain any test cases', qid)
    logging.debug('testing_code=%s', testing_code)
    raise data_types.QuestionParsingError('No test cases were found')

  logging.debug('Found %d test cases in qid=%s', len(visitor.test_cases), qid)
  argument_types, return_type = consolidate_schema_from_test_cases(
      qid,
      test_cases=visitor.test_cases,
      found_args=arg_order,
      found_arg_types=arg_types,
      return_type=return_type,
  )

  logging.debug('Final types for qid=%s are %s', qid, argument_types)
  logging.debug('Final return type for qid=%s is %s', qid, return_type)
  parameters = []
  for v in arg_order:
    parameters.append({'name': v, 'type': argument_types[v]})

  schema = {'params': parameters, 'return': {'type': return_type}}
  test_cases = []
  for k, v in visitor.test_cases.items():
    new_test_case = {'idx': k, 'outputs': v['outputs']}
    new_test_case['inputs'] = {
        arg: value for arg, value in zip(arg_order, v['inputs'])
    }
    test_cases.append(new_test_case)

  return {
      'schema': schema,
      'test_list': test_cases,
      'entry_fn_name': entry_fn_name,
      'use_type_annotation': uses_type_annotation,
  }
