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
"""Tests for question data types."""
# Because of how pytest fixtures work, this error will be incorrectly triggered,
# so disable it for the file here. Pytest Fixture docs:
# https://docs.pytest.org/en/6.2.x/fixture.html
# pylint:disable=redefined-outer-name
import json
import pathlib
import copy
from typing import Dict, Tuple

import pytest

from babelcode import data_types

Question = data_types.Question


@pytest.fixture()
def expected_schema():
  """Expected schema fixture."""
  yield {
      'params': [{
          'name': 'arg',
          'type': 'integer'
      },],
      'return': {
          'type': 'string'
      },
  }


@pytest.fixture()
def expected_tests():
  """Expected tests fixture."""
  yield [{'idx': 0, 'inputs': {'arg': 1}, 'outputs': 'test'}]


@pytest.fixture()
def schema_dict_question(expected_schema, expected_tests):
  """Fixture for a question from a schema dict."""
  input_dict = {
      'qid': 4,
      'title': 'Valid schema dict',
      'schema': {
          'params': [{
              'name': 'arg',
              'type': 'integer'
          }],
          'return': {
              'type': 'string'
          },
      },
      'test_list': [{
          'idx': 0,
          'inputs': {
              'arg': 1
          },
          'outputs': 'test'
      }],
      'entry_fn_name': 'test_dict',
      'text': 'This question has NL',
  }
  question = Question(
      qid='4',
      title='Valid schema dict',
      schema=expected_schema,
      test_list=expected_tests,
      entry_fn_name='test_dict',
      text='This question has NL',
  )
  yield (input_dict, question)


# Don't make this into a fixture so we can parametrize it.
INVALID_QUESTION_DICTS = [
    {
        'qid': 1,
        'title': 'Fail no schema dict',
        'schema': {}
    },
    {
        'qid': 2,
        'title': 'Fail no schema list',
        'schema': [{
            'name': '1'
        }],
    },
    {
        'qid': 3,
        'title': 'Fail wrong schema type',
        'schema': 1
    },
]


# Disable pylint bare generics because otherwise we would have a massive,
# unreadable type annotation.
# pylint:disable=g-bare-generic
def test_read_input_questions(
    tmp_path: pathlib.Path,
    schema_dict_question: Tuple[Dict, Question],
):
  """Test the read_input_questions function."""
  data_path = pathlib.Path(tmp_path, 'questions.jsonl')

  input_questions = [
      *INVALID_QUESTION_DICTS,
      schema_dict_question[0],
  ]

  with data_path.open('w') as f:
    for q in input_questions:
      f.write(json.dumps(q) + '\n')

  result, failed = data_types.read_input_questions(data_path)

  # These are the raw line dictionaries, so need to convert them to strings
  # first.
  failed_ids = {str(q[0]['qid']) for q in failed}

  assert failed_ids == {'1', '2', '3'}

  expected = [schema_dict_question[1]]
  assert result == expected


class TestQuestion:

  # Disable pylint bare generics because otherwise we would have a massive,
  # unreadable type annotation.
  # pylint:disable=g-bare-generic

  def test_from_dict_schema_dict(self, schema_dict_question: Tuple[Dict,
                                                                   Question]):
    """Test the from_dict function with a schema dict."""
    input_dict, expected = schema_dict_question
    assert Question.from_dict(input_dict) == expected

  @pytest.mark.parametrize(
      'input_dict',
      INVALID_QUESTION_DICTS,
      ids=[d['title'] for d in INVALID_QUESTION_DICTS],
  )
  def test_from_dict_failures(self, input_dict):
    """Test that failures raise QuestionError."""
    with pytest.raises(data_types.QuestionParsingError):
      _ = Question.from_dict(input_dict)

  def test_change_var_names(self):
    schema = {
        'params': [
            {
                'name': 'always_money_in',
                'type': 'integer'
            },
            {
                'name': 'testing',
                'type': 'boolean'
            },
        ],
        'return': {
            'type': 'string'
        },
    }
    tests = [
        {
            'idx': 0,
            'inputs': {
                'always_money_in': 1,
                'testing': True
            },
            'outputs': 'test',
        },
        {
            'idx': 1,
            'inputs': {
                'always_money_in': 2,
                'testing': False
            },
            'outputs': 'test',
        },
    ]

    expected_change_schema = copy.deepcopy(schema)
    expected_change_schema['params'][1] = {
        'name': 'the_banana_stand',
        'type': 'boolean',
    }
    expected_change_tests = copy.deepcopy(tests)
    for i in range(len(expected_change_tests)):
      expected_change_tests[i]['inputs'][
          'the_banana_stand'] = expected_change_tests[i]['inputs'].pop(
              'testing')

    question = Question('1',
                        schema=schema,
                        test_list=tests,
                        entry_fn_name='test',
                        title='Test')

    question.change_var_names({'testing': 'the_banana_stand'})

    expected_question = Question(
        '1',
        schema=expected_change_schema,
        test_list=expected_change_tests,
        entry_fn_name='test',
        title='Test',
    )

    assert question == expected_question
