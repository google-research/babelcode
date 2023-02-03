# BabelCode

![overview](/img/overview_fig.png)

A framework for execution-based evaluation of any dataset in any language from the paper [Measuring The Impact Of Programming Language Distribution]().

## How To Evaluate A Dataset

1.  Install the requirements with `pip install -r requirements.txt`
2.  Choose a dataset from [the supported raw datasets.](/data/raw_datasets/). For this example we will use [HumanEval](/data/raw_datasets/human_eval_questions.jsonl).
3.  You must first convert the dataset to the BabelCode format. To create BC-HumanEval, run
```bash
python convert_dataset.py --dataset_name="human_eval" --input_path="data/raw_datasets/human_eval_questions.jsonl"
```
This will create the parsed dataset located in `data/parsed_datasets/human_eval.jsonl`. It will additionally create the files `data/golden_predictions/human_eval.jsonl` and `data/convert_failures/human_eval.txt`. The former is the gold solutions from the dataset that allows validation of BabelCode. The convert failures is the description of all failures that occured when trying to convert the dataset.

4.  To generate the testing code and prompt data for the dataset run 

```bash
python generate_test_code.py --gin_file="configs/generate_code.gin" \
    --input="data/parsed_datasets/human_eval.jsonl" \
    --output="data/problem_code/human_eval"
```

This will create the `data/problem_code/human_eval` directory. In it will be the following files:

* `testing_code.jsonl`: The jinja testing scripts and problem information for each problem in the dataset and each language supported by BabelCode.
* `prompt_info.jsonl`: The translated signatures, both with and without docstrings, for each problem in the dataset and each language supported by BabelCode.  
* `failures`: A directory of JSONL files where each file contains the failures for each langauge.

4. Next build the docker image with

```sh
docker build -t babelcode:latest .
```

**Note:** A prebuilt docker image will be released soon.

5.  To then evaluate a set of predictions on

```bash
docker run -v "$(pwd)/eval_outputs":"$(pwd)/eval_outputs":z -e ALLOW_EXECUTION=true babelcode:latest \
    python evaluate_predictions.py --gin_file="configs/validate.gin" \
    --experiment_name="tutorial" \
    --predictions="data/golden_predictions/human_eval.jsonl" \
    --test_code="data/problem_code/human_eval" \
    --output_path="$(pwd)/eval_outputs"
```

The outputs will be written to `eval_outputs/tutorial`.


## Formatting Predictions

To make your predictions work with this framework, they must be in a jsonlines
file where each line is its own prediction. Each prediction must have the
follwing keys:

1.  `qid`: A question ID the prediction is for.
2.  `language`: The language the prediction is in.
3.  `code`: The code prediction to run.
4.  `id`: The id of the prediction. For each question, no two predictions may
    have the same id.

Optional Keys are:

1.  `entry_fn_name`: The name of the function to call when evaluating.
2.  `entry_cls_name`: If the language requires classes, this is the name of the
    prediction class to call when evaluating.

# Overview of How the Framework Works
![sample](/img/sample_program.png)

1.  For each language, generate a json lines file from question specifications
    where each line contains both the question information and the raw code
    needed to check the correctness of a solution

    1.  The code generated works by passing the test cases as arguments
    2.  The actual execution is wrapped by `try-except` blocks so that we can
        return the exception name.
    3.  Then the resulting outcome string is printed in the format
        `TEST-{TEST_ID}...{RESULT_STR}`

2.  Using a provided directory where each file in it is a set of json lines
    predictions for a given language, create the code files in a temporary
    directory

3.  Execute the predictions by simulating the shell and passing in language
    specific commands to compile and run a given file of code.

4.  Parse out the `TEST-{TEST_ID}...{RESULT_STR}` lines from the stdout captured
    and compare this with the expected test ids in the question data. If the
    `RESULT_STR` for each is not `PASSED`, then the prediction is considered
    failing.

5.  Report the aggregated statistics from all the questions and save both the
    raw results (result for each test case, the stdout/stderr, commands used,
    etc.) and the metrics to a specified output directory.

Additional documentation can be found in [the `docs` directory.](/docs/)

_This is not an officially supported Google product._
