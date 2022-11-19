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

"""Utilities for translation."""


def escape_triple_quotes(seq: str) -> str:
  """Escapes the triple quotes sequence."""
  return seq.replace('"""', '\\"\\"\\"')


def escape_cpp_like_comment_chars(seq: str) -> str:
  """Escapes the characters for C++ like comments."""
  seq = seq.replace('*/', '\\*/')
  seq = seq.replace('/*', '/\\*')
  seq = seq.replace('/', '\\/')
  return seq


def format_cpp_like_docstring(docstring: str, join_seq: str = '\n') -> str:
  """Formats a docstring for C++ style formatting."""
  out = ['/**']
  for line in docstring.splitlines(False):
    prefix = ' * '
    out.append(f'{prefix}{line}')
  out.append(' */')
  return join_seq.join(out)
