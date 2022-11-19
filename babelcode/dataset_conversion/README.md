# Dataset Conversion

The `dataset_conversion` module contains all of the logic needed to parse out
the test cases, schema, and other information from a Python dataset.

## [Assertion Parsing](assertion_parsing.py)

This module handles the parsing of assertions from testing code. It extracts the
literal inputs, outputs, and schema values.

### LiteralParser

The `LiteralParser` AST visitor is used to visit and parse schema types from a
literal (i.e. `"{1:2,3:4}"`). In the case of primitives, it simply determines
the type and sets the schema type. For data structures, e.g. `List`, it
recursively traverses the AST and determines the depth and what the full schema
type is.

#### Unsupported Literals

There are some python specific functionalities that are not supported, such as
lists of multiple types. In this case an error will be raised.

If there is a `dict` object whose keys are not a `int` nor `string`, an error
will be raised.

#### Type Reconciliation

In the case there are both `float` and `int` types, the `int` values will be
cast to `float`. Additionally, if a `float` or `int` is long enough, the schema
type will be set to `double` and `long` respectively.

### AssertionToSchemaVisitor

The `AssertionToSchemaVisitor` visitor class will find all assertions in a given
code block, and parse the functions, inputs and outputs present.

It currently only supports a single, non-nested, calls in the left side of the
assertion:

*   `assert f(x) == 1` is valid.
*   `assert f(g(x)) == 1` is **not** valid.
*   `assert f(x) == y` is **not** valid.
*   `assert f(x) == g(x)` is **not** valid.
*   `assert f.g(x) == 1` is **not** valid.

## [Question Parsing](question_parsing.py)

The question parsing module uses the testing code, solution, and entry function
name to convert a question to the proper BabelCode format. This works in the
following steps:

1.  Try to find the function with the `entry_fn_name` in the solution code. If
    it is not found an error is raised.
2.  Parse the function signature to extract the argument name and order. If type
    annotations are present, parse them to the
    [BabelCode DSL](/babelcode/schema_parsing/README.md).

    a. Additionally, if annotations are found, a flag is saved that will
    indicate during prompt generation to force type annotations in languages
    where it is optional.

    b. Currently, functions with default arguments are **not** supported.

3.  Parse the schema types, inputs and outputs from the assertions present in
    the testing code.

4.  Validate that the parsed schema types are valid and that they align with the
    found literal values.

    a. For a parsed schema type to be considered not valid in this case, it must
    fulfil one of the following:

The schema types for an argument not consistent across all tests found. An
example of this:

```py
# This is invalid because the maximum depth of the first example is 2, while the second has a max depth of 3.
assert f([[],[1]]) == 1 # list<list<integer>>
assert f([[[1]],[[1]]]) == 1 # list<list<list<integer>>>
```

If the schema types across multiple tests indicate that data structures are used
for a given argument, it would be considered invalid if they cannot be
consolidated. Example: 

```py
# This one IS valid because the first has an null data structure, while the second has the full values.

assert f([]) == 1 # list<null> 
assert f([[1]]) == 1 # list<list<integer>>
schema_type = 'list<list<integer>> ```
```

5.  Return the properly formatted test cases and schema for the question.
