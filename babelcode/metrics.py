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

"""Metric functions."""
import collections
import copy
from typing import Any, Dict, List, Tuple

import gin
import numpy as np
from absl import logging

from babelcode import data_types
from babelcode.utils import set_seed

QuestionResult = data_types.QuestionResult
PredictionResult = data_types.PredictionResult
PredictionOutcome = data_types.PredictionOutcome


def pass_at_k_estimator(n, c, k):
  """Pass@K estimator from https://arxiv.org/abs/2107.03374.

  Args:
      n: total number of samples
      c: number of correct sample
      k: k in pass@$k$

  Returns:
    Estimated pass@k value.
  """

  if n - c < k:
    return 1.0
  return 1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))


def pass_at_k_subsampling(pred_results: np.ndarray, k: int,
                          rng: np.random.Generator) -> bool:
  """Pass@k metric done by sampling a subset of the total results.

  Args:
      pred_results: An array with N elements for each prediction with a bool
        value if the prediction passed or not.
      k: Number of predictions to check.
      rng: The numpy random generator.

  Returns:
    Did a program in the sample subset pass its tests.
  """
  if len(pred_results) == 1:
    return pred_results[0] > 0

  # Sample a subset of the prediction results without replacement.
  subset = rng.choice(pred_results, size=k, replace=False)

  # If at least 1 prediction in the subset passes, count that as a pass.
  return subset.sum() > 0


def calculate_subsampling_passes(passing_vals: np.ndarray, k_val: int,
                                 seed: int, subsampling_rounds: int,
                                 subsampling_iter_per_round: int,
                                 shuffle: bool) -> np.ndarray:
  """Calculates the subsampling pass@k means and variances.

  Args:
    passing_vals: The array of bools for if the prediction passed.
    k_val: The k value to calculate.
    seed: The seed.
    subsampling_rounds: Number of subsampling rounds.
    subsampling_iter_per_round: Number of iterations per round.
    shuffle: Shuffle the prediction results at the start of each round.

  Returns:
    The array of results from subsampling.
  """
  logging.info(
      'Calculating subsampling passes for k=%d and passing_vals.shape=%s',
      k_val, passing_vals.shape)
  logging.info('Doing %d rounds with %d iterations per round.',
               subsampling_rounds, subsampling_iter_per_round)
  # The subsampled pass@k for each round.
  # (num subsampling rounds, num iterations per round)
  subsampling_pass_at_k_vals = []

  set_seed(seed)
  rng = np.random.default_rng(seed)

  for round_num in range(subsampling_rounds):
    if shuffle:
      rng.shuffle(passing_vals)
    round_subset_results = []
    for iteration_num in range(subsampling_iter_per_round):
      iteration_results = []

      # Go over each question and determine if at least 1 prediction in the
      # sampled subset passed.
      for i in range(passing_vals.shape[0]):
        had_passing_subset = pass_at_k_subsampling(
            passing_vals[i], k=k_val, rng=rng)
        iteration_results.append(had_passing_subset)

      logging.debug('Finished iteration %d of round %d', iteration_num,
                    round_num)
      logging.debug('Got pass@k results of: %s', iteration_results)

      # Calculate the subsampled pass@k for the questions.
      pass_at_k = float(np.mean(iteration_results)) * 100
      round_subset_results.append(pass_at_k)
    subsampling_pass_at_k_vals.append(round_subset_results)

  return np.array(subsampling_pass_at_k_vals)


