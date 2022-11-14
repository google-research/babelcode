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
"""Result Data Types."""
import collections
import dataclasses
import enum
import re
from typing import Any, Dict, List, Optional, Union

from babelcode.data_types.command import Command
from babelcode.data_types.prediction import Prediction


class PredictionOutcome(enum.Enum):
  """Enum for holding potential outcomes for a prediction."""
  PASSED = 'Passed'
  NO_STDOUT = 'No STDOut'
  TIMED_OUT = 'Timed Out'
  HAD_ERROR = 'Had Error'
  HAD_RUNTIME_ERROR = 'Had Runtime Error'
  FAILED_TEST = 'Failed Tests'

  def __str__(self) -> str:
    return self.value


@dataclasses.dataclass()
class ExecutionResult:
  """execution_result of executing a file."""
  prediction: Prediction
  commands: List[Command]
  stdout: str
  stderr: str
  return_code: int
  net_runtime: Optional[float]
  last_ran_command_idx: int
  command_runtimes: List[Optional[float]]
  command_memory: List[Optional[int]]
  had_error: bool = False
  timed_out: bool = False
  all_commands_ran: bool = False

  def to_dict(self):
    self_dict = dataclasses.asdict(self)
    # Need to do special serialization of Prediction.
    self_dict.pop('prediction')

    return {**self.prediction.to_dict(), **self_dict}

  def __post_init__(self):
    self.all_commands_ran = self.last_ran_command_idx + 1 == len(self.commands)


GET_TC_REGEX = re.compile(r'^TEST-(.+)\.\.\.(.+)$', flags=re.MULTILINE)


@dataclasses.dataclass
class PredictionResult:
  """Parsed result of a prediction."""
  qid: str
  id: str
  lang: str
  code: str
  outcome: PredictionOutcome
  test_case_results: Dict[str, str]
  num_tc_passed: int
  num_tc: int
  all_commands_ran: bool
  final_command_runtime: float
  final_command_memory: int
  net_runtime: Optional[float]
  command_runtimes: List[Optional[float]]
  command_memory: List[Optional[int]]
  stderr: str

  @classmethod
  def from_execution_result(
      cls, execution_result: ExecutionResult,
      question_info: Dict[str, Any]) -> 'PredictionResult':
    """Create a prediction execution_result from an Execution Result.

    Args:
      execution_result: The execution execution_result dict.
      question_info: The question information.

    Returns:
      A new PredictionResult
    """

    outcome = PredictionOutcome.PASSED
    if execution_result.return_code != 0:
      outcome = PredictionOutcome.HAD_ERROR
    elif execution_result.had_error:
      outcome = PredictionOutcome.HAD_ERROR
    elif execution_result.stderr:
      outcome = PredictionOutcome.HAD_ERROR
    elif execution_result.timed_out:
      outcome = PredictionOutcome.TIMED_OUT
    elif not execution_result.stdout:
      outcome = PredictionOutcome.NO_STDOUT
    test_cases_results = {}
    failed_a_test_case = False
    missing_test_case = False
    had_runtime_error = False
    num_passed = 0
    for match in GET_TC_REGEX.findall(execution_result.stdout):
      idx, test_result = match
      if idx in question_info['test_case_ids']:
        test_cases_results[idx] = test_result

    for tid in question_info['test_case_ids']:
      tc_result = test_cases_results.get(tid, 'MISSING')
      if tc_result == 'MISSING':
        test_cases_results[tid] = 'MISSING'
        missing_test_case = True
      elif tc_result == 'FAILED':
        failed_a_test_case = True
      elif tc_result != 'PASSED':
        had_runtime_error = True
      else:
        num_passed += 1

    if outcome == PredictionOutcome.PASSED:
      # We only ever need to add in 'MISSING' if there was an error for some
      # reason.
      if missing_test_case:
        outcome = PredictionOutcome.HAD_ERROR

      elif had_runtime_error:
        outcome = PredictionOutcome.HAD_RUNTIME_ERROR

      elif failed_a_test_case:
        # We only want to do more fail checking in the case that we do not
        # already have a failure.
        outcome = PredictionOutcome.FAILED_TEST

    last_command = execution_result.last_ran_command_idx
    last_runtime = execution_result.command_runtimes[last_command]
    last_memory_used = execution_result.command_memory[last_command]

    return cls(qid=execution_result.prediction.qid,
               id=execution_result.prediction.id,
               lang=execution_result.prediction.lang,
               code=execution_result.prediction.code,
               outcome=outcome,
               test_case_results=test_cases_results,
               num_tc_passed=num_passed,
               num_tc=len(test_cases_results),
               all_commands_ran=execution_result.all_commands_ran,
               net_runtime=execution_result.net_runtime,
               stderr=execution_result.stderr,
               command_runtimes=execution_result.command_runtimes,
               command_memory=execution_result.command_memory,
               final_command_runtime=last_runtime,
               final_command_memory=last_memory_used)

  def to_dict(self):
    out = dataclasses.asdict(self)
    out['language'] = out.pop('lang')
    # For json conversion later.
    out['outcome'] = out['outcome'].value
    return out


