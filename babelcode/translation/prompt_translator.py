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
"""Base class for language specific prompt+signature translation."""
import re
from typing import Callable, Dict, List, Optional, Tuple

import jinja2

from babelcode import data_types
from babelcode import schema_parsing
from babelcode import utils

SchemaMapType = schema_parsing.SchemaMapType
SchemaType = schema_parsing.SchemaType
SchemaValueType = schema_parsing.SchemaValueType
Question = data_types.Question


class PromptTranslator:
  """Base prompt translator class for translating signatures and prompts.

  Attributes:
    lang_name: The name of the language.
    naming_convention: The naming convention to use.
    escape_fn: Callable that takes in a string and replaces language specific
      characters with "\\{CHARACTER}".
  """

  def __init__(self,
               lang_name: str,
               naming_convention: utils.NamingConvention,
               escape_fn: Optional[Callable[[str], str]] = None) -> None:
    """Initialize the PromptTranslator class."""
    self.naming_convention = naming_convention
    self.lang_name = lang_name
    self.escape_fn = escape_fn or (lambda s: s)

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The mapping of source language specific words to the target language.

    For example, the C++ translator would want to change the word 'list' to
    vector. Thus the word_replacement_map would be {'vector':'list'}.

    The values must be a list of words, with the key being the word to replace
    them with. Not Casing does not matter.

    Returns:
        Dict[str, str]: The mapping of words to replace in the prompt.
    """
    raise NotImplementedError

  @property
  def signature_template(self) -> str:
    """The jinja template to create a function signature.

    The template must have the following inputs:
      - `entry_fn_name`: The name of the function.
      - `signature`: The argument signature for the function.
      - `return_type`: The return type of the function.
      - `docstring`: The location of the docstring with respect to the function.
        This must also handle the case when docstring is None.

    The optional arguments are:
      - `entry_cls_name`: The name of the entry class.
      - `params`: The list of parameter names.

    Returns:
        The string jinja2 template for creating a signature.
    """
    raise NotImplementedError

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Cleans the docstring for a given language.

    By "cleaning", we mean removing/escaping characters that could cause errors.
    Args:
        docstring (str): The raw docstring.

    Returns:
        str: The cleaned docstring for the language.
    """
    raise NotImplementedError()

  def translate_entry_function_name(
      self,
      entry_fn_name: str,
  ) -> str:
    """Translates the function name to the proper convention.

    Args:
        entry_fn_name (str): The original function name.

    Returns:
        str: The function name with proper formatting.
    """
    return utils.format_str_with_convention(self.naming_convention,
                                            entry_fn_name)

  def translate_entry_cls_name(self, entry_cls_name: str) -> str:
    """Translates the name of the entry class for a language.

    Args:
        entry_cls_name (str): The name of the entry class.

    Returns:
        The translated entry name.
    """
    return entry_cls_name

  def format_docstring_for_lang(self, docstring: str) -> str:
    """Formats a docstring to a language's syntax.

    Args:
        docstring (str): The original docstring.

    Returns:
        The formatted docstring.
    """
    raise NotImplementedError()

  def format_signature(self, signature_args: List[str]) -> str:
    return ', '.join(signature_args)

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates a single argument name of a function signature to a language.

    Args:
        arg_name (str): The name of the argument.
        arg_type (SchemaType): Its generic type.
        use_type_annotation (bool): If the language does not require type
          annotations, this flag forces the use of them.

    Returns:
        The formatted argument for the signature.
    """
    raise NotImplementedError()

  def translate_argument_name_to_lang(self, arg_name: str) -> str:
    """Translates a single argument name to a language.

    This differs from the signature argument as this will be used for parameters
    or for languages like Haskell where the signature arguments and their types
    are not together.

    Args:
        arg_name (str): The name of the argument.

    Returns:
        The translated argument.
    """
    return arg_name

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the return type of a signature for a language.

    Args:
      return_type (SchemaType): The generic type the function returns.
      use_type_annotation (bool): If the language does not require type
        annotations, this flag forces the use of them.

    Returns:
        The translated return type.
    """
    raise NotImplementedError()

  def translate_prompt(self, source_language: str, prompt: str,
                       entry_fn_name: str) -> str:
    """Translates a prompt to a language.

    This function replaces words from the word replacement map and replaces any
    examples with the function name present to the proper casing for the
    language.

    For Example:
      If the language uses Pascal Casing, a prompt with "entry_fn(...)" present
      will become "EntryFn(...)".

    Args:
        source_language (str): The source language of the prompt. This is used
          for replacing specific language names (i.e. Python) with the name of
          the language this translator is for.
        prompt (str): The prompt to translate.
        entry_fn_name (str): The name of the entry function from the prompt.

    Returns:
        The translated prompt.
    """
    new_entry_name = self.translate_entry_function_name(entry_fn_name)
    prompt = prompt.replace(entry_fn_name, new_entry_name)

    formatting_functions = [str.title, str.lower, str.upper]
    # First replace all of the source language occurrences in the prompt
    for format_fn in formatting_functions:
      prompt = prompt.replace(format_fn(source_language),
                              format_fn(self.lang_name))

    # Then go through the list of words to replace and replace them.
    replace_regex = r'( ?(?:a|an)?(?:^| )(?:__WORDS__)s?)(?=[ ,.])'
    for format_fn in formatting_functions:
      for target, original in self.word_replacement_map.items():
        regex_words = '|'.join(map(format_fn, original))

        new_word = format_fn(target)
        needs_an = any(
            new_word.startswith(v) for v in ['a', 'e', 'i', 'o', 'u'])
        word_regex = replace_regex.replace('__WORDS__', regex_words)
        matches = set(re.findall(word_regex, prompt))
        for found in sorted(list(matches), key=len, reverse=True):
          replacement_word = new_word
          if found.startswith('a ') or found.startswith('an '):
            replacement_word = f'a{"n" if needs_an else ""} {new_word}'
          elif found.startswith(' '):
            replacement_word = f' {new_word}'
          if found.endswith('s') and not replacement_word.endswith('s'):
            replacement_word += 's'

          prompt = prompt.replace(found, replacement_word)

    return self.clean_docstring_for_lang(prompt)

  def translate_type_signature(
      self, schema: SchemaMapType, input_order: List[str],
      use_type_annotation: bool) -> Tuple[List[str], List[str], str]:
    """Translates the type signatures for a functions arguments and returns.

    Args:
        schema (SchemaMapType): The schema of the function.
        input_order (List[str]): The order of arguments.
        use_type_annotation (bool): Use type annotations for this function.

    Returns:
        The translated signature, argument names and return types.
    """
    signature = []
    arguments = []
    for arg_name in input_order:
      arguments.append(self.translate_argument_name_to_lang(arg_name))
      signature.append(
          self.translate_signature_argument_to_lang(arg_name, schema[arg_name],
                                                    use_type_annotation))

    return_type = self.translate_signature_returns_to_lang(
        schema[data_types.EXPECTED_KEY_NAME], use_type_annotation)
    return self.format_signature(signature), arguments, return_type

  def translate_signature(self,
                          entry_fn_name: str,
                          entry_cls_name: str,
                          schema: SchemaMapType,
                          input_order: List[str],
                          use_type_annotation: bool,
                          docstring: Optional[str] = None) -> str:
    """Translates an entire signature.

    Args:
        entry_fn_name (str): The name of the entry function.
        entry_cls_name (str): The name of the entry class.
        schema (SchemaMapType): The schema for the function.
        input_order (List[str]): The order of arguments.
        use_type_annotation (bool): Use type annotation for this function.
        docstring (Optional[str], optional): If passed, this will be used for a
          docstring. Defaults to None.

    Returns:
        The translated signature rendered from the template.
    """
    # First translate the entry function and class.
    entry_fn_name = self.translate_entry_function_name(entry_fn_name)
    entry_cls_name = self.translate_entry_cls_name(entry_cls_name)

    signature, arguments, return_type = self.translate_type_signature(
        schema, input_order, use_type_annotation)
    # Replace the docstring argument with an if statement to handle when there
    # is no docstring.
    template = jinja2.Template(self.signature_template,
                               undefined=jinja2.StrictUndefined)

    return template.render(entry_fn_name=entry_fn_name,
                           entry_cls_name=entry_cls_name,
                           signature=signature,
                           return_type=return_type,
                           params=arguments,
                           docstring=docstring)

  def translate_signature_with_docstring(self, source_language: str,
                                         docstring: str, entry_fn_name: str,
                                         entry_cls_name: str,
                                         schema: SchemaMapType,
                                         input_order: List[str],
                                         use_type_annotation: bool) -> str:
    """Translates the signature and prompt as a docstring.

    Args:
        source_language (str): The source language of the prompt.
        docstring (str): If passed, this will be used for a docstring. Defaults
          to None.
        entry_fn_name (str): The name of the entry function.
        entry_cls_name (str): The name of the entry class.
        schema (SchemaMapType): The schema for the function.
        input_order (List[str]): The order of arguments.
        use_type_annotation (bool): Use type annotation for this function.

    Returns:
        The translated signature with docstring.
    """
    docstring = self.translate_prompt(source_language=source_language,
                                      prompt=docstring,
                                      entry_fn_name=entry_fn_name)

    docstring = docstring.replace('\\', '\\\\')
    docstring = self.escape_fn(docstring)
    docstring = self.format_docstring_for_lang(docstring)

    return self.translate_signature(entry_fn_name=entry_fn_name,
                                    entry_cls_name=entry_cls_name,
                                    schema=schema,
                                    input_order=input_order,
                                    use_type_annotation=use_type_annotation,
                                    docstring=docstring)
