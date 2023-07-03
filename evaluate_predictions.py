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
"""Script to execute code for evaluation across multiple languages."""
import collections
import json
import os
import pathlib
import random
import shutil
from typing import Optional

import gin
import tensorflow as tf
from absl import app
from absl import flags
from absl import logging

from babelcode import QUESTION_DATA_KEYS
from babelcode import execute_bc_predictions
from babelcode import load_progress_from_dir
from babelcode import utils
from babelcode.languages import LanguageRegistry

FLAGS = flags.FLAGS
_GIN = flags.DEFINE_string('gin_file', None, 'Gin configuration file.')
_EXP_NAME = flags.DEFINE_string('experiment_name', None,
                                'Name of the experiment.')
_OUTPUT_PATH = flags.DEFINE_string('output_path', None, 'Output path.')
_PRED_PATH = flags.DEFINE_string('predictions', None, 'Prediction path.')
_TEST_CODE_PATH = flags.DEFINE_string('test_code', None,
                                      'pathlib.Path to testing code')
_OVERWRITE = flags.DEFINE_bool('overwrite', False,
                               'Overwrite output file if it exists')
_LANGUAGES = flags.DEFINE_list('languages', None,
                               'Comma separated list of languages to run')
_DEBUG = flags.DEFINE_bool('debug', False, 'Enable Debug mode')
_NUM_CORES = flags.DEFINE_integer('cpu_count',
                                  None,
                                  help='Number of CPUs to use.')
_DEBUG_NUM_PREDS = flags.DEFINE_integer(
    'debug_num_preds', -1, help='Debugging number of predictions to use.')
_PREDS_PER_QUESTION = flags.DEFINE_integer(
    'samples', None, 'Number of predictions per question.')
_STEP = flags.DEFINE_integer('step', 0, 'Step to use for tensorboard.')
_FORCE_QUESTION_ENTRY = flags.DEFINE_bool(
    'use_question_entry',
    False,
    'Force using the question entry points instead of the prediction ones.',
)
_VALIDATION_MODE = flags.DEFINE_bool('validation', False,
                                     'Enable validation printing.')

_DEBUG_DIR_PATH = flags.DEFINE_string("debug_dir", None,
                                      "Debugging dir to save code to.")

_ALLOW_EXECUTION = flags.DEFINE_bool("allow_execution", False,
                                     "Allow Execution")


