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

"""Tests for code_generator.py."""
# Because of how pytest fixtures work, this error will be incorrectly triggered,
# so disable it for the file here. Pytest Fixture docs:
# https://docs.pytest.org/en/6.2.x/fixture.html
# pylint:disable=redefined-outer-name

import math
import pathlib

import pytest  # pylint: disable=unused-import

from babelcode import code_generator
from babelcode import data_types
from babelcode import schema_parsing

SchemaType = schema_parsing.SchemaType


@pytest.mark.parametrize('schema_type',
                         ['float', 'double', 'list<float>', 'string'])
def test_determine_question_requirements(schema_type):
  """Tests determing question specific requirements."""
  double_precision = 1e-10
  float_precision = 1e-5
  question = data_types.Question(qid='0',
                                 schema=[{
                                     'name': 'arg0',
                                     'type': schema_type
                                 }, {
                                     'name': 'expected',
                                     'type': schema_type
                                 }],
                                 title='testing',
                                 test_list=[],
                                 entry_fn_name='test')

  schema = {
      'arg0': SchemaType.from_generic_type_string(schema_type),
      'expected': SchemaType.from_generic_type_string(schema_type),
  }

  result = code_generator._determine_question_requirements(
      question,
      schema,
      double_precision=double_precision,
      float_precision=float_precision)

  if schema_type == 'float':
    assert math.isclose(result['precision'], float_precision)
    assert result['evaluation_method'] == 'float'
    assert result['use_float']
  elif schema_type == 'double':

    assert math.isclose(result['precision'], double_precision)
    assert result['evaluation_method'] == 'float'
    assert not result['use_float']
  else:
    assert result['evaluation_method'] == 'default'


def test_load_template_map(tmp_path: pathlib.Path):
  """Tests the loading of templates."""
  template_map = {
      'HEADER': 'header.txt',
      'MAIN': 'main.txt',
      'EVALUATION': 'evaluation.txt',
  }

  for k in template_map:
    template_map[k] = tmp_path.joinpath(template_map[k])
    with template_map[k].open('w') as f:
      f.write(f'{k}: ' + '{{inputs}}')

  result_map = code_generator.load_template_map(template_map)

  assert set(result_map.keys()) == {'HEADER', 'MAIN', 'EVALUATION'}
  for k, template in result_map.items():
    result = template.render(inputs='testing')
    assert result == f'{k}: testing'
