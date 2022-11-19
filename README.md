# Code Evaluation Framework

Code Evaluation across many languages.

# How To Evaluate a Set of Predictions

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
file where each line is its own prediction. Each prediction must have an `'id'`
field that represents its id that is unique on a question level (i.e. two
predictions can have the same id, if and only if they are for different
questions). The corresponding question id `'qid'`. The actual prediction code in
the `'code'` field. An `'entry_point'` field with the code to invoke your
solution.

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
