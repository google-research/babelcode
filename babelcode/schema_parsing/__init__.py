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

"""Initialize the schema parsing module and register all of the languages."""
from babelcode.schema_parsing.languages import LanguageSchemaSpec
from babelcode.schema_parsing.languages import LanguageSchemaSpecRegistry
from babelcode.schema_parsing.parsing import parse_language_schema
from babelcode.schema_parsing.parsing import parse_schema_and_input_order
from babelcode.schema_parsing.schema_type import SchemaType
from babelcode.schema_parsing.schema_type import is_generic_equal
from babelcode.schema_parsing.schema_type import reconcile_type
from babelcode.schema_parsing.schema_type import validate_correct_type
from babelcode.schema_parsing.utils import PRIMITIVE_DATA_STRUCTURES
from babelcode.schema_parsing.utils import PRIMITIVE_TYPES
from babelcode.schema_parsing.utils import PRIMITIVE_WITH_NULL
from babelcode.schema_parsing.utils import RECONCILABLE_TYPES
from babelcode.schema_parsing.utils import SchemaMapType
from babelcode.schema_parsing.utils import SchemaTypeError
from babelcode.schema_parsing.utils import SchemaValueType
from babelcode.schema_parsing.utils import allows_null


def _register_specs():
  """Register the different language specifications.

  This is done here so that, when the library is used, it automatically
  registers all of the implemented languages.
  """

  # pylint: disable=g-import-not-at-top
  import inspect

  from babelcode.schema_parsing import languages

  # pylint: enable=g-import-not-at-top
  for name, make_spec_fn in inspect.getmembers(languages, inspect.isfunction):
    lang_spec = make_spec_fn()
    if not isinstance(lang_spec, LanguageSchemaSpec):
      raise TypeError(
          f'{name} must return a LanguageSchemaSpec, instead got {type(lang_spec).__name__}'
      )

    LanguageSchemaSpecRegistry.register_language(lang_spec,
                                                 allow_overwrite=True)


_register_specs()
