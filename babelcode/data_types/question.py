"""Question data type."""

import dataclasses
import json
import pathlib
from typing import Any, Dict, List, Optional, Tuple

from absl import logging
from importlib_metadata import metadata

from babelcode import utils


class IOPairError(Exception):
  """Error when parsing or using an IO Pair."""


class QuestionParsingError(Exception):
  """Error with parsing a question."""


class QuestionValidationError(Exception):
  """Error with validating a question."""


# The required keys for a question dict.
REQUIRED_KEYS = ['question_id', 'title', 'schema', 'test_list', 'entry_fn_name']


# TODO(gabeorlanski): Change schema from list to dict.
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
  """
  qid: str
  title: str
  schema: List[Dict[str, Dict[str, str]]]
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

    qid = str(input_dict['question_id'])
    title = input_dict['title']
    logging.info('Creating Question with id %s and title "%s"', qid, title)

    raw_schema = input_dict['schema']
    if isinstance(raw_schema, dict):
      try:
        # Add the expected return type to the schema.
        raw_schema = raw_schema['params'] + [{
            'name': 'expected',
            **raw_schema['return']
        }]
      except KeyError as e:
        raise QuestionParsingError(f'Question {qid} is missing keys {e}') from e
    elif isinstance(raw_schema, list):
      found_expected = False
      for v in raw_schema:
        if not isinstance(v, dict):
          raise QuestionParsingError(
              f'{qid}: Found a non-dict in the schema list: {v}')
        if 'name' not in v or 'type' not in v:
          raise QuestionParsingError(
              f'{qid}: Missing either name or type in the schema list')

        if v['name'] == 'expected':
          found_expected = True
      if not found_expected:
        logging.error('%s: is missing an expected value', qid)
        raise QuestionParsingError(
            'There must be a value in the schema list with name="expected"')
    else:
      raise QuestionParsingError(
          f'"schema" must be a dict or list. Not {type(raw_schema).__name__} ')
    test_list = input_dict['test_list']

    return cls(qid=qid,
               title=title,
               schema=raw_schema,
               test_list=test_list,
               allow_arbitrary_order=allow_arbitrary_order,
               entry_fn_name=input_dict['entry_fn_name'],
               entry_cls_name=input_dict.get('entry_cls_name', 'Solution'),
               text=input_dict.get('text', None),
               use_type_annotation=input_dict.get('use_type_annotation', False),
               metadata=input_dict.get('metadata', {}),
               challenge_test_list=input_dict.get('challenge_test_list', []))

  def __str__(self) -> str:
    """Convert question to a minimal string."""
    return f'{self.qid}: {self.title}'

  def to_dict(self) -> Dict[str, Any]:
    """Convert the question to a dict."""
    self_dict = dataclasses.asdict(self)
    self_dict['test_case_ids'] = [str(t['idx']) for t in self.test_list]
    return self_dict


def read_input_questions(
    input_path: pathlib.Path
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
      raise json.JSONDecodeError(f'Invalid JSON line: {line_number}, error={e}',
                                 doc=line,
                                 pos=line_number)

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
