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

"""Driver functions for different modules.

These functions are primarily here to avoid circular imports while also allowing
them to be testable.
"""
from typing import Any, Dict, List, Tuple

from absl import logging
from babelcode import code_generator
from babelcode import data_types
from babelcode import languages
from babelcode import schema_parsing
from babelcode import translation
from jinja2 import Template
from tqdm import tqdm


def _generate_question_code(
    question: data_types.Question,
    schema: Dict[str, schema_parsing.SchemaType],
    input_order: List[str],
    literal_translator: translation.LiteralTranslator,
    prompt_translator: translation.PromptTranslator,
    template_map: Dict[str, Template],
    force_type_annotations: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
  """Generates the code for a specific question.

  Args:
    question: The question to generate the testing code for.
    schema: Te parsed schema of the question.
    input_order: The order of inputs.
    literal_translator: The literal translator to use.
    prompt_translator: The prompt translator to use.
    template_map: The mapping of templates to use.
    force_type_annotations: Force type annotations.

  Returns:
    A tuple where the first element is the dict of testing code and the second
    contains prompt info.
  """

  out_dict = question.to_dict()

  out_dict['test_code'] = code_generator.generate_code_for_question(
      question=question,
      parsed_schema=schema,
      input_order=input_order,
      literal_translator=literal_translator,
      template_map=template_map,
      prompt_translator=prompt_translator,
  )

  signature = prompt_translator.translate_signature(
      question.entry_fn_name,
      entry_cls_name=question.entry_cls_name,
      schema=schema,
      input_order=input_order,
      use_type_annotation=question.use_type_annotation
      or force_type_annotations,
  )
  signature_with_docstring = (
      prompt_translator.translate_signature_with_docstring(
          'Python',
          question.text,
          question.entry_fn_name,
          entry_cls_name=question.entry_cls_name,
          schema=schema,
          input_order=input_order,
          use_type_annotation=question.use_type_annotation
          or force_type_annotations,
      )
  )
  description = prompt_translator.translate_prompt(
      'Python', question.text, question.entry_fn_name
  )
  entry_fn_name = prompt_translator.translate_entry_function_name(
      question.entry_fn_name
  )
  entry_cls_name = prompt_translator.translate_entry_cls_name(
      question.entry_cls_name
  )

  out_dict['entry_fn_name'] = entry_fn_name
  out_dict['entry_cls_name'] = entry_cls_name

  prompt_dict = {
      'qid': question.qid,
      'signature': signature,
      'signature_with_docstring': signature_with_docstring,
      'text': description,
      'header': template_map['HEADER'].render(),
      'entry_fn_name': entry_fn_name,
      'entry_cls_name': entry_cls_name,
  }

  return out_dict, prompt_dict


ALLOWED_ERRORS = (
    data_types.QuestionParsingError,
    data_types.QuestionValidationError,
    data_types.IOPairError,
    schema_parsing.SchemaTypeError,
)


# Helper function to generate the code in a given language
def generate_code_for_questions(
    questions: List[data_types.Question], lang: languages.Language
):
  """Generate Code in a specified language.

  Args:
    questions: The list of questions.
    lang: The language to use.

  Returns:
    The problem code and the failures.
  """
  logging.info('Generating %s code', lang.name)
  failures = []
  out = []
  logging.debug('Initializing literal translator.')
  literal_translator = lang.make_literal_translator()
  prompt_translator = lang.make_prompt_translator()
  template_map = code_generator.load_template_map(lang.make_template_map())

  logging.debug('Getting language schema specification.')
  language_schema_spec = (
      schema_parsing.LanguageSchemaSpecRegistry.get_lang_spec(lang.name)
  )

  for question in tqdm(questions, desc='Generating Code'):
    logging.debug('Generating code for %s', question.qid)
    try:
      schema, input_order = schema_parsing.parse_schema_and_input_order(
          language_spec=language_schema_spec, raw_schema=question.schema
      )
    except ALLOWED_ERRORS as e:
      logging.debug(
          '%s failed to parse schema because of %s', question.qid, str(e)
      )
      failures.append((question, e))
      continue

    try:
      question_dict, prompt_dict = _generate_question_code(
          question=question,
          schema=schema,
          input_order=input_order,
          literal_translator=literal_translator,
          template_map=template_map,
          prompt_translator=prompt_translator,
      )

    except ALLOWED_ERRORS as e:
      logging.debug(
          '%s failed to parse schema because of %s', question.qid, str(e)
      )
      failures.append((question, e))
      continue

    out.append((question_dict, prompt_dict))
  fail_msg = f'{len(failures)}/{len(questions)} failed for {lang.name}'
  print(fail_msg)
  logging.info(fail_msg)

  return out, failures
