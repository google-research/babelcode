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

"""Testing each execution in each language."""
import os

from babelcode import code_generator
from babelcode.data_types.prediction import Prediction
from babelcode.data_types.question import Question
from babelcode import data_types
from babelcode.execution import execute_code
from babelcode.schema_parsing import parsing
from tests import utils as testing_utils
import pytest


def setup_module(_):
  """Setup the environment so execution is allowed."""
  os.environ['ALLOW_EXECUTION'] = 'true'


def teardown_module(_):
  """Disable execution on teardown."""
  os.environ['ALLOW_EXECUTION'] = 'true'


@pytest.mark.parametrize('lang_name', testing_utils.LANGS_TO_TEST)
class TestLanguageExecution(testing_utils.BaseLanguageTestingClass):
  """Unit-tests for language execution."""

  def _make_schema(self, params, return_type):
    return {'params': params, 'return': {'type': return_type}}

  def _setup_test(self, lang_name):
    super()._setup_test(lang_name)
    self.prompt_translator = self.lang.make_prompt_translator()

  def make_executable_code(
      self,
      tmp_path,
      question,
      code_return_value,
      use_type_annotations: bool = True,
  ):
    """Helper function to make the temporary code for execution.

    Args:
      tmp_path: Path to the temporary directory.
      question: The question to test.
      code_return_value: The value the code should return.
      use_type_annotations: Use type annotations in the signature.

    Returns:
      The path to the written code and the prediction code
    """

    # Get the schema so we can get the return type of the expected outputs.
    schema, inputs = parsing.parse_schema_and_input_order(
        self.schema_spec, question.schema
    )

    return_value = self.literal_translator.convert_var_to_literal(
        schema[data_types.EXPECTED_KEY_NAME], code_return_value
    )

    out_code_path = tmp_path.joinpath(f'code.{self.lang.file_ext}')

    with out_code_path.open('w') as f:
      input_code = self.lang_spec.func_template_path.read_text()

      signature = self.prompt_translator.translate_signature_with_docstring(
          'Python',
          'Test break /**/ // */ -- """ #',
          'test',
          'Solution',
          schema,
          inputs,
          use_type_annotations,
      )

      input_code = input_code.replace('FN_SIGNATURE', signature)
      input_code = input_code.replace('RETURN_VALUE', return_value)

      code = code_generator.generate_code_for_question(
          question,
          schema,
          input_order=inputs,
          literal_translator=self.literal_translator,
          prompt_translator=self.prompt_translator,
          template_map=self.template_map,
      )
      code = code.replace('PLACEHOLDER_CODE_BODY', input_code)
      code = code.replace('PLACEHOLDER_FN_NAME', self.lang_spec['entry_point'])
      code = code.replace(
          'PLACEHOLDER_CLS_NAME', self.lang_spec.get('entry_cls', '')
      )

      print(code)
      f.write(code)
    return out_code_path, input_code

  @pytest.mark.parametrize(
      'is_correct', [True, False], ids=['correct', 'wrong']
  )
  def test_map_equality(self, lang_name, is_correct, tmp_path):
    self._setup_test(lang_name)

    question = Question(
        qid=0,
        title='testing',
        schema=self._make_schema(
            [
                {'name': 'arg0', 'type': 'boolean'},
            ],
            'map<string;list<double>>',
        ),
        test_list=[
            dict(idx=0, inputs={'arg0': True}, outputs={'A': [1.234567]}),
        ],
        entry_fn_name='test',
    )
    if is_correct:
      output = {'A': [1.234567]}
    else:
      output = {'A': [1.234549]}
    code_path, pred_code = self.make_executable_code(tmp_path, question, output)

    result = execute_code(
        prediction=Prediction('1', '0', lang_name, pred_code, code_path),
        commands=self.lang.command_fn(code_path),
    )
    print(result.stderr)
    assert not result.timed_out
    assert result.return_code == 0
    assert result.stdout == f'TEST-0...{"PASSED" if is_correct else "FAILED"}\n'
    assert not result.stderr

  @pytest.mark.parametrize(
      'is_correct', [True, False], ids=['correct', 'wrong']
  )
  def test_list_equality(self, lang_name, is_correct, tmp_path):
    self._setup_test(lang_name)

    question = Question(
        qid=0,
        title='testing',
        schema=self._make_schema(
            [{'name': 'arg0', 'type': 'boolean'}], 'list<map<string;boolean>>'
        ),
        test_list=[
            dict(idx=0, inputs={'arg0': True}, outputs=[{'A': False}]),
        ],
        entry_fn_name='test',
    )

    if is_correct:
      output = [{'A': False}]
    else:
      output = [{'A': True}]
    code_path, pred_code = self.make_executable_code(tmp_path, question, output)
    result = execute_code(
        prediction=Prediction('1', '0', lang_name, pred_code, code_path),
        commands=self.lang.command_fn(code_path),
    )

    assert not result.timed_out
    assert result.return_code == 0
    assert result.stdout == f'TEST-0...{"PASSED" if is_correct else "FAILED"}\n'
    assert not result.stderr

  @pytest.mark.parametrize(
      'is_correct', [True, False], ids=['correct', 'wrong']
  )
  def test_set_equality(self, lang_name, is_correct, tmp_path):
    self._setup_test(lang_name)

    question = Question(
        qid=0,
        title='testing',
        schema=self._make_schema(
            [{'name': 'arg0', 'type': 'set<string>'}], 'set<integer>'
        ),
        test_list=[
            dict(idx=0, inputs={'arg0': ['1', '2']}, outputs=[1, 2, 2]),
        ],
        entry_fn_name='test',
    )

    if is_correct:
      output = [2, 1]
    else:
      output = [3, 2]

    code_path, pred_code = self.make_executable_code(tmp_path, question, output)
    result = execute_code(
        prediction=Prediction('1', '0', lang_name, pred_code, code_path),
        commands=self.lang.command_fn(code_path),
    )

    assert not result.timed_out
    assert result.return_code == 0
    assert result.stdout == f'TEST-0...{"PASSED" if is_correct else "FAILED"}\n'
    assert not result.stderr

  @pytest.mark.parametrize(
      'type_str',
      ['set<integer>', 'map<string;integer>', 'list<string>', 'string'],
  )
  def test_null_equality(self, lang_name, type_str, tmp_path):
    self._setup_test(lang_name)

    question = Question(
        qid=0,
        title='testing',
        schema=self._make_schema(
            [{'name': 'arg0', 'type': type_str}], type_str
        ),
        test_list=[
            dict(idx=0, inputs={'arg0': None}, outputs=None),
        ],
        entry_fn_name='test',
    )

    code_path, pred_code = self.make_executable_code(tmp_path, question, None)
    result = execute_code(
        prediction=Prediction('1', '0', lang_name, pred_code, code_path),
        commands=self.lang.command_fn(code_path),
    )

    assert not result.timed_out
    assert result.return_code == 0
    assert result.stdout == 'TEST-0...PASSED\n'
    assert not result.stderr

  @pytest.mark.parametrize(
      'is_correct', [True, False], ids=['correct', 'wrong']
  )
  @pytest.mark.parametrize(
      'primitive',
      [('string', '1,2'), ('character', '1')],
      ids=['string', 'char'],
  )
  def test_primitive_equality(self, lang_name, is_correct, primitive, tmp_path):
    self._setup_test(lang_name)
    primitive_type, primitive_value = primitive
    question = Question(
        qid=0,
        title='testing',
        schema=self._make_schema(
            [{'name': 'arg0', 'type': 'boolean'}], primitive_type
        ),
        test_list=[
            dict(idx=0, inputs={'arg0': True}, outputs='2'),
        ],
        entry_fn_name='test',
    )

    code_path, pred_code = self.make_executable_code(
        tmp_path, question, '2' if is_correct else primitive_value
    )
    result = execute_code(
        prediction=Prediction('1', '0', lang_name, pred_code, code_path),
        commands=self.lang.command_fn(code_path),
    )

    assert not result.timed_out
    assert result.return_code == 0
    assert result.stdout == f'TEST-0...{"PASSED" if is_correct else "FAILED"}\n'
    assert not result.stderr

  @pytest.mark.parametrize(
      'is_correct', [True, False], ids=['correct', 'wrong']
  )
  def test_float_equality(self, lang_name, is_correct, tmp_path):
    self._setup_test(lang_name)

    question = Question(
        qid=0,
        title='testing',
        schema=self._make_schema(
            [{'name': 'arg0', 'type': 'boolean'}], 'float'
        ),
        test_list=[
            dict(idx=0, inputs={'arg0': True}, outputs=float('0.0001202')),
        ],
        entry_fn_name='test',
    )

    code_path, pred_code = self.make_executable_code(
        tmp_path,
        question,
        float('0.0001203') if is_correct else float('0.0001302'),
    )
    result = execute_code(
        prediction=Prediction('1', '0', lang_name, pred_code, code_path),
        commands=self.lang.command_fn(code_path),
    )

    assert not result.timed_out
    assert result.return_code == 0
    assert result.stdout == f'TEST-0...{"PASSED" if is_correct else "FAILED"}\n'
    assert not result.stderr

  @pytest.mark.parametrize(
      'is_correct', [True, False], ids=['correct', 'wrong']
  )
  def test_double_equality(self, lang_name, is_correct, tmp_path):
    self._setup_test(lang_name)

    question = Question(
        qid=0,
        title='testing',
        schema=self._make_schema(
            [{'name': 'arg0', 'type': 'boolean'}], 'double'
        ),
        test_list=[
            dict(idx=0, inputs={'arg0': True}, outputs=float('0.0000001202')),
        ],
        entry_fn_name='test',
    )

    code_path, pred_code = self.make_executable_code(
        tmp_path,
        question,
        float('0.0000001203') if is_correct else float('0.0000001302'),
    )
    result = execute_code(
        prediction=Prediction('1', '0', lang_name, pred_code, code_path),
        commands=self.lang.command_fn(code_path),
    )

    assert not result.timed_out
    assert result.return_code == 0
    assert result.stdout == f'TEST-0...{"PASSED" if is_correct else "FAILED"}\n'
    assert not result.stderr
