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

"""Utilities for metrics."""
import tensorflow as tf


def write_to_tb_writer(metrics, writer, step, prefix="eval"):
  """Writes metrics to a tensorboard writer."""
  if writer is None:
    return
  with writer.as_default():
    for met, value in metrics.items():
      name = f"{prefix}/{met}"
      if isinstance(value, (float, int)):
        tf.summary.scalar(name, value, step=step)
      elif isinstance(value, dict):
        write_to_tb_writer(value, writer, step=step, prefix=name)
      elif isinstance(value, str):
        tf.summary.text(name, value, step=step)
      else:
        continue