@gin.configurable(
    'general',
    denylist=[
        'experiment_name', 'prediction_path', 'output_path', 'test_code_path',
        'overwrite', 'eval_languages', 'debug_code_gen_dir'
    ],
)
def evaluate_predictions_from_file(
    experiment_name: str,
    prediction_path: pathlib.Path,
    output_path: pathlib.Path,
    test_code_path: Optional[pathlib.Path],
    overwrite: bool,
    eval_languages: Optional[str] = None,
    debug: bool = False,
    debug_code_gen_dir: Optional[str] = None,
    debug_num_preds: int = -1,
    seed: int = 1,
    validation_mode: bool = False,
):
  """Evaluates a set of predictions.

  Take in a set of predictions files, and execute them against test cases.
  Results are saved to a `results.json` file in the `output_path`.

  Args:
    experiment_name: The name of the experiment.
    prediction_path: The path to the predictions.
    output_path: The output path.
    test_code_path: The path to the testing code.
    overwrite: Overwrite the output directory if found.
    eval_languages: The languages to restrict evaluation to.
    debug: Enable debugging.
    debug_code_gen_dir: Save the generated testing code to a local directory
      instead of a temporary one.
    debug_num_preds: Only debug a specific number of predictions.
    seed: The seed to use.
    validation_mode: Enable validation mode where metrics are not reported, but
      the predictions that had an error or timed out are.

  Raises:
    <Any>:
  """

  debug = debug_num_preds > 0 or debug
  if debug:
    experiment_name = f'{experiment_name}.DEBUG'
    print('Debug is enabled.')
  output_path = output_path.joinpath(experiment_name)

  must_load_progress = False
  if output_path.exists():
    if overwrite:
      shutil.rmtree(output_path)
    else:
      must_load_progress = True

  output_path.mkdir(exist_ok=True, parents=True)
  utils.setup_logging('logs', debug, log_path=output_path)
  logging.info('Evaluating predictions from %s', prediction_path)
  logging.info('Saving to %s', output_path)
  logging.info('Reading tests from %s', test_code_path)

  summary_writer = tf.summary.create_file_writer(str(output_path),
                                                 flush_millis=120)

  existing_results = {}
  if must_load_progress:
    # If a language was stopped mid evaluation, it will still have its
    # temporary path. so check that first.

    logging.info('Getting executed results from %s', output_path)
    existing_results = load_progress_from_dir(output_path)
  else:
    logging.info('No prior results found')

  # Allow the use of multiple language predictions in a single file by using
  # the language in the key during reading.
  all_predictions = list(map(json.loads, prediction_path.open()))
  logging.info('Found %d total predictions', len(all_predictions))

  # Separate the predictions into their own language buckets.
  preds_by_lang = collections.defaultdict(dict)
  question_id_counter = collections.Counter()
  logging.debug('Grouping predictions by language')
  for prediction in all_predictions:
    language = prediction[f"language"]
    pid = question_id_counter[f"{prediction['language']}/{prediction['qid']}"]
    prediction['id'] = pid
    preds_by_lang[language][f"{prediction['qid']}/{pid}"] = prediction
    question_id_counter[f"{prediction['language']}/{prediction['qid']}"] += 1

  langs_found = list(sorted(preds_by_lang))
  logging.info('%d language(s) found', len(langs_found))

  logging.info('# Preds by Language:')
  for lang in langs_found:
    msg = f'{lang:>10} = {len(preds_by_lang[lang])}'
    logging.info(msg)

  if eval_languages:
    if any(l not in langs_found for l in eval_languages):
      raise ValueError(f'{eval_languages=} not found in predictions')
    logging.warning('Only evaluating %s', eval_languages)
    langs_found = eval_languages

  # Save the gin config and the information on where the predictions and test
  # code are located to two files in the output directory.
  logging.info('Saving launch information...')
  with output_path.joinpath('config.gin').open('w') as f:
    f.write(gin.config_str())

  with output_path.joinpath('launch_info.json').open('w') as f:
    json.dump(
        {
            'prediction_path': str(prediction_path),
            'test_code_path': str(test_code_path),
        },
        f,
        indent=True,
    )

  question_mapping = collections.defaultdict(dict)

  found = 0
  if test_code_path:
    logging.info('Reading questions from %s', test_code_path)
    for line in map(json.loads,
                    test_code_path.joinpath('testing_code.jsonl').open()):
      question_mapping[line['language']][str(line['qid'])] = line
      found += 1
  else:
    logging.info('Making question mapping from predictions found.')
    for lang, preds in preds_by_lang.items():
      for pid, pred in preds.items():
        qid, _ = pid.split('/')
        question_mapping[lang][qid] = {k: pred[k] for k in QUESTION_DATA_KEYS}
      found += len(question_mapping[language])

  logging.info('Found %d questions across %d languages', found,
               len(question_mapping))

  all_metrics = {}
  all_pred_metrics = []
  all_error_per_lang = {}
  for lang_name in langs_found:
    lang = LanguageRegistry.get_language(lang_name)

    if debug_num_preds > 0 and len(preds_by_lang[lang_name]) > debug_num_preds:
      logging.warning('ONLY USING %d PREDICTIONS', debug_num_preds)

      # Set the seed for debugging a subset.
      utils.set_seed(seed)
      to_keep = random.sample(list(preds_by_lang[lang_name]), debug_num_preds)
      preds_to_use = {
          k: v for k, v in preds_by_lang[lang_name].items() if k in to_keep
      }
    else:
      preds_to_use = preds_by_lang[lang_name]

    metrics, pred_results = execute_bc_predictions(
        lang=lang,
        question_mapping=question_mapping[lang_name],
        raw_predictions=preds_to_use,
        output_path=output_path,
        debug_dir_path=debug_code_gen_dir,  # type: ignore
        seed=seed,
        step=_STEP.value,
        executed_predictions=existing_results.get(lang_name, {}),
        summary_writer=summary_writer,
        force_question_entry=_FORCE_QUESTION_ENTRY.value,
    )  # type:ignore

    # Add the number of questions with all predictions having error.
    with_all_error = []
    with_all_timed_out = []
    num_questions = 0
    for k, metric_dict in metrics.items():
      # Skip the overview metrics.
      if 'metrics' in k:
        continue
      num_preds = metric_dict['num_predictions']
      qid = k.split('/')[-1]
      title = question_mapping[lang_name][qid]['title']
      if num_preds == metric_dict['Had Error']:
        with_all_error.append(f'{title} ({qid=})')
      elif num_preds == metric_dict['Timed Out']:
        with_all_timed_out.append(f'{title} ({qid=})')
      num_questions += 1
    all_error_per_lang[lang_name] = (
        with_all_error,
        with_all_timed_out,
        num_questions,
    )
    all_metrics.update(metrics)
    all_pred_metrics.extend(pred_results)
  metric_path = output_path.joinpath('metrics.json')
  logging.info('Saving metrics to %s', metric_path)
  with metric_path.open('w') as f:
    json.dump(all_metrics, f)

  pred_result_path = output_path.joinpath('pred_results.jsonl')
  logging.info('Saving all prediction results to %s', pred_result_path)
  with pred_result_path.open('w') as f:
    for l in all_pred_metrics:
      f.write(json.dumps(l.to_dict()) + '\n')
  if validation_mode:
    logging.info(
        'Number of Questions With Issues For %d languages:',
        len(all_error_per_lang),
    )
    for lang_name, (
        with_error,
        with_timeout,
        num_questions,
    ) in all_error_per_lang.items():
      msg = (f'{lang_name:>16} ='
             f' {len(with_error)+len(with_timeout)}/{num_questions}')
      logging.info(msg)
      logging.info('%s\tWith Error=%s', ' ' * 16, with_error)

      logging.info('%s\tWith Timeout=%s', ' ' * 16, with_timeout)
  else:
    logging.info('Metrics:')
    for lang_name in langs_found:
      logging.info('\t%s:', lang_name)
      metrics = all_metrics[f'{lang_name}/metrics']
      to_print = ['questions_passed']
      for k in metrics:
        if 'subsampling_pass' in k or 'estimate' in k:
          to_print.append(k)
      for k in sorted(to_print):
        value = metrics[k]
        key_str = f'{k:>32}'
        if isinstance(value, float):
          value_str = f'{value:.3f}'
        elif isinstance(value, (dict, list, tuple)):
          continue
        else:
          value_str = f'{value}'
        logging.info('\t%s = %s', key_str, value_str)


