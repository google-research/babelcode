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
""" Makes the data files for use in HF datasets. """
import argparse
import collections
import json
import shutil
from pathlib import Path

parser = argparse.ArgumentParser("Make HF Datasets")
parser.add_argument("data_path", type=str, help="Path to the parsed datasets.")
parser.add_argument("output_path", type=str, help="Path to save to.")

SUPPORTED_DS = {"human_eval", "mbpp", "tp3", "transcoder"}

PROMPT_KEYS_TO_KEEP = {
    "signature", "signature_with_docstring", "text", "entry_fn_name",
    "entry_cls_name", "arguments"
}
CODE_KEYS_TO_KEEP = {"title", "test_code", "test_list", "test_case_ids"}

RAW_QUESTION_DIR = Path("data/raw_datasets")


def main(args):
  data_path = Path(args.data_path)
  out_path = Path(args.output_path)
  shutil.rmtree(out_path, ignore_errors=True)
  out_path.mkdir()
  print(f"Creating HF Datasets from parsed datasets located at '{data_path}'")

  for dir_found in data_path.glob("*"):

    code_map = collections.defaultdict(dict)
    prompt_map = collections.defaultdict(dict)
    print(f"Parsing {dir_found}")
    ds_name = dir_found.stem
    if ds_name not in SUPPORTED_DS:
      print(f"{ds_name} is not supported...")
      continue
    raw_question_dir = RAW_QUESTION_DIR.joinpath(f'{ds_name}_questions.jsonl')
    question_solutions = {}
    for l in map(json.loads, raw_question_dir.open()):
      question_solutions[l['id']] = {'solution_python': l['solution']}
      if 'other_lang_solutions' in l:
        for lang, s in l['other_lang_solutions'].items():
          if lang == "C++":
            lang = 'cpp'
          question_solutions[l['id']][f'solution_{lang}'] = s

    for line in map(json.loads,
                    dir_found.joinpath("testing_code.jsonl").open()):
      code_map[line['language']][line['qid']] = line

    for line in map(json.loads, dir_found.joinpath("prompt_info.jsonl").open()):
      prompt_map[line['language']][line['qid']] = line

    assert set(prompt_map.keys()) == set(code_map.keys())
    out = []
    for language in prompt_map.keys():
      prompts = prompt_map[language]
      codes = code_map[language]
      assert set(codes.keys()) == set(prompts.keys())

      for q in codes.keys():
        q_dict = {"qid": q, "language": language}

        for k in PROMPT_KEYS_TO_KEEP:
          q_dict[k] = prompts[q][k]
        for k in CODE_KEYS_TO_KEEP:
          q_dict[k] = codes[q][k]

        q_dict.update(question_solutions[q])
        out.append(q_dict)
    print(f"Found {len(out)} questions")
    with out_path.joinpath(f'{ds_name}.jsonl').open('w') as f:
      for p in out:
        f.write(json.dumps(p) + '\n')


if __name__ == "__main__":
  main(parser.parse_args())
