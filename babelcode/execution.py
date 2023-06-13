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
"""Functions for executing a set of commands to evaluate a code prediction."""
import collections
import contextlib
import copy
import datetime
import gc
import json
import multiprocessing as mp
import os
import pathlib
import signal
import subprocess
from typing import List

from absl import logging
from babelcode.data_types.command import Command
from babelcode.data_types.prediction import Prediction
from babelcode.data_types.result_types import ExecutionResult
from babelcode.languages import Language
from babelcode.utils import convert_timedelta_to_milliseconds
from babelcode.utils import format_timedelta_str
import gin
import psutil


class UnknownLangError(Exception):
  """Exception for when an unknown language is found."""


class PredTimeoutError(Exception):
  """Timeout error for running commands."""


@contextlib.contextmanager
def time_limit(seconds: float):
  """Sets a time limit."""

  def signal_handler(signum, frame):
    raise PredTimeoutError('Timed out!')

  signal.setitimer(signal.ITIMER_REAL, seconds)
  signal.signal(signal.SIGALRM, signal_handler)
  try:
    yield
  finally:
    signal.setitimer(signal.ITIMER_REAL, 0)


CommandResult = collections.namedtuple(
    'CommandResult',
    ['return_code', 'runtime', 'max_memory_used', 'outputs', 'timed_out'],
)


def set_limits():
  """Sets limits and other info before execution."""
  p = psutil.Process(os.getpid())
  p.nice(19)


def safe_execute(command: List[Command],
                 cwd: pathlib.Path,
                 timeout_buffer: float = 0.005) -> CommandResult:
  """Executes a list of commands safely.

  Args:
    command: The list of commands to run.
    cwd: The working directory to run them in.
    timeout_buffer: A buffer to use for timeout.

  Returns:
    The result of executing the command.
  """
  timed_out = False
  return_code = -1
  runtime = command.timeout
  outputs = (None, None)
  start_time = datetime.datetime.now()
  execution_process = subprocess.Popen(  # pylint: disable=subprocess-popen-preexec-fn
      command.command,
      cwd=cwd,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      # preexec_fn=set_limits,
  )
  pid = execution_process.pid
  process = psutil.Process(pid)
  memory_used = process.memory_info().rss
  try:
    with time_limit(command.timeout + timeout_buffer):
      while execution_process.poll() is None:
        memory_used = max(memory_used, process.memory_info().rss)

    outputs = execution_process.communicate()
    runtime = datetime.datetime.now() - start_time
    return_code = execution_process.returncode
  except PredTimeoutError:
    timed_out = True
    runtime = datetime.timedelta(seconds=command.timeout)
  finally:
    execution_process.kill()
  return CommandResult(
      return_code=return_code,
      runtime=runtime,
      max_memory_used=memory_used,
      outputs=outputs,
      timed_out=timed_out,
  )


def execute_code(prediction: Prediction,
                 commands: List[Command]) -> ExecutionResult:
  """Execute a file of code.

  Args:
      prediction: The Prediction to execute.
      commands: The commands to run.

  Returns:
      The execution result.
  """
  if os.getenv('ALLOW_EXECUTION', 'false') != 'true':
    raise ValueError('EXECUTION IS NOT ALLOWED IN THIS ENVIRONMENT')
  failed = False
  file_path = prediction.file_path
  cwd = file_path.parent if file_path.is_file() else file_path
  cwd = str(cwd.resolve().absolute())

  last_ran_command = -1
  start_time = datetime.datetime.utcnow()
  finished_time = None

  command_runtimes = [None] * len(commands)
  command_memory_used = [None] * len(commands)
  for i, command in enumerate(commands):
    last_ran_command = i

    command_result = safe_execute(command, cwd)
    command_memory_used[i] = command_result.max_memory_used
    command_runtimes[i] = convert_timedelta_to_milliseconds(
        command_result.runtime)
    if command_result.timed_out:
      net_runtime = sum(filter(lambda t: t, command_runtimes))
      return ExecutionResult(
          prediction=prediction,
          commands=commands,
          stdout='',
          stderr='',
          return_code=0,
          net_runtime=net_runtime,
          last_ran_command_idx=i,
          timed_out=True,
          command_runtimes=command_runtimes,
          command_memory=command_memory_used,
      )

    finished_time = datetime.datetime.utcnow()
    stdout, stderr = command_result.outputs
    # If there was an error running the commands, stop the iteration.
    if command_result.return_code != 0:
      failed = True
      break

  # Elapsed time
  if finished_time is None:
    elapsed_time = None
  else:
    # Convert the timedelta to milliseconds for ease of use.
    total_time = finished_time - start_time
    elapsed_time = convert_timedelta_to_milliseconds(total_time)

  # We assume that the last process result is the one we care about. So only
  # take the stdout and stderr from those.
  return ExecutionResult(
      prediction=prediction,
      commands=commands,
      stdout=stdout.decode('utf-8', errors='ignore'),
      stderr=stderr.decode('utf-8', errors='ignore'),
      return_code=command_result.return_code,
      net_runtime=elapsed_time,
      last_ran_command_idx=last_ran_command,
      had_error=failed,
      command_runtimes=command_runtimes,
      timed_out=False,
      command_memory=command_memory_used,
  )


