# How to add a language to BabelCode

This guide will document how to add a new Language to BabelCode. There are 4
main parts to this:

1.  Creating the testing data for automatic language testing.
2.  Adding in Language Schema Support.
3.  Adding in the translation support.
4.  Adding in the templates for evaluation.

We start first with the testing data as it should provide a nice overview to the
different core functionalities needed to support a given language. In this
guide, we will add in support for the language **Julia**.

It is **HIGHLY** recommended that you familiarize yourself with how BabelCode's
the schema parsing and translation work prior to trying to add in a new
language.

## Part 1: Setting Up The Testing Data

A critical benefit of BabelCode is that we have set up automatic testing for
each language that ensures it is implemented correctly. Thus, the first part of
adding a new language is creating the testing data to make this possible. The
testing data for each language is located in
[`/test_fixtures/language_data/{LANGUAGE NAME}`](/test_fixtures/language_data/).

For Julia, it is located in
[`/test_fixtures/language_data/Julia`](/test_fixtures/language_data/Julia). Each
language must have the following two files:

### [`spec.yaml`](/test_fixtures/language_data/Julia/spec.yaml)

The `spec.yaml` file is the mappings from testing inputs to their expected
values.

#### Primitive Translations

The first section is `primitives` which has one value for each of the supported
primitive schema types:

```
string, integer, boolean, float, double, float, character, long
```

For Julia, the specification for translating `string` and `integer` types would
look like:

```yaml
primitives:
  string:
    type_name: 'String'
    input: 'Test String'
    output: '"Test String"'
    null_output: '""'
  integer:
    type_name: 'Int64'
    input: 1
    output: '1'
```

Every type entry must have the keys: * `type_name`: The name of the type in the
language. In Julia, this is `String` and `Int64`. * `input`: Is the input value
to translate. * `output`: What the translated should be for the given language.

Further, as both `string` and `character` support null values across **all**
languages, we add in the `null_output` key with what an empty string or char
would be in the target language.

#### Data Structure Translation

Along with primitives, each language must support translating a select set of
data structures. They are `list`, `map`, and `set`. Our testing spec therefore
reflects that. The first section is `data_structures_schema` which holds the
expected **type** translations for each of the generic types:

```yaml
data_structures_schema:
  TYPE_NAME_1[]:
    expected: 'Vector{TYPE_NAME_1}'
    elements:
      - expected: 'TYPE_NAME_1'
  list<list<TYPE_NAME_1>>:
    expected: 'Vector{Vector{TYPE_NAME_1}}'
    elements:
      - expected: 'Vector{TYPE_NAME_1}'
        elements:
          - expected: 'TYPE_NAME_1'
  map<TYPE_NAME_1;TYPE_NAME_1>:
    expected: 'Dict{TYPE_NAME_1, TYPE_NAME_1}'
    elements:
      - expected: 'TYPE_NAME_1'
    key_type:
      expected: 'TYPE_NAME_1'
  set<TYPE_NAME_1>:
    expected: 'Set{TYPE_NAME_1}'
    elements:
      - expected: 'TYPE_NAME_1'
```

Each section has a tree that has an `expected` key and an array of `elements`
that are more nested sections. For map there is also a `key_type` dictionary
with a single `expetected` value in it. We further require that you include
`TYPE_NAME_1` in each of the expected translations so that each data structure
can be tested with each supported *primitive* type. Going over each translation:

*   `TYPE_NAME_1[]` is a flat list.
*   `list<list<TYPE_NAME_1>>` is a list of lists.
*   `map<TYPE_NAME_1;TYPE_NAME_1>` is a map.
*   `set<TYPE_NAME_1>` is a set.

The next section is `data_structures_literals` section which details the
expected literal code for the target language.

```yaml
data_structures_literals:
  nested_list: '[[TYPE_VAL_1, TYPE_VAL_1], [TYPE_VAL_1]]'
  nested_map: 'Dict(KEY_VAL_1 => [TYPE_VAL_1, TYPE_VAL_1])'
  set: 'Set([TYPE_VAL_1])'
```

*   `nested_list` is the translation of a list of lists.
*   `nested_map` is the translation of a map with primitive key and a value of a
    flat list.
*   `set` is the translation of a set of primitives.

For example, in Julia, we test that the translator translates `{"key":[1,1]}` to
`Dict("key" => [1, 1])`.

#### Prompt Translation

The next section is the prompt translation section, which details the expected
translated prompts for the target language.

