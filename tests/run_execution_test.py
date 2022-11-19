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

"""Tests for run_execution."""
from babelcode import run_execution
from babelcode.data_types.prediction import Prediction
from babelcode.languages import LanguageRegistry


def test_setup_language_code_dirs(tmp_path):
  preds = [{
      'id': '1',
      'qid': '1',
      'code': 'Pred 1.1',
      'entry_fn_name': 'testd'
  }, {
      'id': '2',
      'qid': '1',
      'code': 'Pred 1.2',
      'entry_fn_name': 'tesrt'
  }, {
      'id': '1',
      'qid': '2',
      'code': 'Pred 2.1',
      'entry_fn_name': 'teqst',
  }, {
      'id': '1',
      'qid': '10',
      'code': 'Pred 10.1',
      'entry_fn_name': 'tsest'
  }]
  preds = {f'{v["qid"]}_{v["id"]}': v for v in preds}
  questions = {
      '1': {
          'qid': 1,
          'test_code': 'Question 1 PLACEHOLDER_CODE_BODY PLACEHOLDER_FN_NAME',
          'entry_fn_name': 'test',
          'entry_cls_name': 'Solution'
      },
      '2': {
          'qid': '2',
          'test_code': 'Question 2 PLACEHOLDER_CODE_BODY PLACEHOLDER_FN_NAME',
          'entry_fn_name': 'test',
          'entry_cls_name': 'Solution'
      },
      '3': {
          'qid': 3,
          'test_code': 'Question 3 PLACEHOLDER_CODE_BODY PLACEHOLDER_FN_NAME',
          'entry_fn_name': 'test',
          'entry_cls_name': 'Solution'
      }
  }

  out_path = tmp_path.joinpath('out')
  out_path.mkdir()

  result = run_execution.setup_language_code_dirs(
      out_path, LanguageRegistry.get_language('C++'), preds, questions, True)

  expected_1 = Prediction('1',
                          '1',
                          'C++',
                          'Pred 1.1',
                          out_path.joinpath('1_1', '1_1.cpp'),
                          entry_fn_name='test')
  expected_2 = Prediction('2',
                          '1',
                          'C++',
                          'Pred 1.2',
                          out_path.joinpath('1_2', '1_2.cpp'),
                          entry_fn_name='test')
  expected_3 = Prediction('1',
                          '2',
                          'C++',
                          'Pred 2.1',
                          out_path.joinpath('2_1', '2_1.cpp'),
                          entry_fn_name='test')
  expected = {
      '1/1': {
          'prediction': expected_1,
          'full_code': 'Question 1 Pred 1.1 test'
      },
      '1/2': {
          'prediction': expected_2,
          'full_code': 'Question 1 Pred 1.2 test'
      },
      '2/1': {
          'prediction': expected_3,
          'full_code': 'Question 2 Pred 2.1 test'
      }
  }
  assert result == expected

  for v in expected.values():
    assert v['prediction'].file_path.exists()
    contents = v['prediction'].file_path.read_text()
    assert contents == v['full_code']