# Wrapper to allow serialized multiprocessing with mp.pool.
def exec_wrapper(arg_list):
  """Execution wrapper to make execution work with multiprocessing.

  Args:
    arg_list: The list of args.

  Returns:
    The execution result.
  """
  prediction, commands = arg_list
  return execute_code(prediction=prediction, commands=commands)


def execution_results_writer(
    result_queue: mp.JoinableQueue,
    execution_results_file: pathlib.Path,
    runtime_results_file: pathlib.Path,
):
  """Listens to a result queue and writes the runtimes and results to disk."""

  execution_fd = execution_results_file.open('a')
  runtime_fd = runtime_results_file.open('a')
  written_records = 0
  while True:
    if result_queue.empty():
      continue
    execution_results = result_queue.get()
    if execution_results is None:
      logging.debug('Execution Saver Got Poison Pill, exiting...')
      runtime_fd.close()
      execution_fd.close()
      result_queue.task_done()
      return
    is_execution_result, result = execution_results
    if is_execution_result:
      result: ExecutionResult
      execution_fd.write(json.dumps(result.to_dict()) + '\n')
    else:
      runtime_fd.write(json.dumps(result) + '\n')
    result_queue.task_done()
    written_records += 1
    if written_records % 1000 == 0:
      logging.info('Wrote %d records', written_records)


