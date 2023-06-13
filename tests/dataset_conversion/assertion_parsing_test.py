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
"""Tests for the assertion parsing."""
import ast
import json

from babelcode import utils
from babelcode.dataset_conversion import assertion_parsing
import pytest

TEST_DATA = json.loads(
    utils.FIXTURES_PATH.joinpath('assertion_parsing_testdata.json').read_text())
TEST_NAME_TO_DATA = {
    'test_parses_basic': TEST_DATA['BASIC_ASSERTIONS'],
    'test_multiple_asserts': TEST_DATA['MULTIPLE_TEST_CASES'],
}


def pytest_generate_tests(metafunc):
  """Generates the tests dynamically from the passed in test data."""
  test_name = metafunc.function.__name__
  test_cls = metafunc.cls
  if test_cls is None:
    return
  argnames = None
  argvalues = None
  ids = None
  if test_cls.__name__ == 'TestAssertionToSchemaVisitor':
    if test_name in ['test_parses_basic', 'test_multiple_asserts']:
      argnames = ['input_str', 'expected_output_dict']
      argvalues = []
      ids = []
      to_use = TEST_NAME_TO_DATA[test_name]

      for id_name, id_data in to_use.items():
        ids.append(id_name)
        input_str, output_data = id_data

        # Fix the schema types from json
        fixed_expected = {}
        for k, v in output_data.items():
          for i in range(len(v['schema']['params'])):
            v['schema']['params'][i] = tuple(v['schema']['params'][i])

          v['schema']['returns'] = tuple(v['schema']['returns'])
          fixed_expected[int(k)] = v
        argvalues.append((input_str, fixed_expected))

  if argnames:
    metafunc.parametrize(argnames=argnames, argvalues=argvalues, ids=ids)


class TestAssertionToSchemaVisitor:

  def test_parses_basic(self, input_str, expected_output_dict):
    # Test that it parses a single assertion line correctly.
    visitor = assertion_parsing.AssertionToSchemaVisitor('f')
    visitor.visit(ast.parse(input_str))
    assert set(visitor.test_cases) == {0}

    expected = expected_output_dict[0]
    assert visitor.test_cases[0] == expected

  def test_multiple_asserts(self, input_str, expected_output_dict):
    visitor = assertion_parsing.AssertionToSchemaVisitor('f')
    visitor.visit(ast.parse(input_str))
    assert visitor.test_cases == expected_output_dict

  @pytest.mark.parametrize(
      'input_str',
      [
          'assert f(1) != "A"',
          'assert a.f(1) == 2',
          'import random\nassert a.f(1)',
          'assert 1+2==3',
      ],
  )
  def test_raises_error(self, input_str):
    visitor = assertion_parsing.AssertionToSchemaVisitor('f')
    with pytest.raises(assertion_parsing.AssertionToSchemaError):
      _ = visitor.visit(ast.parse(input_str))

  def test_tuple_no_children(self):
    testing_code = [
        'assert clear_tuple((1, 5, 3, 6, 8)) == ()',
    ]
    testing_code = '\n'.join(testing_code)

    visitor = assertion_parsing.AssertionToSchemaVisitor('clear_tuple')
    visitor.visit(ast.parse(testing_code))
    assert len(visitor.test_cases) == 1
    result_schema = visitor.test_cases[0]['schema']['returns']
    assert result_schema == ('tuple<null>', 1)

  def test_set_single_item(self):
    testing_code = ['assert my_dict({})==True']
    testing_code = '\n'.join(testing_code)

    visitor = assertion_parsing.AssertionToSchemaVisitor('clear_tuple')
    visitor.visit(ast.parse(testing_code))
    assert len(visitor.test_cases) == 1
    result_schema = visitor.test_cases[0]['schema']['params'][0]
    assert result_schema == ('set<null>', 1)


class TestLiteralParser:

  def setup_method(self, method):
    self.visitor = assertion_parsing.LiteralParser()

  def _parse_literal(self, code):
    self.visitor.visit(ast.parse(code).body[0].value)

  @pytest.mark.parametrize('input_str', ['f(x(y))', 'a(x)', 'a(1,x)'])
  def test_should_fail(self, input_str):
    """Tests the cases that should fail."""
    with pytest.raises(assertion_parsing.LiteralParsingError):
      self._parse_literal(input_str)

  def test_empty_list_nested(self):
    """Tests that the schema can properly be deduced when there is an empty list.
    """
    self._parse_literal('[[],[1],[1,2,3]]')

    assert self.visitor.schema_type == 'list<list<integer>>'
    assert self.visitor.value == [[], [1], [1, 2, 3]]

  def test_consolidate_types(self):
    """Tests that the consolidation works."""
    self._parse_literal('[[1.0000000000001,1],[1,1],[1,1.0]]')

    assert self.visitor.schema_type == 'list<list<double>>'
    assert self.visitor.value == [
        [1.0000000000001, 1.0],
        [1.0, 1.0],
        [1.0, 1.0],
    ]

  def test_detects_long(self):
    self._parse_literal('[3027040707]')

    assert self.visitor.schema_type == 'list<long>'
    assert self.visitor.value == [3027040707]

  def test_converts_list_of_int_to_float(self):
    """Regression test for converting list of ints and floats to list[float]."""
    self._parse_literal('[1, 3, 2.0, 8.0]')
    assert self.visitor.schema_type == 'list<float>'
    assert all(isinstance(v, float) for v in self.visitor.value)
    assert self.visitor.value == [1.0, 3.0, 2.0, 8.0]

  def convert_single_character_to_character(self):
    self._parse_literal('"a"')
    assert self.visitor.schema_type == 'character'
    assert self.visitor.value == 'a'

  def test_consolidate_types_strings(self):
    """Tests that the consolidation works."""
    self._parse_literal("['3', '11111111']")

    assert self.visitor.schema_type == 'list<string>'
    assert self.visitor.value == ['3', '11111111']
