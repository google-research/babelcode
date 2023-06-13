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
"""Script to convert a python dataset to a parsed version.

Usage:
python convert_dataset.py --dataset_name="$DATASET_NAME" --input_path="$DATASET_LOCATION" 
"""
# pylint: disable=logging-fstring-interpolation
import collections
import copy
import dataclasses
import json
import pathlib
from typing import Any, Dict, Optional

from absl import app
from absl import flags
from absl import logging
from babelcode import utils
from babelcode.dataset_conversion import parse_question_dict
from babelcode.dataset_conversion import POTENTIAL_ERROR_TYPES
from babelcode.languages import LanguageRegistry

Path = pathlib.Path


@dataclasses.dataclass
class RawQuestion:
  """Dataclass used to validate that the keys for each lin in the input file."""
  id: str
  title: str
  testing_code: str
  entry_fn_name: str
  solution: str
  text: Optional[str] = None
  entry_cls_name: str = 'Solution'
  metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
  other_lang_solutions: Dict[str, str] = dataclasses.field(default_factory=dict)


def convert_raw_questions(read_questions: Dict[str, Dict[str, Any]],
                          fixes: Dict[str, Dict[str, Any]]):
  """Convert a dictionary of raw questions into the parsed form.

  Args:
    read_questions: The map of question id to raw question object.
    fixes: The question specific fixes to use.

  Returns:
    The map of question id to the parsed questions and the failures.
  """

  # Make the raw question map
  raw_question_map = {}
  other_languages = set()
  for qid, raw_question in read_questions.items():
    fix = fixes.pop(qid, {})
    raw_question.update(fix)
    try:
      raw_question_map[qid] = RawQuestion(**raw_question)
      other_languages.update(list(raw_question_map[qid].other_lang_solutions))
    except ValueError as e:
      raise ValueError(f'qid={qid} does not have correct keys.') from e

  logging.info('Found additional solutions in %s', other_languages)
  other_languages = {
      k: LanguageRegistry.get_language(k) for k in other_languages
  }
  # Parse each question of the dataset
  failed_to_parse = collections.defaultdict(list)
  parsed_questions = {}
  logging.info('Starting conversion...')
  for qid, raw_question in raw_question_map.items():
    try:
      parsed_question = parse_question_dict(
          qid=qid,
          testing_code=raw_question.testing_code,
          solution=raw_question.solution,
          entry_fn_name=raw_question.entry_fn_name,
      )
    except POTENTIAL_ERROR_TYPES as e:
      logging.warning(f'Question {qid} failed to parse with error {e}')
      failed_to_parse[type(e).__name__].append((str(e), qid))
      continue

    parsed_question = {
        'qid': raw_question.id,
        'title': raw_question.title,
        'entry_cls_name': raw_question.entry_cls_name,
        'text': raw_question.text,
        'metadata': raw_question.metadata,
        **parsed_question,
    }

    old_entry_point = parsed_question['entry_fn_name']
    new_entry_point = utils.format_str_with_convention(
        utils.NamingConvention.SNAKE_CASE, parsed_question['entry_fn_name'])

    solutions = {}
    for lang, sol in raw_question.other_lang_solutions.items():
      lang_name = utils.format_str_with_convention(
          other_languages[lang].naming_convention, old_entry_point)
      solutions[lang] = sol.replace(old_entry_point, lang_name)
    solutions['Python'] = raw_question.solution.replace(old_entry_point,
                                                        new_entry_point)
    parsed_question['solutions'] = solutions
    parsed_question['entry_fn_name'] = new_entry_point
    gold_predictions = []
    for lang, sol in solutions.items():
      gold_predictions.append({
          'qid': raw_question.id,
          'id': 0,
          'code': sol,
          'language': lang,
          'testing_code': '',
          'text': raw_question.text
      })
    parsed_questions[raw_question.id] = (parsed_question, gold_predictions)
  return parsed_questions, failed_to_parse