@gin.configurable('execution', denylist=['predictions', 'lang', 'output_dir'])
def execute_predictions(
    predictions: List[Prediction],
    lang: Language,
    output_dir: pathlib.Path,
    num_workers: int = 1,
    update_freq: int = 250,
    max_task_per_child: int = 1,
    garbage_collection_freq: int = 500,
):
  """Execute a list of predictions in a specific language.

  Args:
      predictions: List of predictions.
      lang: The language the code is written in.
      output_dir: The output directory.
      num_workers: The number of workers to use.
      update_freq: Frequency of updates.
      max_task_per_child: The maximum tasks ran per child before it is killed.
      garbage_collection_freq: How often to run garbage collection.

  Returns:
      The the array of raw execution results and the total runtime.
  """
  if os.getenv('ALLOW_EXECUTION', 'false') != 'true':
    raise ValueError('EXECUTION IS NOT ALLOWED IN THIS ENVIRONMENT')

  logging.info('Evaluating %d predictions in %s', len(predictions), lang.name)

  # Make the arguments to submit to the ThreadPoolExecutor. Do it here so we
  # can have a progress bar as well.
  executor_args = []
  logging.debug('Creating args for executor with %d predictions',
                len(predictions))
  failed = 0
  for prediction in predictions:
    if not prediction.file_path.exists():
      logging.error('Got prediction %s that does not exist', prediction)
      failed += 1
      continue
    executor_args.append((prediction, lang.command_fn(prediction.file_path)))

  logging.info('%d/%d are not be able to be executed', failed, len(predictions))

  # # Create a temporary directory in the project.
  # temp_dir = TEMP_EXECUTION_PATH.joinpath(output_dir.stem)
  # temp_dir.mkdir(parents=True, exist_ok=True)

  execution_results_file = output_dir.joinpath(
      f'{lang.name}_execution_results.jsonl')
  runtime_results_file = output_dir.joinpath(
      f'{lang.name}_runtime_tracking.jsonl')

  execution_results_fd = execution_results_file.open('a')
  runtime_results_fd = runtime_results_file.open('a')

  logging.info('Starting %d workers...', num_workers)
  num_to_complete = len(executor_args)
  num_completed = 0

  start_time = batch_time = datetime.datetime.utcnow()
  results = []

  time_writing = 0
  batch_writing = 0
  last_written_idx = 0

  summary_result_tracking = collections.Counter()
  batch_cpu_used = []
  batch_mem_used = []
  with mp.Pool(num_workers, maxtasksperchild=max_task_per_child) as pool:
    for result in pool.imap_unordered(exec_wrapper, executor_args):
      num_completed += 1

      # Simple tracking of metrics for as it progress
      had_error = result.had_error or result.return_code != 0
      summary_result_tracking['Had Error'] += had_error
      summary_result_tracking['Timed Out'] += result.timed_out
      summary_result_tracking['Executed'] += not (result.timed_out or had_error)
      results.append(result)
      batch_cpu_used.append(psutil.cpu_percent())
      batch_mem_used.append(psutil.virtual_memory().percent)

      # Update stats
      if num_completed % update_freq == 0:
        # Calculate The Overall rate
        pct_done = num_completed / num_to_complete * 100
        current_time = datetime.datetime.utcnow()
        elapsed = current_time - start_time
        if elapsed.total_seconds() == 0:
          rate = num_completed
        else:
          rate = num_completed / elapsed.total_seconds()

        # Calculate The Batch rate
        batch_elapsed = current_time - batch_time
        if batch_elapsed.total_seconds() == 0:
          batch_rate = update_freq
        else:
          batch_rate = update_freq / batch_elapsed.total_seconds()

        rate_msg = (f'{num_completed:,} ({pct_done:0.2f}%) done in'
                    f' {format_timedelta_str(elapsed)}')
        logging.info(rate_msg)
        cpu_usage = max(batch_cpu_used)
        memory_usage = max(batch_mem_used)
        summary_str = [
            'CPU Used = %-6s' % f'{cpu_usage:0.2f}',
            'RAM Used = %-6s' % f'{memory_usage:0.2f}',
        ]

        batch_cpu_used = []
        batch_mem_used = []
        for k, v in summary_result_tracking.items():
          value_str = f'{v:,}'
          summary_str.append(f'{k:>10}={value_str:<8}')

        logging.info(' | '.join(summary_str))
        logging.info(
            'Programs/Second: Batch %-7s | Overall %-7s',
            f'{batch_rate:.2f}',
            f'{rate:.2f}',
        )

        # Write the results to the results file.
        start_write = datetime.datetime.utcnow()
        for i in range(last_written_idx, len(results)):
          execution_results_fd.write(json.dumps(results[i].to_dict()) + '\n')
        batch_writing = (datetime.datetime.utcnow() -
                         start_write).total_seconds()
        last_written_idx = len(results)

        # Log the time spent writing.
        time_writing += batch_writing
        logging.info(
            '%s time spent writing.',
            f'{time_writing / elapsed.total_seconds():.2%}',
        )
        logging.debug(
            'Size of Execution Results: %s KB',
            f'{round(execution_results_file.stat().st_size/1024,2):.2f}',
        )

        batch_metrics = {
            'now': datetime.datetime.utcnow().isoformat(),
            'completed': num_completed,
            'pct_done': pct_done,
            'net_elapsed': elapsed.total_seconds(),
            'net_rate': rate,
            'batch_elapsed': batch_elapsed.total_seconds(),
            'batch_rate': batch_rate,
            'cpu_used': cpu_usage,
            'memory_used': memory_usage,
            'time_writing': time_writing,
            'batch_writing': batch_writing,
        }

        # Save the batch runtime metrics
        write_runtime = datetime.datetime.utcnow()
        runtime_results_fd.write(json.dumps(batch_metrics) + '\n')
        elapsed_write_runtime = (datetime.datetime.utcnow() -
                                 write_runtime).total_seconds()
        logging.debug('Spent %-6f writing runtime batch', elapsed_write_runtime)

        batch_time = datetime.datetime.utcnow()
      if num_completed % garbage_collection_freq == 0:
        logging.debug('Running garbage collection as num_completed=%d',
                      num_completed)
        gc.collect()

    # Cleanup pool
    pool.close()
    pool.terminate()

  logging.debug('Saving Remaining')
  for i in range(last_written_idx, len(results)):
    execution_results_fd.write(json.dumps(results[i].to_dict()) + '\n')

  total_time = datetime.datetime.utcnow() - start_time
  logging.info('Finished executing %d in %s', num_to_complete, total_time)
  logging.debug('Got %d results back, expected %d', num_completed,
                len(executor_args))
  execution_results_fd.close()
  runtime_results_fd.close()

  return results, format_timedelta_str(total_time)
