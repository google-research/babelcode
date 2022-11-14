# Data Types Module

This module holds the main data types used throughout BabelCode. They are
defined here so that we can use them in the framework without circular imports.

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

