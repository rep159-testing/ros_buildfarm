# Copyright 2026 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from ros_buildfarm.common import get_os_package_name
import rosdistro


def test_get_os_package_name_derived_binary():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(test_dir)))
    index_path = os.path.join(workspace_root, 'tests', 'workflow_4', 'index.yaml')
    index_url = f"file://{index_path}"

    index = rosdistro.get_index(index_url)
    dist_file = rosdistro.get_distribution_file(index, 'derived_binary')

    # turtlesim is from base via binary_import -> should resolve to ros-base-turtlesim
    assert get_os_package_name('derived_binary', 'turtlesim', dist_file) == 'ros-base-turtlesim'

    # new_package is defined in derived_binary -> should resolve to ros-derived_binary-new-package
    assert get_os_package_name('derived_binary', 'new_package', dist_file) == 'ros-derived_binary-new-package'


def test_get_os_package_name_derived_source():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(test_dir)))
    index_path = os.path.join(workspace_root, 'tests', 'workflow_4', 'index.yaml')
    index_url = f"file://{index_path}"

    index = rosdistro.get_index(index_url)
    dist_file = rosdistro.get_distribution_file(index, 'derived_source')

    # turtlesim is from base via source_rebuild -> should resolve to ros-derived_source-turtlesim
    assert get_os_package_name('derived_source', 'turtlesim', dist_file) == 'ros-derived_source-turtlesim'
