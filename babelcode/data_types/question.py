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
"""Question data type."""

import copy
import dataclasses
import json
import pathlib
from typing import Any, Dict, List, Optional, Tuple, Union

from absl import logging

from babelcode import utils


class IOPairError(Exception):
  """Error when parsing or using an IO Pair."""


class QuestionParsingError(Exception):
  """Error with parsing a question."""


class QuestionValidationError(Exception):
  """Error with validating a question."""


# The required keys for a question dict.
REQUIRED_KEYS = ['qid', 'title', 'schema', 'test_list', 'entry_fn_name']

EXPECTED_KEY_NAME = 'EXPECTED_OUTPUT_TYPE'


@dataclasses.dataclass
class Question:
  """Dataclass for a programming question from a dataset.

  Attributes:
    qid: The question id
    title: The title of the question
    schema: The schema for the question.
    test_list: The Test cases for the question
    entry_fn_name: The default entry function name to use.
    entry_cls_name: The default entry class name to use for the question if the
      language requires it (i.e. Java)
    text: The natural language description for the question.
    allow_arbitrary_order: Allow results to be arbitrary ordered.
    use_type_annotation: Use type annotation when generating prompts.
    metadata: The metadata dict for the question.
    challenge_test_list: The list of challenge test cases.
    solutions: The mapping of languages to the solution code, if it exists.
  """

  qid: str
  title: str
  schema: Dict[str, Union[List[Dict[str, str]], Dict[str, str]]]
  # The full type would be something along the lines of:
  # `List[Dict[str,Union[bool,float,str,int,List[Union[bool,float,str,int,Dict...]]]]]`.
  # As types such as Lists and Maps can be nested to depth `n`, there is not
  # really a good type to put but `Any`.
  test_list: List[Dict[str, utils.TestValueType]]
  entry_fn_name: str
  entry_cls_name: str = 'Solution'
  text: Optional[str] = None
  allow_arbitrary_order: bool = False
  use_type_annotation: bool = False
  metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
  challenge_test_list: List[Dict[str, utils.TestValueType]] = dataclasses.field(
      default_factory=list)
  solutions: Optional[Dict[str, str]] = dataclasses.field(default_factory=dict)

  def __len__(self):
    return len(self.test_list)

  def __iter__(self):
    for test in self.test_list:
      yield test

  @classmethod
  def from_dict(cls,
                input_dict: Dict[str, Any],
                allow_arbitrary_order: bool = False) -> 'Question':
    """Create a question object from a dictionary.

    Args:
      input_dict: The dictionary to create a question for.
      allow_arbitrary_order: Use arbitrary ordering for checking

    Raises:
      QuestionParsingError: if the question cannot be parsed from the dict.

    Returns:
      The parsed question object.
    """
    missing_keys = [k for k in REQUIRED_KEYS if k not in input_dict]
    if missing_keys:
      raise QuestionParsingError(f'Missing required keys: {missing_keys}')

    qid = str(input_dict['qid'])
    title = input_dict['title']
    logging.info('Creating Question with id %s and title "%s"', qid, title)

    raw_schema = input_dict['schema']
    if isinstance(raw_schema, dict):
      missing_keys = [k for k in ['params', 'return'] if k not in raw_schema]
      if missing_keys:
        raise QuestionParsingError(
            f'Question {qid} is missing keys {missing_keys}')

      for i, arg in enumerate(raw_schema['params']):
        missing_keys = [k for k in ['name', 'type'] if k not in arg]
        if missing_keys:
          raise QuestionParsingError(
              f'Argument {i} of Question {qid} is missing keys {missing_keys}')

      if 'type' not in raw_schema['return']:
        raise QuestionParsingError(
            f'Question {qid} is missing "type" key in return.')

    else:
      raise QuestionParsingError(
          f'"schema" must be a dict. Not {type(raw_schema).__name__} ')
    test_list = input_dict['test_list']

    return cls(
        qid=qid,
        title=title,
        schema=raw_schema,
        test_list=test_list,
        allow_arbitrary_order=allow_arbitrary_order,
        entry_fn_name=input_dict['entry_fn_name'],
        entry_cls_name=input_dict.get('entry_cls_name', 'Solution'),
        text=input_dict.get('text', None),
        use_type_annotation=input_dict.get('use_type_annotation', False),
        metadata=input_dict.get('metadata', {}),
        challenge_test_list=input_dict.get('challenge_test_list', []),
        solutions=input_dict.get('solutions', {}),
    )

  def __str__(self) -> str:
    """Converts question to a minimal string."""
    return f'{self.qid}: {self.title}'

  def to_dict(self) -> Dict[str, Any]:
    """Converts the question to a dict."""
    self_dict = dataclasses.asdict(self)
    self_dict['test_case_ids'] = [str(t['idx']) for t in self.test_list]
    return self_dict

  def copy(self) -> 'Question':
    """Copies the question to a new object."""
    return Question(
        qid=self.qid,
        title=self.title,
        schema=copy.deepcopy(self.schema),
        test_list=copy.deepcopy(self.test_list),
        entry_fn_name=self.entry_fn_name,
        entry_cls_name=self.entry_cls_name,
        text=self.text,
        metadata=copy.deepcopy(self.metadata),
        challenge_test_list=copy.deepcopy(self.challenge_test_list),
        allow_arbitrary_order=self.allow_arbitrary_order,
        use_type_annotation=self.use_type_annotation,
    )

  def change_var_names(self, name_map: Dict[str, str]) -> None:
    """Changes the variable name by updating the tests and schema.

    Args:
      name_map: The mapping of old names to new names.

    Raises:
      QuestionValidationError: If the old name is missing.
    """

    def _update_test(test_dict):
      for old_name, new_name in name_map.items():
        if old_name not in test_dict['inputs']:
          raise QuestionValidationError(
              f'Test case {test_dict["idx"]} in question {self.qiq} does not'
              f' have input {old_name}')

        test_dict['inputs'][new_name] = test_dict['inputs'].pop(old_name)

      return test_dict

    for i in range(len(self.test_list)):
      self.test_list[i] = _update_test(self.test_list[i])

    for i in range(len(self.challenge_test_list)):
      self.challenge_test_list[i] = _update_test(self.challenge_test_list[i])
    logging.info('Renaming %s variables with map=%s', self.qid, name_map)
    found = set()
    for i, arg in enumerate(self.schema['params']):
      if arg['name'] in name_map:
        old_name = arg['name']
        self.schema['params'][i]['name'] = name_map[old_name]
        found.add(old_name)
    if found != set(name_map.keys()):
      raise QuestionValidationError(
          f'Could not find variable(s) {found.difference(set(name_map.keys()))}'
      )


