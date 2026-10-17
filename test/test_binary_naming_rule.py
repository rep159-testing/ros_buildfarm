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

from ros_buildfarm.common import get_os_package_name
from ros_buildfarm.common import get_os_package_name_prefix


class _MockReleaseRepo:

    def __init__(self, name, binary_rule=None, origin_distro=None):
        self.name = name
        self.binary_rule = binary_rule
        self.origin_distro = origin_distro


class _MockDistFile:

    def __init__(self, name, binary_rule=None, overrides=None):
        self.name = name
        self.binary_rule = binary_rule
        self.overrides = overrides or {}

    def get_binary_package_name(self, pkg_name):
        clean_distro = self.name.replace('_', '-')
        clean_pkg = pkg_name.replace('_', '-')
        rule = self.overrides.get(pkg_name, self.binary_rule)
        if rule and isinstance(rule, dict) and 'search' in rule and 'replace' in rule:
            import re
            replace_pattern = rule['replace'].replace('{distro}', clean_distro).replace('{DISTRO}', clean_distro)
            replace_pattern = replace_pattern.replace('_', '-')
            return re.sub(rule['search'], replace_pattern, clean_pkg)
        return 'ros-%s-%s' % (clean_distro, clean_pkg)


def test_standard_legacy_naming_without_dist_file():
    assert get_os_package_name('jazzy', 'std_msgs') == 'ros-jazzy-std-msgs'
    assert get_os_package_name('rolling', 'sensor_msgs') == 'ros-rolling-sensor-msgs'


def test_standard_underscore_sanitization():
    assert get_os_package_name('iron', 'my_special_package') == 'ros-iron-my-special-package'
    assert get_os_package_name('jazzy', 'pkg_with_many_underscores') == 'ros-jazzy-pkg-with-many-underscores'


def test_custom_vendor_binary_rule():
    dist_file = _MockDistFile('jazzy', binary_rule={
        'search': '^',
        'replace': 'vendor-{distro}-'
    })
    assert get_os_package_name('jazzy', 'my_pkg', dist_file=dist_file) == 'vendor-jazzy-my-pkg'
    assert get_os_package_name_prefix('jazzy', dist_file=dist_file) == 'vendor-jazzy-'


def test_exact_package_override_rule():
    dist_file = _MockDistFile('jetty', overrides={
        'gz_cmake': {
            'search': '^gz-cmake$',
            'replace': 'libgz-cmake5-dev'
        }
    })
    assert get_os_package_name('jetty', 'gz_cmake', dist_file=dist_file) == 'libgz-cmake5-dev'
    assert get_os_package_name('jetty', 'other_pkg', dist_file=dist_file) == 'ros-jetty-other-pkg'


def test_unprefixed_native_rule():
    dist_file = _MockDistFile('rolling', binary_rule={
        'search': '^',
        'replace': ''
    })
    assert get_os_package_name('rolling', 'gz_sim', dist_file=dist_file) == 'gz-sim'


def test_regex_group_capture_rule():
    dist_file = _MockDistFile('humble', binary_rule={
        'search': '^nav2-(.*)$',
        'replace': 'corp-{distro}-nav-\\1'
    })
    assert get_os_package_name('humble', 'nav2_planner', dist_file=dist_file) == 'corp-humble-nav-planner'
    assert get_os_package_name('humble', 'nav2_controller', dist_file=dist_file) == 'corp-humble-nav-controller'
