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
"""Tests for metrics."""
import math
import pathlib

from babelcode import metrics
from babelcode.data_types import result_types
from babelcode.data_types.command import Command
from babelcode.data_types.prediction import Prediction
from babelcode.data_types.result_types import ExecutionResult
from babelcode.data_types.result_types import PredictionOutcome
from babelcode.data_types.result_types import QuestionResult
import pytest  # pylint: disable=unused-import


def test_calculate_metrics_from_raw_results():
  pass_result = ExecutionResult(prediction=Prediction('0', '0', 'Python',
                                                      'pass_1',
                                                      pathlib.Path('Test')),
                                commands=[Command(['test', 'command'])],
                                stdout='TEST-0...PASSED\n',
                                stderr='',
                                net_runtime=1.0,
                                return_code=0,
                                last_ran_command_idx=0,
                                had_error=False,
                                command_runtimes=[1.0],
                                command_memory=[1])
  fail_result = ExecutionResult(prediction=Prediction('1', '0', 'Python',
                                                      'fail_1',
                                                      pathlib.Path('Test')),
                                commands=[Command(['test', 'command'])],
                                stdout='TEST-0...FAILED\n',
                                stderr='',
                                net_runtime=2.0,
                                return_code=0,
                                last_ran_command_idx=0,
                                had_error=False,
                                command_runtimes=[1.0],
                                command_memory=[1])

  fail_result_2 = ExecutionResult(prediction=Prediction('0', '1', 'Python',
                                                        'fail_2',
                                                        pathlib.Path('Test')),
                                  commands=[Command(['test', 'command'])],
                                  stdout='TEST-0...MISSING\n',
                                  stderr='FAIL',
                                  net_runtime=2.0,
                                  return_code=0,
                                  last_ran_command_idx=0,
                                  had_error=True,
                                  command_runtimes=[1.0],
                                  command_memory=[1])

  raw_results = [pass_result for _ in range(5)]
  raw_results.extend([fail_result for _ in range(5)])
  raw_results.extend([fail_result_2 for _ in range(7)])

  question_data = {
      '0': {
          'test_case_ids': ['0'],
          'title': 'Q1',
          'tags': ['QT1']
      },
      '1': {
          'test_case_ids': ['0'],
          'title': 'Q2',
          'tags': ['QT2']
      }
  }

  result_metrics, q_results, p_results = metrics.calculate_metrics_from_raw_results(
      raw_results,
      question_data,
      runtime='0:12:34',
      seed=1,
      k_vals=[1, 10, 15],
      num_preds_per_question=10,
      subsampling_rounds=10,
      subsampling_iter_per_round=3,
      tracked_pred_attrs=['net_runtime'],
      include_outcome_pct=True)

  assert len(q_results) == 2
  assert len(p_results) == 17

  assert all(f'estimate_pass@{k}' in result_metrics for k in [1, 10, 15])
  assert all(f'subsampling_pass@{k}' in result_metrics for k in [1, 10, 15])
  for k_val in [1, 10]:
    assert isinstance(result_metrics[f'subsampling_pass@{k_val}_var'], float)

  for k in [1, 10, 15]:
    del result_metrics[f'estimate_pass@{k}']
    del result_metrics[f'subsampling_pass@{k}']
    del result_metrics[f'subsampling_pass@{k}_var']

  expected_net_metrics = {
      'num_predictions': 17,
      'questions_passed': 1,
      'num_questions': 2,
      'total_runtime': '0:12:34',
      'questions_passed_pct': 50.0,
      'Passed': 5,
      'Timed Out': 0,
      'Had Error': 7,
      'Had Runtime Error': 0,
      'Failed Tests': 5
  }
  for k in result_types.PredictionOutcome:

    if k == result_types.PredictionOutcome.PASSED:
      continue
    expected_pct = expected_net_metrics[str(k)] / len(p_results) * 100
    assert f'{k}_pct' in result_metrics
    assert math.isclose(result_metrics.pop(f'{k}_pct'),
                        expected_pct), f'{k}_pct'

  assert result_metrics == expected_net_metrics


