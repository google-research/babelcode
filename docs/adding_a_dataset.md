# Adding A Dataset To BabelCode

This guide will cover how to make a dataset compatible with BabelCode. This guide is split into two main parts:



1. Creating a generic dataset with only BabelCode’s DSL.
2. Converting an existing Python Dataset to BabelCode format.
3. How to use it with BabelCode

We use the term **generic** to describe a dataset that is language agnostic.


## Creating a Generic Dataset

BabelCode only requires that every question in a dataset has:



*   A unique ID string
*   A Title string
*   A Schema that specifies the input and output types for the question
*   A list of test cases that has the pairs of inputs and their expected outputs
*   An entry name for the function

The raw dataset file must be a list of JSON objects where each of the above attributes is a key. For other keys that can be used, refer to the <code>[Question data type](/babelcode/data_types/question.py)</code>. 


### The Question Schema

The `Question.schema` holds all of the necessary type information needed to enable BabelCode to translate it to any language. For each question, the value for the `schema` key must be a dictionary. Example of a question’s schema with whitespace for clarity:


```
{
  "params": [{"name":"arg", "type": "integer"}],
  "return": {"type": "string"},
}
```




*   The `params` key holds the list of dictionaries that represent the input arguments and their order. Each dictionary must have a `name` for the name of the argument and a `type` in BabelCode’s DSL.
*   The `return` key maps to a dictionary that must have a `type` key whose value is the BabelCode DSL that represents the output type for the question.


### The Test List

The `Question.test_list` contains the inputs and outputs needed to evaluate if a program solves a given question. It must be a list of dictionaries. For the above example schema, an example test list would be:


```
[
  {"idx": 0, "inputs": {"arg": 1}, "outputs":"Test String 1"},
  {"idx": 1, "inputs": {"arg": 2}, "outputs":"Test String 2"}
]
```




*   The `"idx"` key represents the index to use for the test case. This **must** be an integer and no test cases for a given problem can have the same idx.
*   The `"inputs"` key holds a dict mapping an input value to an argument name.
*   The `"outputs"` key holds the value that the program must return given the inputs.


### The Entry Points

Each question dictionary must also specify an `entry_fn_name`, this is the name of the function that the question expects. Further, an optional `entry_cls_name` can be specified for languages that require a class name (i.e. Java, C#)

**Note: **these are mainly used for creating signatures for prompting and for creating the predictions that a dataset does not have any errors. Predictions can override these by providing both either an `entry_fn_name` or an `entry_cls_name`


### Other Keys



*   `use_type_annotation`: Force the use of type annotations in the prompts for languages that support no type annotations (i.e. Python)
*   `metadata`: any additional metadata you want to pass to the question.
*   `solutions`: A dictionary whose keys are language names and whose value are solutions in that language. Useful for validating that your dataset is properly implemented.


## Creating a Python Dataset

To aid in creating a Python dataset for BabelCode, we have a `convert_dataset.py` script that will take in a jsonlines file and convert it to the BabelCode format. Each line in the JSON lines file must have the following keys:



*   `id`: The unique id of the question
*   `title`: the title of the question.
*   `testing_code`: A string containing assert statements that will be parsed into the test cases.
*   `solution`: The **Python** solution that will be used to get the signature and arguments.

There are also the following optional keys:



*   `text`: the Natural Language text description of the problem. Used for creating prompts.
*   `other_lang_solutions`: A dictionary whose keys are the names of languages and values are solutions in other languages. 

Additionally, you can provide fixes for individual problems as a JSON lines file in `data/dataset_fixes`. The file name must be the name of the dataset you provide to the command. Each line in this file must have an `id` that matches an ID in the original dataset file. Any other keys provided by this dictionary will override the original values from entry in the raw dataset file with the same `id`.

To parse your Python dataset, run the following command:


```
python convert_dataset.py \
    --dataset_name="{DATASET_NAME}" 
    --input_path="{DATASET_LOCATION}"
```




*   `dataset_name` is the name to save the dataset as.
*   The script will save the parsed dataset to `data/parsed_datasets/{DATASET_NAME}.jsonl` and will create a “golden” predictions file from each question’s solutions. These predictions are useful for testing that your dataset is parsed correctly


### Using your dataset with BabelCode

After either creating a generic dataset or using the conversion script, you can now use the dataset with `generate\_test\_code.py` like any other dataset!