RESERVED_ATTRIBUTES = [
    'num_tc_passed',
    'outcome',
    'test_case_results',
]


@dataclasses.dataclass
class QuestionResult:
  """Class to hold aggregate results for a single question.

  Attributes:
    id: The question id this is for.
    lang: The language this is for.
    num_test_cases: The number of test cases in the question.
    num_predictions: The number of predictions for seen.
    tracked_attributes: The attributes of PredictionResult to track.
    specific_test_results: The counters for each test case.
    results: The overall aggregate results.
  """
  id: str
  lang: str
  num_test_cases: int
  num_predictions: int = 0
  tracked_attributes: List[str] = dataclasses.field(default_factory=list)
  specific_test_results: Dict[str, Dict[str, int]] = dataclasses.field(
      default_factory=lambda: collections.defaultdict(collections.Counter))
  results: Dict[str, List[int]] = dataclasses.field(
      default_factory=lambda: collections.defaultdict(list))

  def __post__init__(self) -> None:
    """Remove reserved attrs from those tracked."""
    for k in RESERVED_ATTRIBUTES:
      if k in self.tracked_attributes:
        self.tracked_attributes.remove(k)

  def __len__(self) -> int:
    """Gets the number of predictions."""
    return self.num_predictions

  def get_vals_for_idx(self, idx: int) -> Dict[str, Any]:
    """Gets the results for an prediction idx."""
    out = {}
    for m, v in self.results.items():
      try:
        out[m] = v[idx]
      except IndexError as e:
        raise IndexError(f'Result {m} had index error with {idx=}') from e
    return out

  def update_with_result(self, pred_result: PredictionResult) -> None:
    """Updates the Question result with a prediction result.

    Args:
      pred_result: The prediciton result to add.
    """
    self.num_predictions += 1
    for outcome in PredictionOutcome:
      self.results[outcome].append(pred_result.outcome == outcome)

    for attr_name in self.tracked_attributes:
      self.results[attr_name].append(getattr(pred_result, attr_name))

    self.results['num_tc_passed'].append(pred_result.num_tc_passed)

    for test_idx in range(self.num_test_cases):
      test_result = pred_result.test_case_results.get(str(test_idx), 'MISSING')
      self.specific_test_results[str(test_idx)][test_result] += 1

  def count_result(self, name: Union[str, PredictionOutcome]) -> int:
    """Gets the number of results with name."""
    return sum(self.results[name])

  def has_result(self, name: Union[str, PredictionOutcome]) -> bool:
    """Checks if there is a result with the name."""
    return bool(self.count_result(name))

  def padded(self, name: Union[str, PredictionOutcome], max_len: int,
             value: Any) -> List[Any]:
    """Pads the result with a value.

    Args:
      name: The name of the result to pad.
      max_len: The length to pad too.
      value: The value to pad with.

    Returns:
    """
    return self.results[name] + [
        value for _ in range(max_len - self.num_predictions)
    ]

  @classmethod
  def from_pred_results(cls, qid: str, lang: str, num_test_cases: int,
                        pred_result_list: List[PredictionResult],
                        tracked_attributes: List[str]) -> 'QuestionResult':
    """Create a QuestionResult from a list of pred results.

    Args:
        qid: The question id.
        lang: The language.
        num_test_cases: The number of test cases for the question.
        pred_result_list: The list of prediction results.
        tracked_attributes: The list of attributes of PredictionResult to track.

    Returns:
        The question result object.
    """
    out = cls(id=qid,
              lang=lang,
              num_test_cases=num_test_cases,
              tracked_attributes=tracked_attributes)
    # Update the results with the list of pred results.
    for pred_result in pred_result_list:
      out.update_with_result(pred_result=pred_result)

    return out
