# Data Types Module

This module holds the main data types used throughout BabelCode. They are
defined here so that we can use them in the framework without circular imports.
The main purpose of having these data types is to improve readability and
maintainability.

## [Command](command.py)

The `Command` data type represents the CLI command to run when executing code
from a given language.

## [Prediction](prediction.py)

The `Prediction` data type holds the information needed to evaluate a given
prediction program.

## [Question](question.py)

The `Question` data types is used to represent a given question from a dataset.
This is then used to generate the testing code and align the predictions to the
proper testing scripts.

## [Result Types](result_types.py)

The result types module holds the data types used for processing the results of
execution.

### [PredictionOutcome](result_types.py#26)

The `PredictionOutcome` enum represents the outcome of evaluating a single
prediction.

### [ExecutionResult](result_types.py#40)

The `ExecutionResult` represents the *raw* result of running a test script in
the command line.

### [PredictionResult](result_types.py#85)

The `PredictionResult` parses an `ExecutionResult` into usable information.

### [QuestionResult](result_types.py#218)

The `QuestionResult` class aggregates `PredictionResult` objects for a given
question.
