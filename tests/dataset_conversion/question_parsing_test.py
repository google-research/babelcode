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

"""Tests for parsing questions module."""
# Because of how pytest fixtures work, this error will be incorrectly triggered,
# so disable it for the file here. Pytest Fixture docs:
# https://docs.pytest.org/en/6.2.x/fixture.html
# pylint:disable=redefined-outer-name
import ast
import copy
import json
import os
import pathlib

import pytest

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import utils as bc_utils
from babelcode.dataset_conversion import assertion_parsing
from babelcode.dataset_conversion import question_parsing

SchemaType = schema_parsing.SchemaType
ERROR_TESTS = {}
VALID_TESTS = {}
TEST_DATA_PATH = bc_utils.FIXTURES_PATH.joinpath(
    'question_parsing_testdata.json'
)
for test_name, test_info in json.loads(TEST_DATA_PATH.read_text()).items():
  if test_info.get('expected_error', None):
    ERROR_TESTS[test_name] = [test_info['input'], test_info['expected_error']]
  else:
    VALID_TESTS[test_name] = [test_info['input'], test_info['expected']]


@pytest.fixture()
def valid_errors():
  yield (
      data_types.QuestionParsingError,
      data_types.QuestionValidationError,
      assertion_parsing.AssertionToSchemaError,
      assertion_parsing.LiteralParsingError,
      data_types.IOPairError,
  )


def pytest_generate_tests(metafunc):
  test_name = metafunc.function.__name__

  if 'parse_question' in test_name:
    argnames = ['question_dict', 'expected']
    if 'valid' in test_name:
      tests_to_use = VALID_TESTS
    else:
      tests_to_use = ERROR_TESTS

    ids = []
    arg_values = []
    for test_id, test_values in copy.deepcopy(tests_to_use).items():
      ids.append(test_id)
      arg_values.append(test_values)

    metafunc.parametrize(argnames=argnames, argvalues=arg_values, ids=ids)


def test_parse_question_valid(question_dict, expected):
  test_code = question_dict.pop('test_list')
  question_dict['testing_code'] = '\n'.join(test_code)
  result = question_parsing.parse_question_dict(**question_dict)
  assert set(result.keys()) == set(expected.keys())
  assert result['entry_fn_name'] == expected['entry_fn_name']
  assert result['schema'] == expected['schema']
  assert len(result['test_list']) == len(expected['test_list'])
  for i in range(len(result['test_list'])):
    l = result['test_list'][i]
    r = expected['test_list'][i]

    assert l == r, f'{i=} {l=} {r=}'


def test_parse_question_error(question_dict, expected, valid_errors):
  test_code = question_dict.pop('test_list')
  question_dict['testing_code'] = '\n'.join(test_code)
  with pytest.raises(valid_errors) as e:
    _ = question_parsing.parse_question_dict(**question_dict)
  assert expected in str(e)


@pytest.mark.parametrize(
    ['input_str', 'expected'],
    [
        ('List[int]', 'list<integer>'),
        ('Dict[str,List[bool]]', 'map<string;list<boolean>>'),
        ('Tuple[List[str],int]', 'tuple<list<string>|integer>'),
    ],
)
def test_convert_type_annotation(input_str, expected):
  node = ast.parse(input_str).body[0].value
  result = question_parsing._convert_type_annotation_to_schema(node)
  assert result == expected


@pytest.mark.parametrize(
    ['input_str'],
    [('float[int]',), ('List',), ('List[str,str]',), ('Dict[str]',)],
)
def test_convert_type_annotation_error(input_str):
  node = ast.parse(input_str).body[0].value
  with pytest.raises(question_parsing.utils.AnnotationError):
    _ = question_parsing._convert_type_annotation_to_schema(node)


@pytest.mark.parametrize(
    ['input_str', 'expected'],
    [
        ('list<null>', 'list<integer>'),
        ('list<integer>', 'list<integer>'),
        (None, 'list<integer>'),
    ],
)
def test_get_final_schema_type(input_str, expected):
  schema_types = [
      question_parsing.PotentialType(
          SchemaType.from_generic_type_string(s), s, 1, 1
      )
      for s in ['list<integer>']
  ]

  result = question_parsing._get_final_schema_type(
      'test', 'test', schema_types, input_str
  )
  assert result == expected


@pytest.mark.parametrize(
    ['arg_types', 'return_type'],
    [
        (['list<integer>', 'string'], 'list<boolean>'),
        (['null', 'null'], 'null'),
        ([None, None], None),
    ],
)
def test_consolidate_schema_from_test_cases(arg_types, return_type):
  test_cases = {
      0: {
          'inputs': [[1], 'typing'],
          'outputs': [],
          'schema': {
              'params': [
                  ('list<integer>', 1),
                  ('string', 0),
              ],
              'returns': ('list<null>', 1),
          },
      },
      1: {
          'inputs': [[], 'typing'],
          'outputs': [True],
          'schema': {
              'params': [
                  ('list<null>', 1),
                  ('string', 0),
              ],
              'returns': ('list<boolean>', 1),
          },
      },
      2: {
          'inputs': [[], ''],
          'outputs': [],
          'schema': {
              'params': [
                  ('list<null>', 1),
                  ('null', 0),
              ],
              'returns': ('list<null>', 1),
          },
      },
  }
  args = ['a', 'b']
  found_types = {v: arg_types[i] for i, v in enumerate(args)}

  (
      result_arg_types,
      result_return_type,
  ) = question_parsing.consolidate_schema_from_test_cases(
      'test', test_cases, args, found_types, return_type
  )
  assert result_arg_types == {'a': 'list<integer>', 'b': 'string'}
  assert result_return_type == 'list<boolean>'


def test_consolidate_schema_float_and_double():
  test_cases = {
      0: {
          'inputs': [[1]],
          'outputs': [],
          'schema': {
              'params': [
                  ('list<null>', 1),
              ],
              'returns': ('map<string;float>', 1),
          },
      },
      1: {
          'inputs': [[]],
          'outputs': [True],
          'schema': {
              'params': [
                  ('list<double>', 1),
              ],
              'returns': ('map<string;double>', 1),
          },
      },
  }
  args = ['a']
  found_types = {'a': 'list<float>'}

  (
      result_arg_types,
      result_return_type,
  ) = question_parsing.consolidate_schema_from_test_cases(
      'test', test_cases, args, found_types, None
  )
  assert result_arg_types == {'a': 'list<double>'}
  assert result_return_type == 'map<string;double>'


def test_get_arguments_default_fail(valid_errors):
  solution = 'def test(a, b=1):\n\tpass'
  with pytest.raises(valid_errors):
    _ = question_parsing.get_arguments_from_solution('Test', solution, 'test')


def test_get_arguments_invalid_annotation():
  solution = 'def get_positive(l: list):\n\tpass'
  args, arg_types, return_type = question_parsing.get_arguments_from_solution(
      'Test', solution, 'get_positive'
  )
  assert args == ['l']
  assert arg_types == {'l': None}
  assert return_type is None
