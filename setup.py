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

from setuptools import find_packages
from setuptools import setup

VERSION = "1.0.0"
setup(
    name="babelcode",
    version=VERSION,
    description=
    "A framework for execution-based evaluation of any dataset in any language.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    project_urls={
        'Source': 'https://github.com/google-research/babelcode',
    },
    license='Apache License, Version 2.0',
    author='Google Inc.',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research"',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent', 'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering :: Artificial Intelligence'
    ],
    packages=find_packages(where='.', include=['babelcode*', 'tests*']),
    install_requires=[
        'jinja2>=3.1.2',
        'numpy>=1.23.1',
        'pandas>=1.4.3',
        'tqdm>=4.64.0',
        'psutil>=5.9.2',
        'absl-py>=1.2.0',
        'tensorflow>=2.10.0',
        'gin-config>=0.5.0',
    ],
)
