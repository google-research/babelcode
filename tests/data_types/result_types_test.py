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

"""Tests for result data types."""
import math
import pathlib

from babelcode.data_types import result_types
from babelcode.data_types.command import Command
from babelcode.data_types.prediction import Prediction
import pytest

PredictionOutcome = result_types.PredictionOutcome


class TestPredictionResult:

  @pytest.mark.parametrize(
      ['return_code', 'stdout', 'stderr', 'expected'],
      [
          (1, '', '', PredictionOutcome.HAD_ERROR),
          (0, 'TEST-0...MISSING\n', '', PredictionOutcome.HAD_ERROR),
          (0, 'TEST-0...KeyError\n', '', PredictionOutcome.HAD_RUNTIME_ERROR),
          (0, 'TEST-0...FAILED\n', '', PredictionOutcome.FAILED_TEST),
          (0, 'TEST-0...PASSED\n', '', PredictionOutcome.PASSED),
          (0, 'TEST-0...PASSED\n', 'Warnings:', PredictionOutcome.PASSED),
      ],
      ids=[
          'RTR_Fail',
          'MISSING',
          'RuntimeError',
          'FailedTests',
          'Passed',
          'Passed_Warnings',
      ],
  )
  def test_process_execution_result_failures(
      self, return_code, stdout, stderr, expected
  ):
    pred = Prediction(
        qid='1',
        id='test',
        lang='C++',
        code='cpp_code',
        file_path=pathlib.Path('1.cpp'),
    )
    exec_result = result_types.ExecutionResult(
        prediction=pred,
        commands=[Command('test command')],
        stdout=stdout,
        stderr=stderr,
        net_runtime=1.0,
        return_code=return_code,
        last_ran_command_idx=0,
        had_error=return_code != 0,
        command_runtimes=[0.9, None],
        command_memory=[10, None],
    )
    if not stdout:
      tc_results = {'0': 'MISSING'}
    else:
      tc_results = {'0': stdout.split('.')[-1].strip()}

    result = result_types.PredictionResult.from_execution_result(
        exec_result, {'test_case_ids': ['0']}
    )
    expected_result = result_types.PredictionResult(
        qid=exec_result.prediction.qid,
        id=exec_result.prediction.id,
        lang=exec_result.prediction.lang,
        outcome=expected,
        test_case_results=tc_results,
        num_tc_passed=sum(v == 'PASSED' for v in tc_results.values()),
        num_tc=1,
        all_commands_ran=True,
        net_runtime=1.0,
        code='cpp_code',
        stderr=stderr,
        final_command_memory=10,
        final_command_runtime=0.9,
        command_memory=[10, None],
        command_runtimes=[0.9, None],
    )

    assert result == expected_result

  @pytest.mark.parametrize(
      ['tc_results', 'expected_outcome'],
      [
          (
              {'1': 'PASSED', '2': 'PASSED', 'CHEESE.BALL': 'PASSED'},
              PredictionOutcome.PASSED,
          ),
          (
              {'1': 'PASSED', '2': 'FAILED', 'CHEESE.BALL': 'PASSED'},
              PredictionOutcome.FAILED_TEST,
          ),
      ],
      ids=['passed', 'failed_test'],
  )
  def test_process_execution_result_passes(self, tc_results, expected_outcome):
    stdout = '\n'.join(f'TEST-{k}...{v}' for k, v in tc_results.items())
    pred = Prediction(
        qid='1',
        id='test',
        lang='C++',
        code='cpp_code',
        file_path=pathlib.Path('1.cpp'),
    )
    exec_result = result_types.ExecutionResult(
        prediction=pred,
        commands=[Command('test command')],
        stdout=stdout,
        stderr='',
        net_runtime=1.0,
        return_code=0,
        last_ran_command_idx=1,
        command_runtimes=[1.0, 2.0],
        command_memory=[0, 10],
    )
    result: result_types.PredictionResult = (
        result_types.PredictionResult.from_execution_result(
            exec_result, {'test_case_ids': ['1', '2', 'CHEESE.BALL']}
        )
    )
    assert result.outcome == expected_outcome
    assert result.test_case_results == tc_results
    assert result.num_tc == 3
    assert result.num_tc_passed == sum(
        1 if v == 'PASSED' else 0 for v in tc_results.values()
    )
    assert result.net_runtime == 1.0
    assert result.code == pred.code
    assert math.isclose(result.final_command_runtime, 2.0)
    assert result.final_command_memory == 10

  def test_process_execution_incorrect_all_missing(self):
    stdout = 'TEST-10...PASSED\nTEST-4...PASSED\nTEST-5...PASSED\n'

    pred = Prediction(
        qid='1',
        id='test',
        lang='C++',
        code='cpp_code',
        file_path=pathlib.Path('1.cpp'),
    )
    exec_result = result_types.ExecutionResult(
        prediction=pred,
        commands=[Command('test command')],
        stdout=stdout,
        stderr='',
        return_code=0,
        net_runtime=1.0,
        last_ran_command_idx=0,
        command_runtimes=[1.0],
        command_memory=[10],
    )

    result = result_types.PredictionResult.from_execution_result(
        exec_result, {'test_case_ids': ['0', '1', '2']}
    )
    assert result.outcome == PredictionOutcome.HAD_ERROR
    assert result.test_case_results == {
        '0': 'MISSING',
        '1': 'MISSING',
        '2': 'MISSING',
    }
    assert result.net_runtime == 1.0
    assert result.code == pred.code


