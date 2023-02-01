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

"""Functions for handling the generation of code."""
import pathlib
from typing import Dict, List, Union

from absl import logging
import gin
from babelcode import data_types
from babelcode import schema_parsing
from babelcode import translation
import jinja2

SchemaType = schema_parsing.SchemaType
SchemaMapType = schema_parsing.SchemaMapType
Question = data_types.Question

# Set a list of required templates that must be present.
REQUIRED_TEMPLATES = ['MAIN', 'HEADER', 'EVALUATION']


@gin.configurable(denylist=['question'])
def pass_through_obfuscate(question: Question) -> Question:
  """Returns the question passed."""
  return question


@gin.configurable(denylist=['question'])
def naive_obfuscation(
    question: Question,
    function_name: str = 'model_prediction',
    cls_name: str = 'Prediction',
    arg_template: str = 'arg{idx}',
    force_type_annotation: bool = False,
) -> Question:
  """Obfuscates a question by naively replacing variables and function name.

  Args:
    question: The question to obfuscate.
    function_name: The name of the function to use.
    cls_name: The name of the class to use.
    arg_template: The template to use for the argument names. Must have `{idx}`.
    force_type_annotation: Force type annotation for the question.

  Returns:
    The obfuscated question.
  """
  logging.info('Naively obfuscating %s', question.qid)
  new_question = question.copy()

  new_arg_names = {
      v['name']: arg_template.format(idx=i)
      for i, v in enumerate(question.schema['params'])
  }
  new_question.change_var_names(new_arg_names)

  new_question.entry_fn_name = function_name
  new_question.entry_cls_name = cls_name
  if force_type_annotation:
    new_question.use_type_annotation = True
  return new_question


def _determine_question_requirements(
    question: Question,
    schema: SchemaMapType,
    double_precision: float,
    float_precision: float,
) -> Dict[str, Union[str, float, bool]]:
  """Determines the question specifc requirements needed for generating the code.

  Args:
    question: The question the requirements are for.
    schema: The schema of the question.
    double_precision: The precision to use for double evaluation.
    float_precision: The precision to use for float evaluation.

  Returns:
    A dict of requirements for the question.
  """
  _ = question

  question_requirements = {
      'evaluation_method': 'default',
      'precision': float_precision,
      'use_float': True,
  }
  return_type = schema[data_types.EXPECTED_KEY_NAME]
  if return_type.type_str == 'double' or return_type.type_str == 'float':
    question_requirements['evaluation_method'] = 'float'
    if return_type.type_str == 'double':
      question_requirements['precision'] = double_precision
      question_requirements['use_float'] = False

  return question_requirements


def load_template_map(
    template_map: Dict[str, pathlib.Path]
) -> Dict[str, jinja2.Template]:
  """Loads the Jinja template maps.

  Args:
    template_map: The mapping of string to paths for the templates.

  Returns:
    The map of template names to loaded templates.

  Raises:
    KeyError: If the required templates aer missing.
  """
  logging.info('Template map is %s', template_map)

  # Make sure that the required templates are present.
  for template_name in REQUIRED_TEMPLATES:
    if template_name not in template_map:
      raise KeyError(f'Missing required template "{template_name}"')

  # Load the actual files as Jinja templates
  templates = {}
  for name, path in template_map.items():
    logging.info('Loading template "%s" located at "%s"', name, path)
    templates[name] = jinja2.Template(
        path.read_text(), undefined=jinja2.StrictUndefined
    )

  return templates


def generate_code_for_question(
    question: Question,
    parsed_schema: Dict[str, SchemaType],
    input_order: List[str],
    literal_translator: translation.LiteralTranslator,
    prompt_translator: translation.PromptTranslator,
    template_map: Dict[str, jinja2.Template],
    float_precision: float = 1e-6,
    double_precision: float = 1e-9,
    debug: bool = False,
) -> str:
  """Generates code for a question.

  Args:
      question: The question to use.
      parsed_schema: The schema for the question parsed in the given language.
      input_order: The ordering of the inputs.
      literal_translator: The literal translator class to use.
      prompt_translator: The prompt translator class to use.
      template_map: The map of templates to use.
      float_precision: Float precision to use for evaluation.
      double_precision: Double precision to use for evaluation.
      debug: Debug mode. Default is False.

  Returns:
      The code to test the question.
  """

  question_requirements = _determine_question_requirements(
      question, parsed_schema, double_precision, float_precision
  )
  logging.debug('question_requirements=%s', question_requirements)

  test_cases = []
  for io_pair in question.test_list:
    test_cases.append(
        literal_translator.generate_test_case_literals(
            qid=question.qid,
            io_pair=io_pair,
            underlying_schema=parsed_schema,
            input_order=input_order,
        )
    )

  # Make the signature to use with the driver function.
  signature, params, _ = prompt_translator.translate_type_signature(
      schema=parsed_schema, input_order=input_order, use_type_annotation=False
  )
  precision = question_requirements['precision']
  type_str = 'float' if question_requirements['use_float'] else 'double'
  precision = literal_translator.convert_primitive_fn(
      SchemaType(type_str=type_str), precision
  )

  evaluation_kwargs = {
      'evaluation_method': question_requirements['evaluation_method'],
      'precision': precision,
  }
  evaluation_code = template_map['EVALUATION'].render(**evaluation_kwargs)

  header_code = template_map['HEADER'].render()
  # Setup the template args for use with the jinja template.
  template_args = {
      'params': params,
      'signature': signature,
      'test_cases': test_cases,
      'return_type': parsed_schema[data_types.EXPECTED_KEY_NAME].lang_type,
      'debug': debug,
      'text': question.text,
      'evaluation_function': evaluation_code,
      'header': header_code,
  }

  main_code = template_map['MAIN'].render(**template_args)

  return main_code
