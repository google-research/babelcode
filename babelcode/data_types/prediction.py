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

"""Prediction data type for storing information about a prediction."""
import dataclasses
import pathlib
from typing import Dict, Optional, Union


@dataclasses.dataclass(frozen=True)
class Prediction:
  """A prediction program to run for a given question.

  Each prediction has its own prediction object that is
  created for it. It stores attributes about it such as
  where the raw code is, prediction id, etc. It is
  frozen so that it can never be changed later in the
  pipeline.

  Attributes:
    id: The id of this prediction.
    qid: The id of the question this prediction is for.
    lang: The name of the language this prediction is in.
    code: The predicted program.
    file_path: The file path where the full testing code along with the program
      are saved.
    entry_fn_name: If this is not None, the name of the function to use as the
      entry point for the prediction.
    entry_cls_name: If this is not None, the class name to use as the entry
      point for this prediction.
  """
  id: str
  qid: str
  lang: str
  code: str
  file_path: pathlib.Path
  entry_fn_name: Optional[str] = None
  entry_cls_name: Optional[str] = None

  @classmethod
  def from_dict(cls, pred_dict: Dict[str, Union[str, int]],
                file_path: pathlib.Path, default_language: str) -> 'Prediction':
    """Creates a prediction object from a dictionary.

    Args:
      pred_dict: The dictionary for the prediction.
      file_path: The path where the full testing code is located at.
      default_language: If no language is present in the dictionary, use this
        language.

    Returns:
      The created prediction object.
    """
    return cls(id=str(pred_dict['id']),
               qid=str(pred_dict['qid']),
               lang=pred_dict.get('language', default_language),
               code=pred_dict['code'],
               entry_fn_name=pred_dict.get('entry_fn_name', None),
               entry_cls_name=pred_dict.get('entry_cls_name', None),
               file_path=file_path)

  def to_dict(self) -> Dict[str, Union[str, int, None]]:
    """Serializes the prediction to a dict.

    Returns:
      The dictionary version of the prediction with file_path serialized
      properly.
    """
    self_dict = dataclasses.asdict(self)

    # pathlib.Path is not JSON serializable
    self_dict['file_path'] = str(self.file_path.resolve().absolute())

    return self_dict
