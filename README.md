# BabelCode

![overview](/img/overview_fig.png)

A framework for execution-based evaluation of any dataset in any language from the paper [Measuring The Impact Of Programming Language Distribution](https://arxiv.org/abs/2302.01973).


## Usage

### Prerequisites

1. Docker (ideally installed in sudoless mode.)
2. Python 3.9+
3. Install the requirements with `pip install -r requirements.txt`

### How To Evaluate A Dataset


1.  Choose a dataset from [the supported raw datasets.](/data/raw_datasets/). For this example we will use [HumanEval](/data/raw_datasets/human_eval_questions.jsonl).
2.  You must first convert the dataset to the BabelCode format. To create BC-HumanEval, run
```bash
python convert_dataset.py --dataset_name="human_eval" --input_path="data/raw_datasets/human_eval_questions.jsonl"
```
This will create the parsed dataset located in `data/parsed_datasets/human_eval.jsonl`. It will additionally create the files `data/golden_predictions/human_eval.jsonl` and `data/convert_failures/human_eval.txt`. The former is the gold solutions from the dataset that allows validation of BabelCode. The convert failures is the description of all failures that occurred when trying to convert the dataset.

3.  To generate the testing code and prompt data for the dataset run 

```bash
python generate_test_code.py --gin_file="configs/generate_code.gin" \
    --input="data/parsed_datasets/human_eval.jsonl" \
    --output="data/problem_code/human_eval"
```

This will create the `data/problem_code/human_eval` directory. In it will be the following files:

* `testing_code.jsonl`: The jinja testing scripts and problem information for each problem in the dataset and each language supported by BabelCode.
* `prompt_info.jsonl`: The translated signatures, both with and without docstrings, for each problem in the dataset and each language supported by BabelCode.  
* `failures`: A directory of JSONL files where each file contains the failures for each language.

4. Finally run
```bash
bash scripts/docker_eval.sh configs/tutorial_eval.gin tutorial data/golden_predictions/human_eval.jsonl data/problem_code/human_eval
```

The outputs will be written to `eval_outputs/tutorial`. It contains:

* `metrics.json`: The overall results for each language
* `pred_results.jsonl`: the results for each prediction
* `{LANGUAGE}_execution_results.jsonl`: The raw execution result for each prediction in LANGUAGE


## Formatting Predictions

To make your predictions work with this framework, they must be in a jsonlines
file where each line is its own prediction. Each prediction must have the
follwing keys:

1.  `qid`: A question ID the prediction is for.
2.  `language`: The language the prediction is in.
3.  `code`: The code prediction to run.

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

## Citation
```
@article{orlanski2023measuring,
  title={Measuring The Impact Of Programming Language Distribution},
  author={Orlanski, Gabriel and Xiao, Kefan and Garcia, Xavier and Hui, Jeffrey and Howland, Joshua and Malmaud, Jonathan and Austin, Jacob and Singh, Rishah and Catasta, Michele},
  journal={arXiv preprint arXiv:2302.01973},
  year={2023}
}
```
If you use the supported datasets, you must also cite the original work the datasets were created from:

### HumanEval
```
@article{chen2021codex,
  title={Evaluating Large Language Models Trained on Code},
  author={Mark Chen and Jerry Tworek and Heewoo Jun and Qiming Yuan and Henrique Ponde de Oliveira Pinto and Jared Kaplan and Harri Edwards and Yuri Burda and Nicholas Joseph and Greg Brockman and Alex Ray and Raul Puri and Gretchen Krueger and Michael Petrov and Heidy Khlaaf and Girish Sastry and Pamela Mishkin and Brooke Chan and Scott Gray and Nick Ryder and Mikhail Pavlov and Alethea Power and Lukasz Kaiser and Mohammad Bavarian and Clemens Winter and Philippe Tillet and Felipe Petroski Such and Dave Cummings and Matthias Plappert and Fotios Chantzis and Elizabeth Barnes and Ariel Herbert-Voss and William Hebgen Guss and Alex Nichol and Alex Paino and Nikolas Tezak and Jie Tang and Igor Babuschkin and Suchir Balaji and Shantanu Jain and William Saunders and Christopher Hesse and Andrew N. Carr and Jan Leike and Josh Achiam and Vedant Misra and Evan Morikawa and Alec Radford and Matthew Knight and Miles Brundage and Mira Murati and Katie Mayer and Peter Welinder and Bob McGrew and Dario Amodei and Sam McCandlish and Ilya Sutskever and Wojciech Zaremba},
  year={2021},
  eprint={2107.03374},
  archivePrefix={arXiv},
  primaryClass={cs.LG}
}
```

### Mostly Basic Programming Problems (MBPP)
```
@article{Austin2021ProgramSW,
  title={Program Synthesis with Large Language Models},
  author={Jacob Austin and Augustus Odena and Maxwell Nye and Maarten Bosma and Henryk Michalewski and David Dohan and Ellen Jiang and Carrie J. Cai and Michael Terry and Quoc V. Le and Charles Sutton},
  journal={ArXiv},
  year={2021},
  volume={abs/2108.07732}
}
```

### Python Programming Puzzles (P3)
```
@inproceedings{
    schuster2021programming,
    title={Programming Puzzles},
    author={Tal Schuster and Ashwin Kalyan and Alex Polozov and Adam Tauman Kalai},
    booktitle={Thirty-fifth Conference on Neural Information Processing Systems Datasets and Benchmarks Track},
    year={2021},
    url={https://arxiv.org/abs/2106.05784}
}
```

### Transcoder
```
@article{roziere2020unsupervised,
  title={Unsupervised translation of programming languages},
  author={Roziere, Baptiste and Lachaux, Marie-Anne and Chanussot, Lowik and Lample, Guillaume},
  journal={Advances in Neural Information Processing Systems},
  volume={33},
  year={2020}
}
```

_This is not an officially supported Google product._