if __name__ == '__main__':

  def eval_preds_main(_):
    """Main entry point to the launch."""
    FLAGS['alsologtostderr'].value = True
    # Create gin bindings to overwrite the config.
    bindings = []

    if _DEBUG.value:
      bindings.append('general.debug=True')
    if _NUM_CORES.value:
      bindings.append(f'execution.num_workers={_NUM_CORES.value}')
    if _DEBUG_NUM_PREDS.value > 0:
      bindings.append(f'general.debug_num_preds={_DEBUG_NUM_PREDS.value}')
    if _PREDS_PER_QUESTION.value is not None and _PREDS_PER_QUESTION.value > 0:
      bindings.append(
          f'metrics.num_preds_per_question={_PREDS_PER_QUESTION.value}')

    print(f'gin_{bindings=}')
    gin_path = pathlib.Path(_GIN.value).resolve()
    print(f'Gin pathlib.Path={gin_path}')
    gin.parse_config_file(str(gin_path))
    gin.parse_config(bindings=bindings)

    test_code_path = None
    if _TEST_CODE_PATH.value:
      test_code_path = pathlib.Path(_TEST_CODE_PATH.value).resolve()

    if _ALLOW_EXECUTION.value:
      os.environ['ALLOW_EXECUTION'] = 'true'

    debug_dir = _DEBUG_DIR_PATH.value
    if debug_dir:
      debug_dir = pathlib.Path(debug_dir)
    evaluate_predictions_from_file(
        experiment_name=_EXP_NAME.value,
        prediction_path=pathlib.Path(_PRED_PATH.value).resolve(),
        output_path=pathlib.Path(_OUTPUT_PATH.value).resolve(),
        test_code_path=test_code_path,
        overwrite=_OVERWRITE.value,
        validation_mode=_VALIDATION_MODE.value,
        eval_languages=_LANGUAGES.value,
        debug_code_gen_dir=debug_dir)

  flags.mark_flags_as_required([
      _GIN.name,
      _EXP_NAME.name,
      _OUTPUT_PATH.name,
      _PRED_PATH.name,
  ])
  app.run(eval_preds_main)
