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
import collections
import json
import logging
import pathlib
import shutil
import tempfile
from typing import Any, Callable, Dict, List, Tuple

import gin
from absl import logging
from jinja2 import Template
from tqdm import tqdm

from babelcode import code_generator
from babelcode import data_types
from babelcode import execution
from babelcode import languages
from babelcode import metrics as metrics_module
from babelcode import schema_parsing
from babelcode import translation
from babelcode import utils

ObfuscationFnType = Callable[[data_types.Question], data_types.Question]
Prediction = data_types.Prediction


@gin.configurable('prompt_generation',
                  allowlist=['force_type_annotations', 'obfuscation_fn'])
def generate_prompt_info(
    original_question: data_types.Question,
    language: languages.Language,
    prompt_translator: translation.PromptTranslator = None,
    template_map: Dict[str, Template] = None,
    force_type_annotations: bool = False,
    obfuscation_fn: ObfuscationFnType = code_generator.pass_through_obfuscate,
) -> Dict[str, Any]:
  """Generates the prompt information for a question.

  Args:
    original_question: The question to generate the testing code for.
    language: The langauge to use.
    prompt_translator: The prompt translator to use.
    template_map: The mapping of templates to use.
    force_type_annotations: Force type annotations. obfuscation_function
    obfuscation_fn: Callable that takes in a question and returns a question.
      Can use this to obfuscate variables.

  Returns:
    The dict of prompting information.
  """

  question = obfuscation_fn(original_question)

  language_schema_spec = (
      schema_parsing.LanguageSchemaSpecRegistry.get_lang_spec(language.name))
  schema, input_order = schema_parsing.parse_schema_and_input_order(
      language_spec=language_schema_spec, raw_schema=question.schema)

  signature = prompt_translator.translate_signature(
      question.entry_fn_name,
      entry_cls_name=question.entry_cls_name,
      schema=schema,
      input_order=input_order,
      use_type_annotation=question.use_type_annotation
      or force_type_annotations,
  )
  signature_with_docstring = description = None
  if original_question.text:
    # Replace the original fn name with the obfuscated one
    text = original_question.text.replace(original_question.entry_fn_name,
                                          question.entry_fn_name)
    text = text.replace(original_question.entry_cls_name,
                        question.entry_cls_name)

    signature_with_docstring = (
        prompt_translator.translate_signature_with_docstring(
            'Python',
            text,
            question.entry_fn_name,
            entry_cls_name=question.entry_cls_name,
            schema=schema,
            input_order=input_order,
            use_type_annotation=question.use_type_annotation
            or force_type_annotations,
        ))
    description = prompt_translator.translate_prompt('Python', text,
                                                     question.entry_fn_name)
  entry_fn_name = prompt_translator.translate_entry_function_name(
      question.entry_fn_name)
  entry_cls_name = prompt_translator.translate_entry_cls_name(
      question.entry_cls_name)

  return {
      'qid': question.qid,
      'signature': signature,
      'signature_with_docstring': signature_with_docstring,
      'text': description,
      'header': template_map['HEADER'].render(),
      'entry_fn_name': entry_fn_name,
      'entry_cls_name': entry_cls_name,
      'arguments': input_order,
  }