@pytest.fixture
def prediction_result(request) -> result_types.PredictionResult:
  default_kwargs = {
      'qid': '0',
      'id': '0',
      'lang': 'Python',
      'outcome': PredictionOutcome.PASSED,
      'test_case_results': {'0': 'PASSED', '1': 'PASSED'},
      'net_runtime': 1.1,
      'num_tc_passed': 2,
      'num_tc': 2,
      'all_commands_ran': True,
      'final_command_runtime': 1.0,
      'final_command_memory': 10,
      'command_runtimes': [1.0],
      'command_memory': [10],
      'stderr': '',
      'code': 'Test Code',
  }

  pred_kwargs = {}
  for k, v in default_kwargs.items():
    if hasattr(request, 'params'):
      pred_kwargs[k] = request.params.get(k, v)
    else:
      pred_kwargs[k] = v

  yield result_types.PredictionResult(**pred_kwargs)


class TestQuestionResult:

  def test_update_with_result(self, prediction_result):
    """Tests updating a question result."""
    result = result_types.QuestionResult(
        '0', 'Python', 2, tracked_attributes=['final_command_memory']
    )
    result.update_with_result(prediction_result)

    assert result.num_predictions == 1
    expected_keys = set(PredictionOutcome)
    expected_keys.update(['final_command_memory', 'num_tc_passed'])
    assert set(result.results.keys()) == expected_keys

    expected_outcome = prediction_result.outcome
    outcome_results = {v: result.results[v] for v in PredictionOutcome}
    expected_outcome_results = {}
    for v in PredictionOutcome:
      if v == expected_outcome:
        expected_outcome_results[v] = [True]
      else:
        expected_outcome_results[v] = [False]
    assert outcome_results == expected_outcome_results
    assert result.results['final_command_memory'] == [
        prediction_result.final_command_memory
    ]

    assert len(result.specific_test_results) == prediction_result.num_tc

    for k, v in prediction_result.test_case_results.items():
      assert k in result.specific_test_results, f'Missing test "{k}"'
      assert result.specific_test_results[k] == {
          v: 1
      }, f'{k} does not have correct value.'

  def test_get_vals_for_idx(self, prediction_result):
    """Tests getting values for a prediction idx."""
    q_result = result_types.QuestionResult(
        '0', 'Python', 2, tracked_attributes=['final_command_memory']
    )
    q_result.update_with_result(prediction_result)

    result = q_result.get_vals_for_idx(0)

    expected_results = {k: False for k in PredictionOutcome}
    expected_results[PredictionOutcome.PASSED] = True
    expected_results['final_command_memory'] = 10
    expected_results['num_tc_passed'] = 2
    assert result == expected_results
