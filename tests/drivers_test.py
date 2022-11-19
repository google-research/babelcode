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
      mock_generate.return_value = ('MOCK_QUESTION', 'MOCK_PROMPT')

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
