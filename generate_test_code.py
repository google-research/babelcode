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

"""Script to generate testing code for a given set of problems."""
import json
import shutil
import pathlib
from typing import Optional

from absl import app
from absl import flags
from absl import logging

from babelcode import generate_code_for_questions
from babelcode.data_types.question import read_input_questions
from babelcode.languages import LanguageRegistry
from babelcode.utils import setup_logging


def generate_problem_code_main(input_path: pathlib.Path, output_path: pathlib.Path,
                               debug_lang: Optional[str], debug: bool):
  setup_logging('generate_tests', debug)
  logging.info('Generating tests')
  logging.info(f'Reading from {input_path}')
  logging.info(f'Saving all generated tests to {output_path}')
  output_path.mkdir(parents=True, exist_ok=True)
  failures_path = output_path.joinpath('failures')
  shutil.rmtree(failures_path, True)
  failures_path.mkdir()

  questions, failed = read_input_questions(input_path=input_path)
  logging.info(f'Found {len(questions)} questions')
  if failed:
    logging.error(f'{len(failed)} failed to parse.')
  with failures_path.joinpath('read_failed.txt').open('w') as f:
    for line, reason in failed:
      f.write(f'{reason}: {json.dumps(line)}\n')

  langs_to_use = LanguageRegistry.list_languages()
  if debug_lang:
    langs_to_use = [debug_lang]

  all_questions = []
  all_prompts = []
  logging.info(f'{len(langs_to_use)} total language(s) to generate tests for')
  for lang_name in langs_to_use:
    lang = LanguageRegistry.get_language(lang_name)

    parsed, failed = generate_code_for_questions(questions=questions, lang=lang)
    for q, p in parsed:
      all_questions.append({'language': lang_name, **q})
      all_prompts.append({'language': lang_name, **p})

    with failures_path.joinpath(f'{lang_name}_failed.jsonl').open('w') as f:
      for question, reason in failed:
        f.write(
            json.dumps({
                'qid': question.qid,
                'reason': str(reason),
                'error': type(reason).__name__,
                'question': question.to_dict()
            }) + '\n')
  with output_path.joinpath('testing_code.jsonl').open('w') as f:
    logging.info(
        f'Saving questions to {output_path.joinpath("testing_code.jsonl")}')
    for p in all_questions:
      f.write(json.dumps(p) + '\n')
  with output_path.joinpath('prompt_info.jsonl').open('w') as f:
    logging.info(
        f'Saving prompt info to {output_path.joinpath("prompt_info.jsonl")}')
    for p in all_prompts:
      f.write(json.dumps(p) + '\n')


if __name__ == '__main__':
  FLAGS = flags.FLAGS

  _INPUT = flags.DEFINE_string('input', None, help='pathlib.Path to input problems.')
  _OUTPUT = flags.DEFINE_string('output', None, help='pathlib.Path to output.')
  _LANG = flags.DEFINE_string('debug_lang',
                              None,
                              help='Debug a single language')
  _DEBUG = flags.DEFINE_bool('debug', False, help='Debug')

  def main(_):
    FLAGS['alsologtostderr'].value = True
    generate_problem_code_main(pathlib.Path(_INPUT.value), pathlib.Path(_OUTPUT.value),
                               _LANG.value, _DEBUG.value)

  flags.mark_flags_as_required([_INPUT.name, _OUTPUT.name])

  app.run(main)