def read_input_questions(
    input_path: pathlib.Path,
) -> Tuple[List[Question], List[Tuple[Dict[str, Any], Exception]]]:
  """Read and parse questions from an input file.

  This reads and parses the questions from a given json lines file. If it fails
  to parse a given line, it adds that to the list of failed lines and returns
  them with

  Args:
    input_path: The path the to the questions json lines file.

  Raises:
    json.JSONDecodeError: The line is not valid JSON.

  Returns:
    The list of questions.
  """
  logging.info('Reading questions from file "%s"', input_path)
  found_questions = []
  failed_line_dicts = []
  for line_number, raw_line in enumerate(input_path.open('r')):
    # Because we are reading a json lines file, we check to try-except the
    # decoding of the line so we can provide better debugging information to the
    # user. Otherwise, using map(json.loads,file) would say that the line number
    # where the error occurred is always 1 as it only ever sees a single line at
    # a time.
    try:
      line = json.loads(raw_line)
    except json.JSONDecodeError as e:
      logging.exception('Line %s is not valid JSON for reason "%s"',
                        line_number, e)
      raise json.JSONDecodeError(
          f'Invalid JSON line: {line_number}, error={e}',
          doc=line,
          pos=line_number,
      )

    try:
      found_questions.append(Question.from_dict(line, False))

    # In the case a line is missing keys, we do not want to cause the entire
    # program to fail. So we add it to the list of lines that failed. The only
    # way that `from_dict` could raise a `KeyError` is if a required key for a
    # question is missing. Rather than adding a lot of
    # `if x in line ... else raise QuestionError` for each required key, it is
    # easier to check for the `KeyError``.
    except QuestionParsingError as e:
      failed_line_dicts.append((line, e))
      logging.warning('Line %s failed to parse with reason %s', line_number, e)

  return found_questions, failed_line_dicts
