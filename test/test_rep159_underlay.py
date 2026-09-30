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

from ros_buildfarm.common import BINARY_IMPORT_DISTROS_ENV
from ros_buildfarm.common import get_binary_import_distros
from ros_buildfarm.common import get_default_parent_result_spaces


class _DistFile:

    def __init__(self, extends):  # noqa: D107
        self.extends = extends


def test_no_extends_attribute_means_no_parents():
    assert get_binary_import_distros(object()) == []


def test_empty_extends_means_no_parents():
    assert get_binary_import_distros(_DistFile([])) == []


def test_only_binary_import_parents_in_order():
    dist_file = _DistFile([
        {'distro_name': 'upstream', 'index_url': None,
         'extension_method': 'source_rebuild'},
        {'distro_name': 'lyrical', 'index_url': 'https://example.org/i.yaml',
         'extension_method': 'binary_import'},
        {'distro_name': 'jetty', 'index_url': None,
         'extension_method': 'binary_import'},
    ])
    assert get_binary_import_distros(dist_file) == ['lyrical', 'jetty']


def test_default_parent_spaces_without_the_variable():
    assert get_default_parent_result_spaces('binext', environ={}) == \
        ['/opt/ros/binext']


def test_binary_import_parents_come_first():
    environ = {BINARY_IMPORT_DISTROS_ENV: 'lyrical'}
    assert get_default_parent_result_spaces('binext', environ=environ) == \
        ['/opt/ros/lyrical', '/opt/ros/binext']


def test_empty_entries_are_ignored():
    environ = {BINARY_IMPORT_DISTROS_ENV: ':lyrical::jetty:'}
    assert get_default_parent_result_spaces('binext', environ=environ) == \
        ['/opt/ros/lyrical', '/opt/ros/jetty', '/opt/ros/binext']
