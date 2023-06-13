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
"""Test configuration module."""

# Because of how pytest fixtures work, this error will be incorrectly triggered,
# so disable it for the file here. Pytest Fixture docs:
# https://docs.pytest.org/en/6.2.x/fixture.html
# pylint:disable=redefined-outer-name

import json
import pathlib
import shutil

import pytest

from babelcode import data_types
from babelcode.data_types.prediction import Prediction
from babelcode.schema_parsing.schema_type import SchemaType
from babelcode.utils import FIXTURES_PATH


@pytest.fixture()
def code_dir():
  """Code directory fixture."""
  yield FIXTURES_PATH.joinpath('code')


@pytest.fixture()
def py_failing(code_dir):
  """Failing Python Program fixture."""
  yield code_dir.joinpath('failing.py')


@pytest.fixture()
def py_passing(code_dir):
  """Passing Python Program fixture."""
  yield code_dir.joinpath('passing.py')


@pytest.fixture
def sample_execution_results():
  """Sample execution results fixture."""
  sample_file = FIXTURES_PATH.joinpath('sample_prediction_results.jsonl')
  out = []
  for line in map(json.loads, sample_file.open()):
    stdout_str = '\n'.join(
        f'TEST-{i}...{v}' for i, v in enumerate(line['test_results']))
    pred_id = str(line['id'])
    qid = str(line['qid'])
    fp = pathlib.Path(f'{qid}_{id}.test')
    pred_info = Prediction(id=pred_id, qid=qid, lang=line['lang'], file_path=fp)
    had_error = len(line['stderr']) > 0  # pylint:disable=g-explicit-length-test
    out.append(
        dict(
            prediction=pred_info.to_dict(),
            commands=['testing'],
            stdout=stdout_str,
            stderr=line['stderr'],
            return_code=1 if had_error else 0,
            net_runtime=line['net_runtime'],
            command_runtimes=line['command_runtimes'],
            last_ran_command_idx=0,
            had_error=had_error,
        ))
  yield out


@pytest.fixture
def sample_question_info():
  """Sample question info fixture."""
  yield json.loads(FIXTURES_PATH.joinpath('sample_questions.json').read_text())


@pytest.fixture()
def sample_schema():
  """Sample schema fixture."""
  yield {
      'arg0':
          SchemaType.from_generic_type_string('list<list<string>>'),
      'arg1':
          SchemaType.from_generic_type_string('boolean'),
      data_types.EXPECTED_KEY_NAME:
          SchemaType.from_generic_type_string('integer'),
  }


@pytest.fixture()
def passing_prediction(tmp_path, py_passing):
  pass_path = tmp_path.joinpath('passing')
  pass_path.mkdir(parents=True)
  tmp_file = pass_path.joinpath(py_passing.name)
  shutil.copyfile(py_passing, tmp_file)
  yield Prediction('1',
                   'PASS',
                   'Python',
                   code=py_passing.read_text(),
                   file_path=tmp_file)


@pytest.fixture()
def failing_prediction(tmp_path, py_failing):
  fail_path = tmp_path.joinpath('failing')
  fail_path.mkdir(parents=True)
  tmp_file = fail_path.joinpath(py_failing.name)
  shutil.copyfile(py_failing, tmp_file)

  yield Prediction('1',
                   'FAIL',
                   'Python',
                   code=py_failing.read_text(),
                   file_path=tmp_file)