def calculate_question_aggregate_metrics(
    question_results: Dict[str, QuestionResult],
    tracked_attributes: List[str]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
  """Calculate aggregate metrics for the question results.

  Args:
      question_results: The dict of qids to question results.
      tracked_attributes: The attributes of PredictionResult to track.

  Returns:
      Returns the main dict of results for the whole set of questions, and the
      individual question results.
  """

  def calculate_question_metric(question: QuestionResult):
    out = {
        'qid': question.id,
        'language': question.lang,
        'num_predictions': question.num_predictions
    }
    for outcome in PredictionOutcome:
      out[str(outcome)] = question.count_result(outcome)

    # Certain metrics, such as runtimes and test cases passed are only cared
    # about depending on if that prediction passed
    tracked_stats = {k: [] for k in tracked_attributes + ['num_tc_passed']}
    num_total_tests_passed = collections.Counter()

    for i in range(len(question)):
      try:
        p = question.get_vals_for_idx(i)
      except IndexError as e:
        logging.error('%d is too big for question %s with len(question)=%d', i,
                      question.id, len(question))
        raise e
      if p[PredictionOutcome.PASSED]:
        for attr_name in tracked_stats.keys():
          tracked_stats[attr_name].append(p[attr_name])

      num_total_tests_passed[p['num_tc_passed']] += 1

    for k, v in tracked_stats.items():
      out[f'{k}_median'] = np.median(v) if v else None
      out[f'{k}_mean'] = np.mean(v) if v else None

    num_passed_n_total_tests = {}
    for tc_count in range(question.num_test_cases + 1):
      num_passed_n_total_tests[str(tc_count)] = num_total_tests_passed[tc_count]
    out['num_passed_N_total_tests'] = num_passed_n_total_tests
    out['num_results_by_test'] = question.specific_test_results
    return out

  logging.info('Calculating question aggregate metrics.')
  outcome_counts = collections.Counter()
  net_metrics = {
      'num_predictions': 0,
      'questions_passed': 0,
      'num_questions': len(question_results)
  }
  individual_question_metrics = []

  for question_result in question_results.values():
    q_metrics = calculate_question_metric(question_result)
    for outcome in PredictionOutcome:
      outcome_counts[str(outcome)] += q_metrics[str(outcome)]

    net_metrics['num_predictions'] += q_metrics['num_predictions']
    net_metrics['questions_passed'] += question_result.has_result(
        PredictionOutcome.PASSED)

    individual_question_metrics.append(q_metrics)

  net_metrics['questions_passed_pct'] = (  # type: ignore
      net_metrics['questions_passed'] / len(question_results)) * 100
  return {**net_metrics, **outcome_counts}, individual_question_metrics


def calculate_pass_metrics(
    question_results: Dict[str, QuestionResult],
    seed: int,
    k_vals: List[int],
    num_preds_per_question: int,
    subsampling_rounds: int,
    subsampling_iter_per_round: int,
    shuffle: bool,
):
  """Calculates the pass@k metrics with the codex estimator and subsampling.

  Args:
    question_results: The mapping of question id to question result.
    seed: The seed to use for randomization.
    k_vals: The k values to report.
    num_preds_per_question: The number of predictions per question.
    subsampling_rounds: The number of rounds for subsampling.
    subsampling_iter_per_round: The number of iterations to do for each round.
    shuffle: If true, shuffle the set of results (by question) at the start of
      each subsampling round.

  Returns:
    The pass@k metrics. Those calculated by the codex estimator are prefixed
    with "estimator_" and those from subsampling are calculated are prefixed
    with "subsampling_".
  """
  logging.info('Calculating pass@k values for %d questions.',
               len(question_results))
  logging.debug('Creating the passing values nested arrays')

  pass_val_arrays = []
  for question in question_results.values():
    if len(question) < num_preds_per_question:
      logging.debug('Padding %s', question.id)
      pass_arr = question.padded(PredictionOutcome.PASSED,
                                 num_preds_per_question, False)
    else:
      pass_arr = question.results[PredictionOutcome.PASSED]
    pass_val_arrays.append(pass_arr)

  passed_counts = list(map(sum, pass_val_arrays))
  out = {}
  logging.debug('Setting seed=%d', seed)

  for k in k_vals:
    if k > num_preds_per_question:
      logging.warning(
          'Skipping k=%d because num_preds_per_question=%d (not enough predictions)',
          k, num_preds_per_question)
      out[f'estimate_pass@{k}'] = None  # type: ignore
      out[f'subsampling_pass@{k}'] = None  # type: ignore
      out[f'subsampling_pass@{k}_var'] = None  # type: ignore
      continue
    estimator_values = []
    for results_for_question in passed_counts:
      estimator_values.append(
          pass_at_k_estimator(
              n=num_preds_per_question, c=results_for_question, k=k))

    # Cast to float for later serialization.
    estimated_pass_at_k = float(np.mean(estimator_values) * 100)
    out[f'estimate_pass@{k}'] = estimated_pass_at_k  # type: ignore

    subsampled_pass_at_k = calculate_subsampling_passes(
        np.array(pass_val_arrays),
        k,
        subsampling_rounds=subsampling_rounds,
        subsampling_iter_per_round=subsampling_iter_per_round,
        seed=seed,
        shuffle=shuffle)

    out[f'subsampling_pass@{k}'] = np.mean(subsampled_pass_at_k)
    out[f'subsampling_pass@{k}_var'] = float(subsampled_pass_at_k.var())

  return out


def _group_execution_results_by_question(
    raw_results: List[data_types.ExecutionResult], question_data: Dict[str, Any]
) -> Tuple[int, Dict[str, data_types.PredictionResult]]:
  """Groups the raw execution results into a set of prediction results by question id.

  Args:
    raw_results: The list of raw execution results.
    question_data: The information for each question.

  Returns:
    The number of predictions ran and the grouped prediction results.
  """
  preds_by_question = collections.defaultdict(list)
  num_predictions_ran = len(raw_results)
  # Define this variable here for latter debugging of potential parsing errors.
  num_parsed = 0
  for result in raw_results:
    pred_result = PredictionResult.from_execution_result(
        result, question_data[result.prediction.qid])
    preds_by_question[pred_result.qid].append(pred_result)

    num_parsed += 1
    if num_parsed % 5000 == 0:
      logging.info('Parsed %d results', num_parsed)
  logging.info('Finished parsing %d (expected %d) for %d questions', num_parsed,
               num_predictions_ran, len(preds_by_question))

  return num_predictions_ran, dict(preds_by_question)


def _create_question_results(
    preds_by_question: Dict[str, data_types.PredictionResult],
    question_data: Dict[str, Any], tracked_attributes: List[str],
    num_preds_per_question: int
) -> Tuple[int, Dict[str, data_types.QuestionResult]]:
  """Creates the question results for the predictions grouped by question.

  Args:
    preds_by_question: Predictions grouped by question id.
    question_data: The underlying question data.
    tracked_attributes: The attributes of PredictionResult to keep track of.
    num_preds_per_question: The number of predictions per question.

  Returns:
    The maximum predictions found for a single question, used for padding and
    the mapping of question id to question result.
  """
  question_results = {}
  max_preds = num_preds_per_question
  logging.info('Creating %d question results...', len(preds_by_question))
  completed = 0
  for qid, preds in preds_by_question.items():
    question_results[qid] = QuestionResult.from_pred_results(
        qid=qid,
        lang=preds[0].lang,
        num_test_cases=len(question_data[qid]['test_case_ids']),
        pred_result_list=preds,
        tracked_attributes=tracked_attributes)
    max_preds = max(max_preds, len(preds))
    completed += 1
    if completed % 2500 == 0:
      logging.info('%d/%d finished.', completed, len(preds))

  logging.debug('max_preds=%d', max_preds)
  return max_preds, question_results


@gin.configurable(
    'metrics', denylist=['raw_results', 'question_data', 'seed', 'runtime'])
def calculate_metrics_from_raw_results(
    raw_results: List[data_types.ExecutionResult],
    question_data: Dict[str, Any],
    runtime: str,
    seed: int,
    k_vals: List[int],
    num_preds_per_question: int,
    tracked_pred_attrs: List[str],
    subsampling_rounds: int = 10,
    subsampling_iter_per_round: int = 10,
    shuffle: bool = True,
    include_outcome_pct: bool = True):
  """Calculate metrics from the raw execution results.

  Args:
    raw_results (List[data_types.ExecutionResult]): The raw execution results.
    question_data (Dict[str, Any]): The question specific data.
    runtime (str): The net runtime of the entire execution.
    seed (int): The seed to use.
    k_vals (List[int]): The k values to use for pass@k
    num_preds_per_question (int): The number of predictions per question. If
      more or found or some questions have too few predictions, then their
      passed counts will be padded with False for pass@k calculation.
    tracked_pred_attrs (List[str]): The list of PredictionResult attributes to
      track and report mean and median for.
    subsampling_rounds (int, optional): Number of rounds for the subsampling
      pass@k values.
    subsampling_iter_per_round: Number of iterations per round for the
      subsampling pass@k values.
    shuffle (bool, optional): Shuffle before subsampling. Defaults to True.
    include_outcome_pct (bool, optional): Include percentages for each outcome.
      Defaults to True.

  Returns:
    The metrics dict for the raw results.
  """
  logging.info('Calculating metrics from %d results', len(raw_results))
  logging.debug('%d number of predictions per question.',
                num_preds_per_question)

  num_predictions_ran, preds_by_question = _group_execution_results_by_question(
      raw_results=raw_results, question_data=question_data)
  max_preds, question_results = _create_question_results(
      preds_by_question=preds_by_question,
      question_data=question_data,
      tracked_attributes=tracked_pred_attrs,
      num_preds_per_question=num_preds_per_question)

  # Calculate overall metrics
  net_metrics, question_metrics = calculate_question_aggregate_metrics(
      question_results=question_results, tracked_attributes=tracked_pred_attrs)

  if include_outcome_pct:

    # Calculate the pct stats for all of the prediction outcomes excluding
    # passed, as that is equal to the estimate pass@1 value.
    logging.info('Calculating percentages for prediction outcomes...')
    for outcome in PredictionOutcome:
      if outcome == PredictionOutcome.PASSED:
        continue

      new_key = f'{str(outcome)}_pct'
      net_metrics[new_key] = net_metrics[str(  # type:ignore
          outcome)] / num_predictions_ran * 100

  pass_metrics = calculate_pass_metrics(
      question_results=question_results,
      seed=seed,
      num_preds_per_question=max_preds,
      k_vals=k_vals,
      subsampling_rounds=subsampling_rounds,
      subsampling_iter_per_round=subsampling_iter_per_round,
      shuffle=shuffle)

  net_metrics = {**net_metrics, **pass_metrics}

  net_metrics['total_runtime'] = runtime

  prediction_results = []
  for p in preds_by_question.values():
    prediction_results.extend(p)

  return net_metrics, question_metrics, prediction_results


@gin.configurable(denylist=['lang_metrics', 'question_metrics', 'language'])
def format_output_metrics(
    lang_metrics: Dict[str, Dict[str, Any]],
    question_metrics: List[Dict[str, Any]],
    language: str,
    question_key_format: str = '{language}/question/{question_id}',
    language_key_format: str = '{language}/{field}',
):
  """Format the language metrics and questions metrics for saving.

  Args:
      lang_metrics (Dict[str, Dict[str, Any]]): The language overall metrics.
      question_metrics (List[Dict[str, Any]]): The question specific metrics.
      language (str): The name of the language.
      question_key_format (str, optional): The formatting template to use for
        the question keys. Must have language and question_id in it. Defaults to
        '{language}/question/{question_id}'.
      language_key_format (str, optional): The formatting template to use for
        the overall key. Must have language and field in it. Defaults to
        '{language}/{field}'.

  Returns:
    The dict with the language metrics and the question metrics using their
    respective key format.
  """

  # Create the initial output dict from the language metrics dict.
  formatted_metrics = {
      language_key_format.format(language=language, field='metrics'):
          lang_metrics
  }

  for question_result in question_metrics:
    key = question_key_format.format(
        language=language, question_id=question_result['qid'])
    formatted_metrics[key] = question_result

  return formatted_metrics
