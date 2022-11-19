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


"""Tests the execution functions."""
import json
import os
import shutil

from babelcode import execution
from babelcode.data_types.command import Command
from babelcode.data_types.prediction import Prediction
from babelcode.languages import LanguageRegistry
import pytest


def setup_module(_):
  """Setup the environment so execution is allowed."""
  os.environ['ALLOW_EXECUTION'] = 'true'


def teardown_module(_):
  """Disable execution on teardown."""
  os.environ['ALLOW_EXECUTION'] = 'true'


def make_python_commands(file_path):
  return [Command(['python', file_path.name])]


@pytest.fixture()
def passing_prediction(tmp_path, py_passing):
  pass_path = tmp_path.joinpath('passing')
  pass_path.mkdir(parents=True)
  tmp_file = pass_path.joinpath(py_passing.name)
  shutil.copyfile(py_passing, tmp_file)
  yield Prediction(
      '1', 'PASS', 'Python', code=py_passing.read_text(), file_path=tmp_file
  )


@pytest.fixture()
def failing_prediction(tmp_path, py_failing):
  fail_path = tmp_path.joinpath('failing')
  fail_path.mkdir(parents=True)
  tmp_file = fail_path.joinpath(py_failing.name)
  shutil.copyfile(py_failing, tmp_file)

  yield Prediction(
      '1', 'FAIL', 'Python', code=py_failing.read_text(), file_path=tmp_file
  )


def test_execute_code_ran(passing_prediction):
  result = execution.execute_code(
      prediction=passing_prediction,
      commands=make_python_commands(passing_prediction.file_path),
  )

  assert result.prediction == passing_prediction
  assert result.return_code == 0
  assert not result.stderr
  assert result.stdout == 'This should be printed\n'
  assert result.last_ran_command_idx == 0
  assert not result.had_error
  assert not result.timed_out
  assert result.all_commands_ran


def test_execute_code_fail(failing_prediction):
  result = execution.execute_code(
      prediction=failing_prediction,
      commands=make_python_commands(failing_prediction.file_path),
  )
  assert result.prediction == failing_prediction
  assert result.return_code == 1
  assert 'This should fail!' in result.stderr
  assert not result.stdout
  assert result.last_ran_command_idx == 0
  assert result.had_error
  assert not result.timed_out
  assert result.all_commands_ran


@pytest.mark.parametrize('num_workers', [1, 2], ids=['Single', 'Parallel'])
def test_execute_predictions(
    num_workers, passing_prediction, failing_prediction, tmp_path
):
  prediction_list = [
      passing_prediction,
      failing_prediction,
      passing_prediction,
      failing_prediction,
  ]
  with execution.time_limit(3):
    results, runtime = execution.execute_predictions(
        prediction_list,
        LanguageRegistry.get_language('Python'),
        tmp_path,
        num_workers,
        update_freq=1,
    )

  debug_results = list(
      map(json.loads, tmp_path.joinpath('Python_runtime_tracking.jsonl').open())
  )
  assert len(debug_results) == 4
  assert [d['completed'] for d in debug_results] == [1, 2, 3, 4]

  execution_results = list(
      map(
          json.loads, tmp_path.joinpath('Python_execution_results.jsonl').open()
      )
  )

  assert len(execution_results) == 4
  result = []
  for i, d in enumerate(results):
    assert d.to_dict() == execution_results[i]

    result.append((d.prediction.id, d.had_error, d.return_code))

  assert set(result) == {
      (passing_prediction.id, False, 0),
      (failing_prediction.id, True, 1),
      (passing_prediction.id, False, 0),
      (failing_prediction.id, True, 1),
  }
  assert isinstance(runtime, str)
  assert runtime.count(':') == 2
