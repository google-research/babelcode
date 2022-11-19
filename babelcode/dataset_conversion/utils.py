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

"""Utilities for the dataset conversion module."""

import ast

# Dict to hold mapping of primitives to their generic form
PRIMITIVE_TYPES_TO_GENERIC = {
    'int': 'integer',
    'str': 'string',
    'bool': 'boolean',
    'float': 'float'
}


class AnnotationError(Exception):
  """Invalid type annotation."""


def convert_to_source(node: ast.AST) -> str:
  """Convert an AST node to its respective source code.

  Args:
      node (ast.AST): The node to convert.

  Returns:
      The raw code.
  """
  return ast.unparse(node).rstrip()