def test_calculate_question_aggregate_metrics():
  """Tests calculating aggregate metrics for questions."""
  question_0_results = QuestionResult('0',
                                      'Python',
                                      num_test_cases=3,
                                      num_predictions=3)
  for outcome in PredictionOutcome:
    bool_arr = [False] * 3
    if outcome == PredictionOutcome.HAD_ERROR:
      bool_arr = [False, False, True]
    elif outcome == PredictionOutcome.PASSED:
      bool_arr = [True, False, False]
    elif outcome == PredictionOutcome.TIMED_OUT:
      bool_arr = [False, True, False]
    question_0_results.results[outcome] = bool_arr

  question_0_results.results['net_runtime'] = [1.0, None, None]
  question_0_results.results['num_tc_passed'] = [3, 0, 0]
  question_0_results.specific_test_results = {
      '1': {
          'FAILED': 1,
          'PASSED': 2,
          'MISSING': 3
      },
      '2': {
          'MISSING': 5
      }
  }

  question_1_results = QuestionResult('1',
                                      'Python',
                                      num_test_cases=3,
                                      num_predictions=3)
  for outcome in PredictionOutcome:
    bool_arr = [False] * 3
    if outcome == PredictionOutcome.FAILED_TEST:
      bool_arr = [False, True, True]
    elif outcome == PredictionOutcome.HAD_ERROR:
      bool_arr = [True, False, False]
    question_1_results.results[outcome] = bool_arr

  question_1_results.results['net_runtime'] = [1.0, 2.0, 3.0]
  question_1_results.results['num_tc_passed'] = [0, 1, 2]
  question_1_results.specific_test_results = {
      '1': {
          'FAILED': 1,
          'PASSED': 2,
          'MISSING': 3
      }
  }

  question_result_dict = {'0': question_0_results, '1': question_1_results}

  net_metrics, q_metrics = metrics.calculate_question_aggregate_metrics(
      question_result_dict, ['net_runtime'])

  expected_keys = [str(outcome) for outcome in PredictionOutcome]
  expected_keys += [
      'num_predictions', 'questions_passed', 'num_questions',
      'questions_passed_pct'
  ]
  assert len(q_metrics) == 2
  assert set(net_metrics) == set(expected_keys)

  assert net_metrics == {
      'num_predictions': 6,
      'questions_passed': 1,
      'num_questions': 2,
      'questions_passed_pct': 50.0,
      'Passed': 1,
      'Timed Out': 1,
      'Had Error': 2,
      'Had Runtime Error': 0,
      'Failed Tests': 2,
  }
  q_metrics = list(sorted(q_metrics, key=lambda x: x['qid']))
  assert q_metrics[0] == {
      'qid': '0',
      'language': 'Python',
      'num_predictions': 3,
      'Had Error': 1,
      'Passed': 1,
      'Timed Out': 1,
      'Had Runtime Error': 0,
      'Failed Tests': 0,
      'net_runtime_mean': 1.0,
      'net_runtime_median': 1.0,
      'num_tc_passed_mean': 3.0,
      'num_tc_passed_median': 3.0,
      'num_passed_N_total_tests': {
          '0': 2,
          '1': 0,
          '2': 0,
          '3': 1
      },
      'num_results_by_test': {
          '1': {
              'FAILED': 1,
              'PASSED': 2,
              'MISSING': 3
          },
          '2': {
              'MISSING': 5
          }
      }
  }
  assert q_metrics[1] == {
      'qid': '1',
      'language': 'Python',
      'num_predictions': 3,
      'Had Error': 1,
      'Passed': 0,
      'Timed Out': 0,
      'Had Runtime Error': 0,
      'Failed Tests': 2,
      'net_runtime_mean': None,
      'net_runtime_median': None,
      'num_tc_passed_mean': None,
      'num_tc_passed_median': None,
      'num_passed_N_total_tests': {
          '0': 1,
          '1': 1,
          '2': 1,
          '3': 0
      },
      'num_results_by_test': {
          '1': {
              'FAILED': 1,
              'PASSED': 2,
              'MISSING': 3
          }
      }
  }


def test_calculate_pass_metrics():
  """Tests calculating the pass@k metrics."""
  question_0_results = QuestionResult('0',
                                      'Python',
                                      num_test_cases=3,
                                      num_predictions=4)
  for outcome in PredictionOutcome:
    bool_arr = [False] * 4
    if outcome == PredictionOutcome.HAD_ERROR:
      bool_arr = [False, False, True, False]
    elif outcome == PredictionOutcome.PASSED:
      bool_arr = [True, False, False, False]
    elif outcome == PredictionOutcome.TIMED_OUT:
      bool_arr = [False, True, False, False]
    question_0_results.results[outcome] = bool_arr

  question_0_results.results['net_runtimes'] = [1.0, None, None]
  question_0_results.results['num_tc_passed'] = [3, 0, 0]

  question_1_results = QuestionResult('1',
                                      'Python',
                                      num_test_cases=3,
                                      num_predictions=3)
  for outcome in PredictionOutcome:
    bool_arr = [False] * 3
    if outcome == PredictionOutcome.FAILED_TEST:
      bool_arr = [False, True, True]
    elif outcome == PredictionOutcome.HAD_ERROR:
      bool_arr = [True, False, False]
    question_1_results.results[outcome] = bool_arr

  question_1_results.results['net_runtimes'] = [1.0, 2.0, 3.0]
  question_1_results.results['num_tc_passed'] = [0, 1, 2]

  question_result_dict = {'0': question_0_results, '1': question_1_results}

  result = metrics.calculate_pass_metrics(question_result_dict,
                                          seed=1,
                                          k_vals=[1, 10],
                                          num_preds_per_question=4,
                                          subsampling_rounds=10,
                                          subsampling_iter_per_round=4,
                                          shuffle=True)

  assert result == {
      'estimate_pass@1': 12.5,
      'subsampling_pass@1': 8.75,
      'estimate_pass@10': None,
      'subsampling_pass@10': None,
      'subsampling_pass@1_var': 360.9375,
      'subsampling_pass@10_var': None
  }
