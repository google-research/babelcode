"""Command data type."""
import dataclasses
from typing import List


@dataclasses.dataclass
class Command:
  """The bash command to execute along with the timeout to use with it.

  The command needs to be formatted as a list of arguments for it to work with
  the subprocess shell. For example the command `rm -rf dir` would be passed as
  `["rm","-rf","dir"]`.

  Attributes:
    command: The string command to run.
    timeout: The timeout to use with the command. Defaults to 10.
  """
  command: List[str]
  timeout: int = 10
