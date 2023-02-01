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

"""Makes error code from a evaluation result for debugging."""
import argparse
import collections
import json
import random
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path().parent

if str(Path(__file__).parents[1]) not in sys.path:
  sys.path.insert(0, str(Path(__file__).parents[1]))

from babelcode.languages import LanguageRegistry

defaultdict = collections.defaultdict

parser = argparse.ArgumentParser(
    description='Makes error code from a evaluation result for debugging.')
parser.add_argument('dataset', help='Name of the dataset.')
parser.add_argument('pred_results', type=Path, help='Prediction Results File.')
parser.add_argument('output_path', type=Path, help='Path to save results.')
parser.add_argument(
    '--n_per_question',
    '-n',
    type=int,
    default=1,
    help='Number of predictions to generate per question.')
parser.add_argument(
    '--num_questions',
    '-q',
    type=int,
    default=-1,
    help='Max number of questions to print.')
parser.add_argument('--seed', type=int)
parser.add_argument(
    '--include_failed',
    default='',
    help='Comma Separated list of languages to include predictions who failed tests.'
)

OUTCOME_TO_WRITE = ['Had Error', 'Had Runtime Error', 'Timed Out']


def main(dataset, pred_results, output_path: Path, num_to_save_per_question,
         num_questions_to_print, lang_include_failed):
  dataset_path = PROJECT_ROOT.joinpath('data', 'problem_code', dataset,
                                       'testing_code.jsonl')
  testing_code = {
      f'{l["language"]}/{l["qid"]}': l
      for l in map(json.loads, dataset_path.open())
  }
  lang_include_failed = lang_include_failed.split(',')
  pred_failures_by_question = defaultdict(lambda: defaultdict(dict))
  for l in map(json.loads, pred_results.open()):
    outcome = l['outcome']
    if outcome not in OUTCOME_TO_WRITE:
      if outcome != 'Failed Tests':
        continue
      else:
        if l['language'] not in lang_include_failed:
          continue

    lang, qid = l['language'], l['qid']
    if outcome not in pred_failures_by_question[lang][qid]:
      pred_failures_by_question[lang][qid][outcome] = []
    pred_failures_by_question[lang][qid][outcome].append(l)
  print((
      f'{sum(map(len,pred_failures_by_question.values()))} questions found with'
      + f' an error across {len(pred_failures_by_question)} languages'))

  output_path = output_path.joinpath(dataset)

  if output_path.exists():
    shutil.rmtree(output_path)

  output_path.mkdir(parents=True)

  for lang_name, question_errors in pred_failures_by_question.items():
    print('\n' + '=' * 80)
    print(lang_name)
    lang_path = output_path.joinpath(lang_name)
    lang_path.mkdir()
    language = LanguageRegistry.get_language(lang_name)

    qids_to_print = list(question_errors)
    if num_questions_to_print != -1:
      qids_to_print = random.sample(
          qids_to_print, k=min(len(qids_to_print), num_questions_to_print))

    for qid in qids_to_print:
      outcomes = question_errors[qid]
      print(f'{qid=}')
      print('# Outcomes by type:')
      for outcome in OUTCOME_TO_WRITE:
        print(f'\t{outcome} = {len(outcomes.get(outcome,[]))}')
      test_code_data = testing_code[f'{lang_name}/{qid}']
      test_code = test_code_data['test_code']

      test_code = test_code.replace('PLACEHOLDER_FN_NAME',
                                    test_code_data['entry_fn_name'])
      test_code = test_code.replace('PLACEHOLDER_CLS_NAME',
                                    test_code_data['entry_cls_name'])

      for outcome, q_list in outcomes.items():
        to_save = random.sample(
            q_list, k=min(num_to_save_per_question, len(q_list)))
        for p in to_save:
          filename = f'{p["qid"]}_{p["id"]}_{p["outcome"].replace(" ","_")}'
          print(f'Saving {filename}')
          with lang_path.joinpath(f'stderr.{filename}').open('w') as f:
            f.write(p['stderr'])
          with lang_path.joinpath(f'{filename}.{language.file_ext}').open(
              'w') as f:
            code = test_code.replace('PLACEHOLDER_CODE_BODY', p['code'])
            f.write(code)


if __name__ == '__main__':
  args = parser.parse_args()
  random.seed(args.seed)
  main(args.dataset, args.pred_results, args.output_path, args.n_per_question,
       args.num_questions, args.include_failed)
