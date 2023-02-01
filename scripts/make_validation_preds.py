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

"""Makes the validation predictions for testing that the literals can be parsed correctly."""
import collections
import json
import pathlib
import sys

from absl import app
from absl import flags

PROJECT_ROOT = pathlib.Path().parent

if str(pathlib.Path(__file__).parents[1]) not in sys.path:
  sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

from babelcode import languages
from babelcode import schema_parsing

_NAME = flags.DEFINE_string('name',
                            None,
                            required=True,
                            help="Name of the dataset this is for validating.")
_TEST_CODE_PATH = flags.DEFINE_string('problem_code_path',
                                      None,
                                      required=True,
                                      help="Path to where the problem code is.")
_OUT_PATH = flags.DEFINE_string('output_path',
                                None,
                                required=True,
                                help="Path to save.")


def make_pred_dict(qid, pid, code, lang):
  return {'qid': qid, 'id': pid, 'code': code, 'language': lang}


def group_by_lang(generator):
  out = collections.defaultdict(dict)
  for line in generator:
    out[line['language']][line['qid']] = line
  return out


def main(_):
  ds_name = _NAME.value
  print(f'Making validation predictions for {ds_name}')
  fixtures_path = PROJECT_ROOT.joinpath('test_fixtures', 'language_data')
  test_code = pathlib.Path(_TEST_CODE_PATH.value)
  prompt_info = group_by_lang(
      map(json.loads,
          test_code.joinpath('prompt_info.jsonl').open()))
  question_info = group_by_lang(
      map(json.loads,
          test_code.joinpath('testing_code.jsonl').open()))

  assert set(prompt_info.keys()) == set(question_info.keys())
  print(f'Languages found: {list(prompt_info)}')

  validation_preds = []
  print('Checking for golden predictions')
  golden_path = PROJECT_ROOT.joinpath('data', 'golden_predictions',
                                      f'{ds_name}.jsonl')
  if golden_path.exists():
    print('Golden Predictions found')
    golden_predictions = group_by_lang(map(json.loads, golden_path.open()))

    for lang, preds in golden_predictions.items():
      print(f'Replacing validation preds for {lang} with golden...')
      for qid, pred in preds.items():
        validation_preds.append(pred)
        if qid in prompt_info[lang]:
          prompt_info[lang].pop(qid)

  for lang, prompt_map in prompt_info.items():
    if not prompt_map:
      continue
    print(f'Generating {len(prompt_map)} validation predictions for {lang}...')
    language = languages.LanguageRegistry.get_language(lang)
    translator = language.make_literal_translator()
    func_template = fixtures_path.joinpath(lang,
                                           'func_template.txt').read_text()
    question_map = question_info[lang]
    language_spec = schema_parsing.LanguageSchemaSpecRegistry.get_lang_spec(
        lang)
    for qid, prompt in prompt_map.items():
      question_data = question_map[qid]

      schema, _ = schema_parsing.parse_schema_and_input_order(
          language_spec, question_data['schema'])
      return_type = schema['expected']
      return_value = question_data['test_list'][0]['outputs']

      return_code = translator.convert_var_to_literal(return_type, return_value)
      signature = prompt['signature_with_docstring'] or prompt['signature']
      input_code = func_template.replace('FN_SIGNATURE', signature)
      input_code = input_code.replace('RETURN_VALUE', return_code)
      validation_preds.append(make_pred_dict(qid, '1', input_code, lang))

  out_path = pathlib.Path(_OUT_PATH.value)
  if not out_path.exists():
    out_path.mkdir(parents=True)
  print(f'Saving {len(validation_preds)} to {out_path}')
  with out_path.joinpath(f'{ds_name}.jsonl').open('w') as f:
    f.write('\n'.join(map(json.dumps, validation_preds)))


if __name__ == "__main__":
  app.run(main)