def _generate_question_code(
    question: data_types.Question,
    schema: Dict[str, schema_parsing.SchemaType],
    input_order: List[str],
    literal_translator: translation.LiteralTranslator,
    prompt_translator: translation.PromptTranslator,
    template_map: Dict[str, Template],
) -> Dict[str, Any]:
  """Generates the code for a specific question.

  Args:
    question: The question to generate the testing code for.
    schema: Te parsed schema of the question.
    input_order: The order of inputs.
    literal_translator: The literal translator to use.
    prompt_translator: The prompt translator to use.
    template_map: The mapping of templates to use.

  Returns:
    The dictionary with testing code.
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

  out_dict['entry_fn_name'] = prompt_translator.translate_entry_function_name(
      question.entry_fn_name)
  out_dict['entry_cls_name'] = prompt_translator.translate_entry_cls_name(
      question.entry_cls_name)
  return out_dict


ALLOWED_ERRORS = (
    data_types.QuestionParsingError,
    data_types.QuestionValidationError,
    data_types.IOPairError,
    schema_parsing.SchemaTypeError,
)


# Helper function to generate the code in a given language
def generate_code_for_questions(questions: List[data_types.Question],
                                lang: languages.Language):
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
      schema_parsing.LanguageSchemaSpecRegistry.get_lang_spec(lang.name))

  for question in tqdm(questions, desc='Generating Code'):
    logging.debug('Generating code for %s', question.qid)
    try:
      schema, input_order = schema_parsing.parse_schema_and_input_order(
          language_spec=language_schema_spec, raw_schema=question.schema)
    except ALLOWED_ERRORS as e:
      logging.debug('%s failed to parse schema because of %s', question.qid,
                    str(e))
      failures.append((question, e))
      continue

    try:
      question_dict = _generate_question_code(
          question=question,
          schema=schema,
          input_order=input_order,
          literal_translator=literal_translator,
          template_map=template_map,
          prompt_translator=prompt_translator,
      )
      prompt_dict = generate_prompt_info(
          original_question=question,
          language=lang,
          template_map=template_map,
          prompt_translator=prompt_translator,
      )

    except ALLOWED_ERRORS as e:
      logging.debug('%s failed to parse schema because of %s', question.qid,
                    str(e))
      failures.append((question, e))
      continue

    out.append((question_dict, prompt_dict))
  fail_msg = f'{len(failures)}/{len(questions)} failed for {lang.name}'
  print(fail_msg)
  logging.info(fail_msg)

  return out, failures


def setup_language_code_dirs(
    out_dir: pathlib.Path,
    lang: languages.Language,
    predictions: Dict[str, Any],
    question_mapping: Dict[str, Dict[str, str]],
    force_question_entry: bool,
):
  """Setup the directories for each of the questions.

  Args:
      out_dir: Path to write dirs to.
      lang: The language to write each question in.
      predictions: The predictions for this language.
      question_mapping: The mapping of questions to their information.
      force_question_entry: Force using the default question entry points
        instead of those specified by the predictions.

  Raises:
    KeyError: Duplicated prediction ids.

  Returns:
      The dict of `Prediction` objects with their full testing code created
      and the read question info.
  """
  # Do an ID->Question data mapping so we can align with the predictions.

  out = {}
  for key, pred_dict in tqdm(predictions.items(), desc='Creating Dirs'):
    # Get the prediction and question data.
    qid = key.split('/')[0]
    try:
      question = question_mapping[qid]
    except KeyError:
      logging.warning('Could not find %s', qid)
      continue
    file_name = key.replace('/', '_')
    q_path = out_dir.joinpath(file_name)
    q_path.mkdir()
    code_path = q_path.joinpath(f'{file_name}.{lang.file_ext}')
    if force_question_entry:
      pred_dict['entry_fn_name'] = question['entry_fn_name']
      if pred_dict.get('entry_cls_name', None) is not None:
        pred_dict['entry_cls_name'] = question['entry_cls_name']
    prediction = Prediction.from_dict(pred_dict,
                                      file_path=code_path,
                                      default_language=lang.name)
    with code_path.open('w', encoding='utf-8') as f:
      code = question['test_code'].replace('PLACEHOLDER_CODE_BODY',
                                           prediction.code)

      entry_fn_name = prediction.entry_fn_name or question['entry_fn_name']

      entry_cls_name = prediction.entry_cls_name or question['entry_cls_name']

      code = code.replace('PLACEHOLDER_FN_NAME', entry_fn_name)
      code = code.replace('PLACEHOLDER_CLS_NAME', entry_cls_name)
      f.write(code)

    pred_key = f'{prediction.qid}/{prediction.id}'
    if pred_key in out:
      logging.error('Prediction %s already exists', pred_key)
      raise KeyError('Duplicate predictions')
    out[pred_key] = prediction

  return out


@gin.configurable(
    'tensorboard_metrics',
    denylist=['results', 'question_results', 'step', 'summary_writer', 'lang'],
)
def write_metrics_to_tb(
    results,
    question_results,
    step,
    summary_writer,
    lang,
    overall_metrics: List[str],
    question_metrics: List[str],
):
  """Writes the metrics to a tensorboard."""
  utils.write_to_tb_writer(
      {
          k: v for k, v in results.items() if k in overall_metrics
      },
      summary_writer,
      step,
      lang,
  )
  utils.write_to_tb_writer(
      {
          q['qid']: {
              k: v for k, v in q.items() if k in question_metrics
          } for q in question_results
      },
      summary_writer,
      step,
      f'{lang}_questions',
  )


def load_progress_from_dir(dir_path: pathlib.Path) -> Dict[str, Any]:
  """Loads progress of an evaluation run from a directory.

  Args:
    dir_path: The directory to load progress from.

  Returns:
    A dict with the keys 'execution_results' that has the prior ran execution
    results.
  """
  logging.info('Loading progress from %s', dir_path)
  out = collections.defaultdict(dict)
  found_results = 0
  for exec_file in dir_path.glob('*_execution_results.jsonl'):
    logging.info('Loading execution results from %s', exec_file)
    for lang, results in data_types.read_execution_results_from_file(
        exec_file).items():
      out[lang].update(results)
      found_results += len(results)
  logging.info('Found %d execution results across %d languages:', found_results,
               len(out))
  for k, v in out.items():
    logging.info('\t%-10s: %s', k, len(v))
  return out


def _process_results(
    lang: languages.Language,
    raw_results: List[data_types.ExecutionResult],
    total_runtime: str,
    question_mapping: Dict[str, Dict[str, str]],
    step: int,
    seed: int,
    summary_writer=None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
  """Processes the results from executing code."""
  metrics_tuple = metrics_module.calculate_metrics_from_raw_results(
      raw_results=raw_results,  # type: ignore
      question_data=question_mapping,
      runtime=total_runtime,
      seed=seed,
      k_vals=gin.REQUIRED,  # type: ignore
      num_preds_per_question=gin.REQUIRED,  # type: ignore
      subsampling_rounds=gin.REQUIRED,  # type: ignore
      subsampling_iter_per_round=gin.REQUIRED,  # type: ignore
      shuffle=gin.REQUIRED,  # type: ignore
      include_outcome_pct=gin.REQUIRED,
  )  # type: ignore
  metrics, question_results, pred_results = metrics_tuple
  if summary_writer is not None:
    write_metrics_to_tb(
        metrics,
        question_results,
        step,
        summary_writer,
        lang.name,
        overall_metrics=gin.REQUIRED,
        question_metrics=gin.REQUIRED,
    )

  logging.info('Adding metadata to %d questions', len(question_results))
  for i in range(len(question_results)):
    qid = question_results[i]['qid']
    meta = question_mapping[qid].get('metadata', {})
    for k in list(meta.keys()):
      if k in question_results[i]:
        logging.warning(
            'Question %s has metadata key %s that is used for a metric.',
            qid,
            k,
        )
        meta.pop(k)

    question_results[i].update({
        'title': question_mapping[qid]['title'],
        **meta
    })

  metrics = metrics_module.format_output_metrics(
      lang_metrics=metrics,
      question_metrics=question_results,
      language=lang.name,
  )
  return metrics, pred_results


def execute_bc_predictions(
    lang: languages.Language,
    question_mapping: Dict[str, Dict[str, str]],
    raw_predictions: Dict[str, Any],
    output_path: pathlib.Path,
    debug_dir_path: pathlib.Path,
    seed: int,
    step: int,
    force_question_entry: bool,
    executed_predictions: Dict[str, Any],
    summary_writer=None,
):
  """Evaluates the predictions from a single language."""

  def run_executions_in_dir(used_dir_path):
    logging.debug('Writing %s code to %s', lang.name, used_dir_path)
    if force_question_entry:
      logging.info('Force Use Question Entry is Enabled.')
    else:
      logging.info('Force Use Question Entry is disabled.')

    removed = 0
    to_remove = []
    for k in executed_predictions:
      if k in raw_predictions:
        logging.debug('%s prediction is already completed, removing', k)
        raw_predictions.pop(k)
        removed += 1
      else:
        to_remove.append(k)
    logging.debug('Removing %d keys that were not found...', len(to_remove))
    for k in to_remove:
      executed_predictions.pop(k)
    logging.info(
        'Skipping %d already executed predictions out of %d',
        removed,
        len(raw_predictions) + removed,
    )
    if raw_predictions:
      predictions = setup_language_code_dirs(
          used_dir_path,
          lang=lang,
          predictions=raw_predictions,
          question_mapping=question_mapping,
          force_question_entry=force_question_entry,
      )

      # Execute the predictions for the specific language.
      raw_results, total_runtime = execution.execute_predictions(
          list(predictions.values()), lang, output_path)

      raw_results += list(executed_predictions.values())
    else:
      logging.info('All predictions have been executed, evaluating...')
      raw_results = list(executed_predictions.values())
      total_runtime = '00:00:00'

    return _process_results(
        lang=lang,
        raw_results=raw_results,
        total_runtime=total_runtime,
        question_mapping=question_mapping,
        step=step,
        seed=seed,
        summary_writer=summary_writer,
    )

  if debug_dir_path is not None:
    debug_dir_path = pathlib.Path(debug_dir_path, lang.name)
    if debug_dir_path.exists():
      shutil.rmtree(debug_dir_path)
    debug_dir_path.mkdir(parents=True)
    return run_executions_in_dir(debug_dir_path)
  else:
    # Use a temporary directory so that we can write without worry.
    with tempfile.TemporaryDirectory() as temp_dir:
      return run_executions_in_dir(pathlib.Path(temp_dir))
