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

"""Tests for the driver functions."""
from unittest import mock
import pathlib
import json

from babelcode import code_generator
from babelcode import data_types
from babelcode import drivers
from babelcode import languages
import pytest  # pylint: disable=unused-import


def test_generate_code_for_questions(sample_question_info):
  language = languages.LanguageRegistry.get_language('Python')
  questions = [
      data_types.Question.from_dict(d) for d in sample_question_info.values()
  ]

  with mock.patch(
      'babelcode.schema_parsing.parse_schema_and_input_order'
  ) as mock_parse_schema:
    mock_parse_schema.return_value = ('MOCK_SCHEMA', 'MOCK_INPUT_ORDER')
    with mock.patch(
        'babelcode.drivers._generate_question_code'
    ) as mock_generate:
      mock_generate.return_value = 'MOCK_QUESTION'
      with mock.patch('babelcode.drivers.generate_prompt_info') as mock_prompt:
        mock_prompt.return_value = 'MOCK_PROMPT'
        result, result_failures = drivers.generate_code_for_questions(
            questions, language
        )
        assert len(result) == 3
        assert all(r == ('MOCK_QUESTION', 'MOCK_PROMPT') for r in result)
        assert not result_failures
        assert mock_generate.call_count == len(questions)
        for i, mock_call_args in enumerate(mock_generate.call_args_list):
          call_kwargs = mock_call_args.kwargs
          assert set(call_kwargs.keys()) == {
              'question',
              'schema',
              'input_order',
              'literal_translator',
              'template_map',
              'prompt_translator',
          }
          assert call_kwargs['question'] == questions[i]
          assert call_kwargs['schema'] == 'MOCK_SCHEMA'
          assert call_kwargs['input_order'] == 'MOCK_INPUT_ORDER'

    assert mock_parse_schema.call_count == len(questions)
    assert all(
        v.kwargs['raw_schema'] == questions[i].schema
        for i, v in enumerate(mock_parse_schema.call_args_list)
    )


def test_generate_prompt_info():
  question = data_types.Question(
      '1',
      schema={
          'params': [
              {'name': 'scooby', 'type': 'integer'},
          ],
          'return': {'type': 'string'},
      },
      test_list=[{
          'idx': 0,
          'inputs': {'scooby': 1},
          'outputs': 'test',
      }],
      entry_fn_name='entry',
      entry_cls_name='Solution',
      title='Test',
      use_type_annotation=True,
      text='Testing the C++ Question Prompts for entry',
  )
  lang = languages.LanguageRegistry.get_language('Python')
  prompt_translator = lang.make_prompt_translator()
  template_map = code_generator.load_template_map(lang.make_template_map())
  result = drivers.generate_prompt_info(
      question,
      language=lang,
      prompt_translator=prompt_translator,
      template_map=template_map,
      force_type_annotations=False,
      obfuscation_fn=code_generator.naive_obfuscation,
  )

  assert set(result.keys()) == {
      'qid',
      'arguments',
      'signature',
      'signature_with_docstring',
      'text',
      'header',
      'entry_fn_name',
      'entry_cls_name',
  }

  assert result['qid'] == question.qid
  assert result['signature'] == 'def model_prediction(arg0: int) -> str:'
  assert (
      result['text'] == 'Testing the C++ Question Prompts for model_prediction'
  )
  assert result['entry_fn_name'] == 'model_prediction'
  assert result['entry_cls_name'] == 'Prediction'


def test_setup_language_code_dirs(tmp_path):
  preds = [
      {'id': '1', 'qid': '1', 'code': 'Pred 1.1', 'entry_fn_name': 'testd'},
      {'id': '2', 'qid': '1', 'code': 'Pred 1.2', 'entry_fn_name': 'tesrt'},
      {
          'id': '1',
          'qid': '2',
          'code': 'Pred 2.1',
          'entry_fn_name': 'teqst',
      },
      {'id': '1', 'qid': '10', 'code': 'Pred 10.1', 'entry_fn_name': 'tsest'},
  ]
  preds = {f'{v["qid"]}/{v["id"]}': v for v in preds}
  questions = {
      '1': {
          'qid': 1,
          'test_code': 'Question 1 PLACEHOLDER_CODE_BODY PLACEHOLDER_FN_NAME',
          'entry_fn_name': 'test',
          'entry_cls_name': 'Solution',
      },
      '2': {
          'qid': '2',
          'test_code': 'Question 2 PLACEHOLDER_CODE_BODY PLACEHOLDER_FN_NAME',
          'entry_fn_name': 'test',
          'entry_cls_name': 'Solution',
      },
      '3': {
          'qid': 3,
          'test_code': 'Question 3 PLACEHOLDER_CODE_BODY PLACEHOLDER_FN_NAME',
          'entry_fn_name': 'test',
          'entry_cls_name': 'Solution',
      },
  }

  out_path = tmp_path.joinpath('out')
  out_path.mkdir()

  result = drivers.setup_language_code_dirs(
      out_path,
      languages.LanguageRegistry.get_language('C++'),
      preds,
      questions,
      True,
  )

  expected_1 = data_types.Prediction(
      '1',
      '1',
      'C++',
      'Pred 1.1',
      out_path.joinpath('1_1', '1_1.cpp'),
      entry_fn_name='test',
  )
  expected_2 = data_types.Prediction(
      '2',
      '1',
      'C++',
      'Pred 1.2',
      out_path.joinpath('1_2', '1_2.cpp'),
      entry_fn_name='test',
  )
  expected_3 = data_types.Prediction(
      '1',
      '2',
      'C++',
      'Pred 2.1',
      out_path.joinpath('2_1', '2_1.cpp'),
      entry_fn_name='test',
  )
  expected = {
      '1/1': expected_1,
      '1/2': expected_2,
      '2/1': expected_3,
  }
  assert result == expected

  for v in expected.values():
    assert v.file_path.exists()
    contents = v.file_path.read_text()
    assert v.code in contents


