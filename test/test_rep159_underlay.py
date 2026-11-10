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
from ros_buildfarm.common import get_binary_import_underlays
from ros_buildfarm.common import get_default_parent_result_spaces
from ros_buildfarm.common import get_distribution_install_prefix
from ros_buildfarm.common import PARENT_RESULT_SPACES_ENV


class _DistFile:

    def __init__(self, name='test_distro', extends=None, install_rule=None):
        self.name = name
        self.extends = extends or []
        self.install_rule = install_rule

    def get_install_prefix(self, pkg_name=None):
        if not self.install_rule:
            return '/opt/ros/%s' % self.name
        if isinstance(self.install_rule, str):
            return self.install_rule.replace('{distro}', self.name)
        if isinstance(self.install_rule, dict):
            import re
            return re.sub(self.install_rule['search'], self.install_rule['replace'].replace('{distro}', self.name), pkg_name or '')
        return '/opt/ros/%s' % self.name


def test_no_extends_attribute_means_no_underlays():
    assert get_binary_import_underlays(object()) == []


def test_empty_extends_means_no_underlays():
    assert get_binary_import_underlays(_DistFile('binext', [])) == []


def test_only_binary_import_parents_in_order():
    dist_file = _DistFile('binext', [
        {'distro_name': 'upstream', 'index_url': None,
         'extension_method': 'source_rebuild'},
        {'distro_name': 'lyrical', 'index_url': 'https://example.org/i.yaml',
         'extension_method': 'binary_import'},
        {'distro_name': 'jetty', 'index_url': None,
         'extension_method': 'binary_import'},
    ])
    assert get_binary_import_underlays(dist_file) == [
        '/opt/ros/lyrical',
        '/opt/ros/jetty'
    ]


def test_custom_install_rule_in_extends_string_template():
    dist_file = _DistFile('binext', [
        {'distro_name': 'gazebo',
         'extension_method': 'binary_import',
         'install_rule': '/usr'},
        {'distro_name': 'acme',
         'extension_method': 'binary_import',
         'install_rule': '/opt/acme/{distro}'},
    ])
    assert get_binary_import_underlays(dist_file) == [
        '/usr',
        '/opt/acme/acme'
    ]


def test_custom_install_rule_in_extends_regex():
    dist_file = _DistFile('binext', [
        {'distro_name': 'vendor_v1',
         'extension_method': 'binary_import',
         'install_rule': {
             'search': '^.*$',
             'replace': '/opt/vendor/{distro}'
         }},
    ])
    assert get_binary_import_underlays(dist_file) == [
        '/opt/vendor/vendor-v1'
    ]


def test_default_parent_spaces_without_the_variable():
    assert get_default_parent_result_spaces('binext', environ={}) == \
        ['/opt/ros/binext']


def test_legacy_binary_import_parents_come_first():
    environ = {BINARY_IMPORT_DISTROS_ENV: 'lyrical'}
    assert get_default_parent_result_spaces('binext', environ=environ) == \
        ['/opt/ros/lyrical', '/opt/ros/binext']


def test_explicit_parent_result_spaces_take_precedence():
    environ = {
        PARENT_RESULT_SPACES_ENV: '/opt/acme/upstream:/opt/custom/lyrical',
        BINARY_IMPORT_DISTROS_ENV: 'legacy_distro'
    }
    assert get_default_parent_result_spaces('binext', environ=environ) == \
        ['/opt/acme/upstream', '/opt/custom/lyrical']


def test_dist_file_custom_prefix_resolution():
    dist_file = _DistFile('acme_distro', install_rule='/opt/acme/{distro}')
    assert get_distribution_install_prefix(dist_file) == '/opt/acme/acme_distro'
    assert get_default_parent_result_spaces('acme_distro', environ={}, dist_file=dist_file) == \
        ['/opt/acme/acme_distro']
