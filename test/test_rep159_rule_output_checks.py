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

"""REP 159 rule output reaches shell commands: check it, quote paths."""

import subprocess

import pytest
from ros_buildfarm.common import check_install_prefix
from ros_buildfarm.common import check_os_package_name
from ros_buildfarm.common import get_binary_import_underlays
from ros_buildfarm.common import get_default_parent_result_spaces
from ros_buildfarm.common import get_distribution_install_prefix
from ros_buildfarm.common import get_os_package_name
from ros_buildfarm.common import get_os_package_name_prefix
from ros_buildfarm.common import PARENT_RESULT_SPACES_ENV
from ros_buildfarm.workspace import call_build_tool


UNSAFE_NAMES = [
    '',
    'ros-x-foo; touch /tmp/pwned',
    'ros-x-$(id)',
    'ros-x-`id`',
    'ros-x-foo bar',
    'ros-x-foo"',
    "ros-x-foo'",
    '-ros-x-foo',
    'ros-x-foo\n',
    'ros_x_foo',
    None,
]

UNSAFE_PREFIXES = [
    '',
    '/',
    'opt/ros/x',
    '/opt/ros/x; touch /tmp/pwned',
    '/opt/ros/$(id)',
    '/opt/ros/`id`',
    '/opt/ros/x y',
    '/opt/ros/x"',
    '/opt/../etc',
    '/opt/./ros',
    '/opt//ros',
    '/opt/ros/',
    '/opt/ros/x\n',
    '/opt/ros/a:/opt/ros/b',
    None,
]


class _NamingDistFile:

    def __init__(self, name='x', binary_package_name=None, binary_rule=None):
        self.name = name
        self.binary_rule = binary_rule
        self._binary_package_name = binary_package_name

    def get_binary_package_name(self, pkg_name):
        return self._binary_package_name


class _PrefixDistFile:

    def __init__(self, name='x', install_prefix=None, extends=None):
        self.name = name
        self.extends = extends or []
        self._install_prefix = install_prefix

    def get_install_prefix(self, pkg_name=None):
        return self._install_prefix


@pytest.mark.parametrize('name', [
    'ros-lyrical-rclcpp', 'vendor-extendable-gz-math', 'gz-math9',
    'libfoo++', 'ros-x-foo.bar', 'R', 'ros-ROS1Legacy-pkg'])
def test_valid_os_package_names_pass(name):
    assert check_os_package_name(name) == name


@pytest.mark.parametrize('name', UNSAFE_NAMES)
def test_unsafe_os_package_names_are_rejected(name):
    with pytest.raises(ValueError, match='Invalid OS package name'):
        check_os_package_name(name)


def test_stock_os_package_name_is_unchanged():
    assert get_os_package_name('lyrical', 'rcl_cpp') == 'ros-lyrical-rcl-cpp'
    assert get_os_package_name_prefix('my_distro') == 'ros-my-distro-'


@pytest.mark.parametrize('name', UNSAFE_NAMES[1:5])
def test_binary_rule_output_is_checked(name):
    dist_file = _NamingDistFile(binary_package_name=name)
    with pytest.raises(ValueError, match='Invalid OS package name'):
        get_os_package_name('x', 'foo', dist_file=dist_file)


def test_valid_binary_rule_output_passes():
    dist_file = _NamingDistFile(binary_package_name='vendor-x-foo')
    assert get_os_package_name('x', 'foo', dist_file=dist_file) == \
        'vendor-x-foo'


@pytest.mark.parametrize('replace', ['', '$(id)-', 'vendor x-', 'a;b-'])
def test_binary_rule_prefix_is_checked(replace):
    dist_file = _NamingDistFile(
        binary_rule={'search': '^', 'replace': replace})
    with pytest.raises(ValueError, match='Invalid OS package name prefix'):
        get_os_package_name_prefix('x', dist_file=dist_file)


def test_valid_binary_rule_prefix_passes():
    dist_file = _NamingDistFile(
        binary_rule={'search': '^', 'replace': 'vendor-{distro}-'})
    assert get_os_package_name_prefix('my_distro', dist_file=dist_file) == \
        'vendor-my-distro-'


@pytest.mark.parametrize('prefix', [
    '/opt/ros/lyrical', '/opt/acme/ext-jetty', '/usr', '/opt/a_b/c+d/e.f'])
def test_valid_install_prefixes_pass(prefix):
    assert check_install_prefix(prefix) == prefix


@pytest.mark.parametrize('prefix', UNSAFE_PREFIXES)
def test_unsafe_install_prefixes_are_rejected(prefix):
    with pytest.raises(ValueError, match='Invalid install prefix'):
        check_install_prefix(prefix)


def test_install_rule_of_the_distribution_is_checked():
    dist_file = _PrefixDistFile(install_prefix='/opt/$(id)')
    with pytest.raises(ValueError, match='Invalid install prefix'):
        get_distribution_install_prefix(dist_file)


def test_install_rule_in_extends_is_checked():
    dist_file = _PrefixDistFile('child', extends=[{
        'distro_name': 'parent', 'extension_method': 'binary_import',
        'install_rule': '/opt/`id`/{distro}'}])
    with pytest.raises(ValueError, match='Invalid install prefix'):
        get_binary_import_underlays(dist_file)


def test_parent_result_spaces_from_the_environment_are_checked():
    environ = {PARENT_RESULT_SPACES_ENV: '/opt/ros/a:/opt/ros/b;id'}
    with pytest.raises(ValueError, match='Invalid install prefix'):
        get_default_parent_result_spaces('x', environ=environ)


def test_own_install_prefix_from_the_dist_file_is_checked():
    dist_file = _PrefixDistFile(install_prefix='/opt/ros/x y')
    with pytest.raises(ValueError, match='Invalid install prefix'):
        get_default_parent_result_spaces('x', environ={}, dist_file=dist_file)


@pytest.mark.parametrize('with_setup_sh', [True, False])
def test_build_command_quotes_parent_result_spaces(
        tmp_path, monkeypatch, with_setup_sh):
    ws_root = tmp_path / 'ws'
    (ws_root / 'src').mkdir(parents=True)
    # a space and a command substitution: the path must reach the shell as
    # one word, and nothing in it may run
    parent_space = tmp_path / 'opt ros $(touch pwned)'
    (parent_space / 'lib').mkdir(parents=True)
    if with_setup_sh:
        (parent_space / 'setup.sh').write_text('true\n')

    captured = {}

    def fake_call(cmd, cwd=None, shell=False, stderr=None, env=None):
        captured['cmd'] = cmd
        return 0

    monkeypatch.setattr(subprocess, 'call', fake_call)
    assert call_build_tool(
        'colcon', 'x', str(ws_root),
        parent_result_spaces=[str(parent_space)], env={}) == 0

    # run everything before the build tool, then print the prefix path
    prologue, _ = captured['cmd'].rsplit(' && PYTHONIOENCODING=', 1)
    out = subprocess.check_output(
        ['sh', '-c', prologue + ' && printf %s "$CMAKE_PREFIX_PATH"'],
        cwd=str(tmp_path), env={'PATH': '/usr/bin:/bin'})
    assert out.decode().split(':')[0] == str(parent_space)
    assert not (tmp_path / 'pwned').exists()
