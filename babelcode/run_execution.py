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

"""Functions for setting up the environment for and running execution."""
import json
import logging
import pathlib
import shutil
import tempfile
from typing import Any, Dict, List

from babelcode.data_types.prediction import Prediction
from babelcode.execution import execute_predictions
from babelcode.languages import Language
from babelcode.metrics import calculate_metrics_from_raw_results
from babelcode.metrics import format_output_metrics
from babelcode.utils.metric_utils import write_to_tb_writer
import gin
from tqdm import tqdm

logger = logging.getLogger(__name__)

__all__ = ['run_execution_for_lang_predictions']


def setup_language_code_dirs(
    out_dir: pathlib.Path,
    lang: Language,
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
    qid = key.split('_')[0]
    try:
      question = question_mapping[qid]
    except KeyError:
      logger.warning('Could not find %s', qid)
      continue
    file_name = key
    q_path = out_dir.joinpath(file_name)
    q_path.mkdir()
    code_path = q_path.joinpath(f'{file_name}.{lang.file_ext}')
    if force_question_entry:
      pred_dict['entry_fn_name'] = question['entry_fn_name']
      if pred_dict.get('entry_cls_name', None) is not None:
        pred_dict['entry_cls_name'] = question['entry_cls_name']
    prediction = Prediction.from_dict(
        pred_dict, file_path=code_path, default_language=lang.name
    )
    with code_path.open('w') as f:
      code = question['test_code'].replace(
          'PLACEHOLDER_CODE_BODY', prediction.code
      )

      entry_fn_name = prediction.entry_fn_name or question['entry_fn_name']

      entry_cls_name = prediction.entry_cls_name or question['entry_cls_name']

      code = code.replace('PLACEHOLDER_FN_NAME', entry_fn_name)
      code = code.replace('PLACEHOLDER_CLS_NAME', entry_cls_name)
      f.write(code)

    pred_key = f'{prediction.qid}/{prediction.id}'
    if pred_key in out:
      logger.error('Prediction %s already exists', pred_key)
      raise KeyError('Duplicate predictions')
    out[pred_key] = {'prediction': prediction, 'full_code': code}

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
  write_to_tb_writer(
      {k: v for k, v in results.items() if k in overall_metrics},
      summary_writer,
      step,
      lang,
  )
  write_to_tb_writer(
      {
          q['qid']: {k: v for k, v in q.items() if k in question_metrics}
          for q in question_results
      },
      summary_writer,
      step,
      f'{lang}_questions',
  )


def run_execution_for_lang_predictions(
    lang: Language,
    question_mapping: Dict[str, Dict[str, str]],
    raw_predictions: Dict[str, Any],
    output_path: pathlib.Path,
    debug_dir_path: pathlib.Path,
    seed: int,
    step: int,
    force_question_entry: bool,
    summary_writer=None,
):
  """Evaluate the predictions from a single language."""

  def run_executions_in_dir(used_dir_path):
    logger.debug('Writing %s code to %s', lang.name, used_dir_path)
    if force_question_entry:
      logging.info('Force Use Question Entry is Enabled.')
    else:
      logging.info('Force Use Question Entry is disabled.')
    predictions = setup_language_code_dirs(
        used_dir_path,
        lang=lang,
        predictions=raw_predictions,
        question_mapping=question_mapping,
        force_question_entry=force_question_entry,
    )

    # Execute the predictions for the specific language.
    raw_results, total_runtime = execute_predictions(
        [d['prediction'] for d in predictions.values()], lang, output_path
    )

    (
        metrics,
        question_results,
        pred_results,
    ) = calculate_metrics_from_raw_results(  # pylint: disable=line-too-long
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

      question_results[i].update(
          {'title': question_mapping[qid]['title'], **meta}
      )

    metrics = format_output_metrics(
        lang_metrics=metrics,
        question_metrics=question_results,
        language=lang.name,
    )

    return metrics, pred_results

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