def test_load_progress_from_dir(tmp_path: pathlib.Path):
  """Tests the loading of progress from a directory."""

  with tmp_path.joinpath('test.jsonl').open('w') as f:
    f.write('This should not appear!')

  cpp_execution_result = data_types.ExecutionResult(
      data_types.Prediction(
          qid='2',
          id='1',
          lang='C++',
          code='cpp_code',
          file_path=pathlib.Path('1.cpp').resolve().absolute(),
      ),
      commands=[data_types.Command('test command')],
      stdout='',
      stderr='Test Stderr',
      net_runtime=0.1,
      command_runtimes=[None],
      command_memory=[None],
      return_code=1,
      last_ran_command_idx=0,
  )

  with tmp_path.joinpath('C++_execution_results.jsonl').open('w') as f:
    f.write(json.dumps(cpp_execution_result.to_dict()) + '\n')

  py_execution_result = data_types.ExecutionResult(
      data_types.Prediction(
          qid='2',
          id='1',
          lang='Python',
          code='cpp_code',
          file_path=pathlib.Path('1.cpp').resolve().absolute(),
      ),
      commands=[data_types.Command('test command')],
      stdout='',
      stderr='Test Stderr',
      net_runtime=0.1,
      command_runtimes=[None],
      command_memory=[None],
      return_code=1,
      last_ran_command_idx=0,
  )
  with tmp_path.joinpath('Python_execution_results.jsonl').open('w') as f:
    f.write(json.dumps(py_execution_result.to_dict()) + '\n')

  result = drivers.load_progress_from_dir(tmp_path)

  expected = {
      'Python': {'2/1': py_execution_result},
      'C++': {'2/1': cpp_execution_result},
  }
  assert result == expected


@pytest.mark.parametrize(
    'with_progress', [True, False], ids=['With Progress', 'No Progress']
)
def test_run_execution_for_lang(tmp_path, passing_prediction, with_progress):
  language = languages.LanguageRegistry.get_language('Python')

  def _make_pred(qid, id):
    p_dict = passing_prediction.to_dict()
    p_dict['qid'] = qid
    p_dict['id'] = id
    return data_types.Prediction.from_dict(
        p_dict, passing_prediction.file_path, language.name
    )

  question_mapping = {'1': {'title': 'Test Question'}}
  preds = {
      '1/1': _make_pred('1', '1'),
      '1/2': _make_pred('1', '2'),
      '2/1': _make_pred('2', '1'),
  }

  expected_process_input_results = set(preds.keys())
  progress = {}
  if with_progress:
    progress = {'1/2': preds.pop('1/2')}
  with mock.patch(
      'babelcode.drivers.setup_language_code_dirs'
  ) as mock_setup_dirs:
    mock_setup_dirs.return_value = {
        k: {'prediction': v, 'full_code': None} for k, v in preds.items()
    }
    with mock.patch('babelcode.execution.execute_predictions') as mock_execute:
      mock_execute.return_value = (list(preds.values()), '1:1:1')
      with mock.patch('babelcode.drivers._process_results') as mock_process:
        mock_process.return_value = ['A', 'B']
        result = drivers.run_execution_for_lang_predictions(
            lang=language,
            question_mapping=question_mapping,
            raw_predictions={**preds, **progress},
            debug_dir_path=tmp_path,
            output_path=tmp_path,
            executed_predictions=progress,
            seed=1,
            step=1,
            force_question_entry=False,
        )

        assert result == ['A', 'B']

        passed_results = mock_process.call_args_list[0].kwargs['raw_results']
        actual_ids = {f'{result.qid}/{result.id}' for result in passed_results}
        assert set(
            mock_setup_dirs.call_args_list[0].kwargs['predictions']
        ) == set(preds.keys())
        assert actual_ids == expected_process_input_results
        assert mock_execute.call_count == 1
        assert mock_process.call_count == 1
        assert mock_setup_dirs.call_count == 1
