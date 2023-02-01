# Code Evaluation Framework

Code Evaluation across many languages.

## How To Evaluate a Set of Predictions

1.  Install the requirements with `pip install -r requirements.txt`
2.  Download the `questions.jsonl` file with all of the question data.
3.  Then, in a bash terminal, run the command

`python generate_test_code.py ${PATH TO YOUR questions.jsonl} ${WHERE YOU WANT
TO OUTPUT}`

1.  To then evaluate a set of predictions on

`python evaluate_predictions.py ${PATH TO THE PREDICTIONS FILE} ${PATH TO THE
OUTPUT OF STEP 3}`

NOTE: The predictions need to be a single jsonlines file where each entry must
have a `language` key.

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

_This is not an officially supported Google product._
