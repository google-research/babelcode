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

"""Tests for the prediction data type."""
import pathlib

from babelcode import data_types


class TestPrediction:
  """Tests for the prediction data type."""

  def test_prediction_from_dict(self):
    """Tests loading a prediction from a dictionary."""
    file_path = pathlib.Path('test.py')
    input_dict = {
        'id': 1,
        'qid': 2,
        'code': 'Prediction code',
        'entry_fn_name': 'test_fn',
        'entry_cls_name': 'test_cls'
    }

    result = data_types.Prediction.from_dict(pred_dict=input_dict,
                                             file_path=file_path,
                                             default_language='vba')

    assert result == data_types.Prediction(id='1',
                                           qid='2',
                                           code='Prediction code',
                                           entry_fn_name='test_fn',
                                           entry_cls_name='test_cls',
                                           lang='vba',
                                           file_path=file_path)

  def test_prediction_to_dict(self):
    """Test `to_dict()`."""
    result = data_types.Prediction(id='1',
                                   qid='2',
                                   code='Prediction code',
                                   entry_fn_name='test_fn',
                                   entry_cls_name='test_cls',
                                   lang='vba',
                                   file_path=pathlib.Path('test.py')).to_dict()

    assert result == {
        'id': '1',
        'qid': '2',
        'code': 'Prediction code',
        'entry_fn_name': 'test_fn',
        'entry_cls_name': 'test_cls',
        'lang': 'vba',
        'file_path': str(pathlib.Path('test.py').resolve().absolute())
    }