```yaml
prompt_translation:
  # The name of the argument as if it was being passed. Important for languages
  # such as PHP where it would be $arg_name
  argument_name: 'arg_name'

  # The name and type annotation of an argument in a function signature.
  signature_argument: 'arg_name::TYPE_NAME'

  # The translated return type.
  return_type: "::TYPE_NAME"

  # The properly escaped and formatted docstring, for this you must properly
  # escape and format the string 'Test Docstring.\n/**///*/--"""'
  docstring: "\"\"\"\nTest Docstring.\n/**///*/--\\\"\\\"\\\"\n\"\"\""

  # How the signature with docstring should be formatted. The CAPS values are
  # replaced by the other values from this section.
  signature_with_docstring: "DOCSTRING\nfunction test(SIGNATURE)RETURNS"
```

#### Final Sections

The final two sections are `escaped_string` and `entry_point`. The
`escaped_string` has the input string and what it should be escaped too. Set
`entry_point` to `'test'`.

### [func_template.txt](/test_fixtures/language_data/Julia/func_template.txt)

This barebones text file contains the basic template to making a function in the
target language for execution.

For Julia the template is: `txt FN_SIGNATURE return RETURN_VALUE end`

*   `FN_SIGNATURE` is replaced with the function's signature.
*   `RETURN_VALUE` is replaced with a literal code translation.

### Testing the added language