def convert_dataset(
    dataset_name: str,
    input_path: Path,
    debug: bool,
    disable_fixes: bool = False,
    debug_question: str = None,
):
  """Converts a dataset to BabelCode format.

  Args:
    dataset_name: Name of the dataset.
    input_path: The input path of the dataset.
    debug: Enable debugging.
    disable_fixes: Disable the use of fixes.
    debug_question: Debug a specific quesiton id.
  """
  print('Starting Dataset Conversion.')
  output_path = utils.PROJECT_ROOT.joinpath('data')
  utils.setup_logging(f'convert_{dataset_name}', debug=debug)
  logging.info('Converting %s located at "%s"', dataset_name, input_path)
  fixes = {}
  if not disable_fixes:
    fix_file_path = utils.PROJECT_ROOT.joinpath('data', 'dataset_fixes',
                                                f'{dataset_name}.jsonl')
    if fix_file_path.exists():
      logging.info('Using fixes file located at %s', fix_file_path)
      for line_number, line in enumerate(fix_file_path.open()):
        try:
          line = json.loads(line)
        except json.JSONDecodeError as e:
          # Loading each line in the json file will not provide good debug
          # information. So we print the line number if a line failed.
          logging.error('Line %s had json error', line)
          logging.error('line=%d', line_number)
          raise e
        qid = str(line.pop('id'))
        fixes[qid] = line
    else:
      logging.warning('Fixes are enabled but no fixes found at %s',
                      fix_file_path)
  else:
    logging.info('No fixes passed')

  logging.info('Reading questions')
  raw_question_map = {}
  for line_number, line in enumerate(map(json.loads, input_path.open())):
    raw_question_map[line['id']] = line
    if len(raw_question_map) % 50 == 0:
      logging.info('Found %d questions', len(raw_question_map))
  logging.info(
      '%d raw questions found after reading %s',
      len(raw_question_map),
      input_path,
  )
  logging.info(
      '%d fixes were unused.',
      sum(1 for q in fixes if q not in raw_question_map),
  )

  if debug_question:
    logging.warning('Only parsing debug_question=%s', debug_question)
    raw_question_map = {debug_question: raw_question_map[debug_question]}

  parsed_questions, failed_to_parse = convert_raw_questions(
      raw_question_map, copy.deepcopy(fixes))
  if failed_to_parse:
    logging.warning(
        f'{sum(map(len,failed_to_parse.values()))}/{len(raw_question_map)} failed'
        ' to parse.')
  else:
    logging.info('All questions parsed successfully')

  failure_path = utils.PROJECT_ROOT.joinpath('data', 'convert_failures')
  # shutil.rmtree(failure_path,ignore_errors=True)
  failure_path.mkdir(parents=True, exist_ok=True)
  logging.debug(f'Saving failures to {failure_path}')
  logging.info('Failure Count by Type:')
  with failure_path.joinpath(f'{dataset_name}.txt').open('w') as f:
    for e_type, failures in failed_to_parse.items():
      logging.info(f'{e_type:>24} = {len(failures)}')
      for reason, qid in failures:
        if qid in fixes:
          logging.error(f'The fix for {qid} failed.')
        f.write(f'Question {qid} => {e_type}: {reason}\n')

  gold_path = output_path.joinpath('golden_predictions')
  gold_path.mkdir(parents=True, exist_ok=True)
  gold_path = gold_path.joinpath(f'{dataset_name}.jsonl')
  output_path = output_path.joinpath('parsed_datasets')
  output_path.mkdir(parents=True, exist_ok=True)
  output_path = output_path.joinpath(f'{dataset_name}.jsonl')
  logging.info(f'Saving to {output_path}')
  logging.info(f'Saving golden predictions to {gold_path}')
  with gold_path.open('w') as gold_file:
    with output_path.open('w') as parsed_file:
      for qid, (parsed, gold) in parsed_questions.items():
        parsed_file.write(f'{json.dumps(parsed)}\n')
        for pred in map(json.dumps, gold):
          gold_file.write(f'{pred}\n')


if __name__ == '__main__':
  FLAGS = flags.FLAGS
  _DATASET_NAME = flags.DEFINE_string('dataset_name', None, help='Dataset name')
  _INPUT_PATH = flags.DEFINE_string('input_path', None, help='Input path')
  _DEBUG = flags.DEFINE_bool('debug', False, help='Debug')
  _DISABLE_FIXES = flags.DEFINE_bool('disable_fixes',
                                     False,
                                     help='Disable fixes')
  _DEBUG_QID = flags.DEFINE_string('debug_question',
                                   None,
                                   help='Single question id to debug.')

  def convert_main(_):
    FLAGS['alsologtostderr'].value = True
    convert_dataset(
        dataset_name=_DATASET_NAME.value,
        input_path=Path(_INPUT_PATH.value),
        disable_fixes=_DISABLE_FIXES.value,
        debug=_DEBUG.value,
        debug_question=_DEBUG_QID.value,
    )

  flags.mark_flags_as_required([_DATASET_NAME.name, _INPUT_PATH.name])
  app.run(convert_main)
