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
"""Initialization of the Code Generation module."""
from babelcode.translation.literal_translator import LiteralTranslator
from babelcode.translation.primitive_translator import convert_float
from babelcode.translation.primitive_translator import convert_string
from babelcode.translation.primitive_translator import make_primitive_translator
from babelcode.translation.prompt_translator import PromptTranslator
from babelcode.translation.utils import escape_cpp_like_comment_chars
from babelcode.translation.utils import escape_triple_quotes
from babelcode.translation.utils import format_cpp_like_docstring
