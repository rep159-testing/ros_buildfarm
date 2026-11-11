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

from types import SimpleNamespace

from ros_buildfarm.release_job import get_workspace_package


def test_default_is_ros_workspace():
    assert get_workspace_package(SimpleNamespace()) == 'ros_workspace'
    assert get_workspace_package(
        SimpleNamespace(workspace_package=None)) == 'ros_workspace'


def test_named_workspace_package():
    assert get_workspace_package(
        SimpleNamespace(workspace_package='ros_workspace_shell')) == \
        'ros_workspace_shell'


def _package_xml(name, depends=()):
    return (
        '<package format="3"><name>%s</name><version>0.1.0</version>'
        '<description>d</description>'
        '<maintainer email="nobody@example.com">nobody</maintainer>'
        '<license>Apache-2.0</license>%s</package>' % (
            name, ''.join('<depend>%s</depend>' % d for d in depends)))


def _parse(monkeypatch, workspace_package, package_xmls):
    import ros_buildfarm.release_job as release_job
    cache = SimpleNamespace(
        distribution_file=SimpleNamespace(
            workspace_package=workspace_package),
        release_package_xmls=package_xmls)
    monkeypatch.setattr(
        release_job, 'get_distribution_cache', lambda index, name: cache)
    monkeypatch.setattr(
        release_job, 'get_package_condition_context',
        lambda index, name: {'ROS_DISTRO': name, 'ROS_VERSION': '2'})
    index = SimpleNamespace(
        distributions={'srcext': {'distribution_type': 'ros2'}})
    pkgs = release_job._get_and_parse_distribution_cache(
        index, 'srcext', ['upstream_a', 'ros_workspace_shell'],
        include_test_deps=True, include_group_deps=False,
        disable_groups_workaround=False)
    return {
        name: sorted(d.name for d in pkg.exec_depends)
        for name, pkg in pkgs.items()}


def test_packages_depend_on_the_named_workspace_package(monkeypatch):
    deps = _parse(monkeypatch, 'ros_workspace_shell', {
        'ros_workspace_shell': _package_xml('ros_workspace_shell'),
        'upstream_a': _package_xml('upstream_a'),
        'ros_workspace': _package_xml('ros_workspace'),
    })
    assert deps == {
        'ros_workspace_shell': [],
        'upstream_a': ['ros_workspace_shell'],
    }


def test_default_workspace_package_is_ros_workspace(monkeypatch):
    deps = _parse(monkeypatch, None, {
        'ros_workspace': _package_xml('ros_workspace', ['ament_package']),
        'ament_package': _package_xml('ament_package'),
        'upstream_a': _package_xml('upstream_a'),
        'ros_workspace_shell': _package_xml('ros_workspace_shell'),
    })
    # ros_workspace's own dependencies are not in pkg_names here, so they
    # are not parsed; the shell is an ordinary package
    assert deps == {
        'ros_workspace': ['ament_package'],
        'upstream_a': ['ros_workspace'],
        'ros_workspace_shell': ['ros_workspace'],
    }