To test your added language only, navigate to
[`tests/utils.py`](/tests/utils.py#27). The `LANGS_TO_TEST` variable sets the
list of languages to test. To test *only* one language, in this case Julia, set
`LANGS_TO_TEST = ['Julia']`.

Then to run **just** the language specific tests, run the command:

```sh
bash scripts/run_tests_in_docker.sh -f tests/languages
```

These test should all fail at the moment as we have yet to add in the language
support.

## Part 2: Adding in Language Schema Support

To add in support for schema parsing the generic DSL types to the language
specific types, navigate to
[`/babelcode/schema_parsing/language.py`](/babelcode/schema_parsing/languages.py).
This file stores all of the language specific specifications that are used to
translate the generic types to their language specific counterparts.

To add in a new language, add in a function called `make_{LANG_NAME}_spec()`
that returns a `LanguageSchemaSpec` object. For Julia this is:

```py
def make_julia_spec() -> LanguageSchemaSpec:
  """Makes Julia spec."""

  # Mapping of primitive types to Julia types.
  primitive_map = {
      'boolean': 'Bool',
      'integer': 'Int64',
      'character': 'Char',
      'float': 'Float64',
      'double': 'Float64',
      'long': 'Int64',
      'string': 'String',
  }
  return LanguageSchemaSpec(
      # Name of the language to register as.
      name='Julia',

      # The mapping defined prior
      primitive_lang_map=primitive_map,

      # The function to format the a list of type t to the Julia specific type.
      format_list_type=lambda t: 'Vector{' + t + '}',

      # The function to format a map with key type k and value type v to the
      # Julia specific type.
      format_map_type=lambda k, v: 'Dict{' + k + ', ' + v + '}',

      # The function to format the a set of type t to the Julia specific type.
      format_set_type=lambda t: 'Set{' + t + '}',
  )
```

To test that you have correctly implemented the language spec, run `sh bash
scripts/run_tests_in_docker.sh -f tests/languages/schema_test.py`

If the schema spec is implemented correctly, all tests should pass.

## Part 3: Adding in Translation Support

The next step to adding a language is adding the support to translate values to
valid code in the target language. To do this, first create a new python file
called `{LANGUAGE NAME}.py` to
[`babelcode/languages/lang_implementations`](/babelcode/languages/lang_implementations).
For Julia, this is
[`babelcode/languages/lang_implementations/julia.py`](/babelcode/languages/lang_implementations/julia.py).

There are 3 parts to adding in a language, they are:

*   `JuliaLiteralTranslator` => The class for translating objects to the literal
    code to initialize them in Julia
*   `JuliaPromptTranslator` => The class for handling the translation of the
    prompts to match Julia specific formatting.
*   Registering the language by creating a
    [`Language`](/babelcode/languages/language.py#41) object.

### The Language Literal Translator

The `JuliaLiteralTranslator` must inherit the base
[`LiteralTranslator`](/babelcode/translation/literal_translator.py) class. Then
override the specific functions to reflect the target language. For Julia, this
is:

```py
class JuliaLiteralTranslator(translation.LiteralTranslator):
  """The Julia generator."""

  def format_map(self, key_type: SchemaType, value_type: SchemaType,
                 entries: List[str]) -> str:
    """Formats a map for Julia."""

    # Maps can be empty, so we need specific if statement to handle them.
    if not entries:
      return 'Dict{' + key_type.lang_type + ',' + value_type.lang_type + '}()'

    # If it is not empty, then we format each of the entries in the map.
    return f'Dict({"," .join(entries)})'

  def format_map_entry(self, key: str, value: str) -> str:
    """Formats a single entry for a map."""

    # In Python, this is akin to each KEY: VALUE line in a dictionary
    # initialization.
    return f'{key} => {value}'

  def format_set(self, generic_type: SchemaType, set_values: List[str]):
    """Formats a set for Julia."""

    # Sets can be empty, so we need specific if statement to handle them.
    if not set_values:
      return generic_type.lang_type + '()'

    return f'Set([{", ".join(set_values)}])'

  def format_list(self, generic_type: SchemaType,
                  list_values: List[str]) -> str:
    """Formats a list for Julia."""
    if not list_values:
      return f'{generic_type.lang_type}(undef,0)'
    return f'[{", ".join(list_values)}]'
```

To illustrate the translations, here are some Python to Julia examples:

*   `{"Key": 1}` => `'Dict("Key" => 1)'
*   `[1]` => `'[1]'`
*   `{"A","B"}` => `'Set(["A", "B"])'`

### The Prompt Translator

Next, we have the `JuliaPromptTranslator` which must inherit from
[`PromptTranslator`](/babelcode/translation/prompt_translator.py).

```py
class JuliaPromptTranslator(translation.PromptTranslator):
  """The Julia prompt translator."""

  @property
  def word_replacement_map(self) -> Dict[str, str]:
    """The Julia words to replace."""

    # For each key, we go through its corresponding list and replace all
    # occurences of each word with the key. Matching existing casing.
    return {
        'vector': ['array', 'list'],
        'dictionary': ['map'],
    }

  @property
  def signature_template(self) -> str:
    """The Julia signature template."""

    # The Jinja template to format the docstring and signature.
    return '\n'.join([
        '{%- if docstring is not none -%}{{docstring~"\n"}}{%- endif -%}',
        'function {{entry_fn_name}}({{signature}}){{return_type}}',
    ])

  def clean_docstring_for_lang(self, docstring: str) -> str:
    """Cleans and translates a docstring for Julia."""

    # Escapping the docstring for the language.
    return translation.escape_triple_quotes(docstring)

  def format_docstring_for_lang(self, docstring: str) -> str:
    """Formats a docstring for Julia."""
    return f'"""\n{docstring}\n"""'

  def translate_signature_argument_to_lang(self, arg_name: str,
                                           arg_type: SchemaType,
                                           use_type_annotation: bool) -> str:
    """Translates the signature argument to Julia."""

    # Julia does not require annotations, but to keep datasets consistent to
    # their source, we add in the flag to use type annotations.
    if use_type_annotation:
      return f'{arg_name}::{arg_type.lang_type}'

    return arg_name

  def translate_signature_returns_to_lang(self, return_type: SchemaType,
                                          use_type_annotation: bool) -> str:
    """Translates the signature return to Julia."""

    # Julia does not require annotations, but to keep datasets consistent to
    # their source, we add in the flag to use type annotations.
    if use_type_annotation:
      return f'::{return_type.lang_type}'
    return ''
```

### Registering the Language

To register the language, we first must create the language object. For Julia,
this is: ```py language.LanguageRegistry.register_language( language.Language(
name='Julia', file_ext='jl', # The function to take in a file, and create the
commands to execute it # through the command line. command_fn=lambda fp:
[Command(['julia', fp.name], timeout=10)],

```
    # A mapping of primitive type names, to a function that takes in a
    # value, and returns the converted value string.
    primitive_conversion_mapping={},

    # The prompt and literal translator classes.
    literal_translator_cls=JuliaLiteralTranslator,
    prompt_translator_cls=JuliaPromptTranslator,

    # The naming convention the language uses.
    naming_convention=utils.NamingConvention.SNAKE_CASE,

    # The function to properly escape strings.
    escape_fn=lambda s: s.replace('$', '\\$')))
```

~~~

For an example of the `primitive_conversion_mapping`, look at the implementations of either [Java](/babelcode/languages/lang_implementations/java.py) or [Rust](/babelcode/languages/lang_implementations/java.py).

Then, in [`babelcode/languages/lang_implementations/__init__.py`](babelcode/languages/lang_implementations/__init__.py), import the module.

### Testing generation

To test that the translations have been implemented properly, run

```sh
bash scripts/run_tests_in_docker.sh -f tests/languages/generation_test.py
~~~

To test the generation and then run `sh bash scripts/run_tests_in_docker.sh -f
tests/languages/prompt_test.py` to test the prompt translation.

## Part 4: Adding in execution support

Finally, to enable execution, we must first add templates to generate the
testing code and then add the commands to install the language to the docker
image.

### Templates

There are 3 required Jinja templates that each language must have. These go in
[`/templates/{LANGUAGE NAME}`](/templates).

#### Evaluation Template

The evaluation template [`evaluation.txt`](/templates/Julia/evaluation.txt)
generates the code used to determine if the result from a prediction matches the
expected outputs. For Julia, this looks like:

```
{%- if evaluation_method == 'float' -%}
    return abs(actual - expected) < {{precision}}
{%- else -%}
    return actual == expected
{%- endif -%}
```

It must support proper float equivalence, and have a defaul setting.

#### Header Template

The header template stores all file headers or imports to use.

#### Main Template

The Main template [`main.txt`](/templates/Julia/main.txt) generates the overall
testing script for evaluating predictions. For Julia this looks like:

```
{{ header }}
{% if text is not none -%}
# Question Prompt (NOT what is passed to the model)
{% for line in text.split('\n') -%}
{{ "# " ~ line ~ "\n"}}
{%- endfor -%}
#
{%- endif %}
# SOLUTION CODE
# ============================================
PLACEHOLDER_CODE_BODY

# TESTING CODE
# ============================================
function validate_solution(actual, expected)
    {% filter indent(width=4) -%}
    {{ evaluation_function }}
    {%- endfilter %}
end

function driver({{signature}}, expected)
    try

        {% if debug -%}
        @printf("\n==================\nDEBUGGING PRINTS:\n")
        @printf("RESULT=%s\n",PLACEHOLDER_FN_NAME({{ params|join(', ')}}))
        @printf("EXPECTED=%s\n",expected)
        @printf("==================\n")
        {%- endif -%}
        if validate_solution(PLACEHOLDER_FN_NAME({{ params|join(', ')}}), expected)
            return "PASSED";
        end
        return "FAILED";
    catch exception_obj
        return string(Base.typename(typeof(exception_obj)).wrapper);
    end
end

function main()
    {% for test_case in test_cases  %}
    result = driver({{test_case.inputs|join(", ")}}, {{test_case.outputs}});
    @printf("TEST-{{test_case.idx}}...%s\n",result);
    {% endfor %}
end

main()
```

First, their is `{{header}}` which is used to add any imports from the header
template.

The next block: `PLACEHOLDER_CODE_BODY` Is a placeholder for the prediction body
and, additionally, debug text.

```
function validate_solution(actual, expected)
    {% filter indent(width=4) -%}
    {{ evaluation_function }}
    {%- endfilter %}
end
```

Will load the evaluation code.

```
function driver({{signature}}, expected)
    try
        if validate_solution(PLACEHOLDER_FN_NAME({{ params|join(', ')}}), expected)
            return "PASSED";
        end
        return "FAILED";
    catch exception_obj
        return string(Base.typename(typeof(exception_obj)).wrapper);
    end
end

function main()
    {% for test_case in test_cases  %}
    result = driver({{test_case.inputs|join(", ")}}, {{test_case.outputs}});
    @printf("TEST-{{test_case.idx}}...%s\n",result);
    {% endfor %}
end

main()
```

Babelcode checks if a prediction passes the test cases by parsing the standard
output. We therefore require that every language prints out the results in the
format `TEST-{IDX}...{RESULT}` where `IDX` is the index of the test case and
`{RESULT}` is either `PASSED`, `FAILED`, or the name of a runtime error.

### Adding language installation

Finally, add in the installation commands to [Dockerfile](/Dockerfile) to allow
the language to run.

## Part 5: Testing Your Language

Finally, run the commands: `sh bash scripts/run_tests_in_docker.sh -f
tests/languages/` To test your specific language, and then comment out the line
added in [`tests/utils.py`](/tests/utils.py#27) to enable all languages to be
tested. Then test all of BabelCode by running `sh bash
scripts/run_tests_in_docker.sh`
