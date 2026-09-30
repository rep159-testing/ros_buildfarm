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

import pytest
from ros_buildfarm.scripts.ci.create_workspace import get_repositories_data
from rosdistro import get_cached_distribution
from rosdistro.distribution_cache import DistributionCache

# upstream_a <- upstream_b <- upstream_c <- downstream_src_a, as in the
# REP-159 harness; libxml2 and libyaml are rosdep keys, not packages.
SOURCE_CHAIN = {
    'upstream_a': ['libxml2'],
    'upstream_b': ['upstream_a'],
    'upstream_c': ['upstream_b'],
    'downstream_src_a': ['upstream_c', 'libyaml'],
}


def _package_xml(name, depends):
    return (
        '<package format="3"><name>%s</name><version>1.0.0</version>'
        '<description>%s</description>'
        '<maintainer email="m@example.com">m</maintainer>'
        '<license>Apache-2.0</license>%s</package>' % (
            name, name, ''.join('<depend>%s</depend>' % d for d in depends)))


def _source_entry(name):
    return {
        'type': 'git',
        'url': 'https://github.com/rep159-testing/%s.git' % name,
        'version': 'main'}


def _distribution(source_chain, released=None):
    """Build a cached distribution of source-only and released packages."""
    released = released or {}
    repositories = {
        name: {'source': _source_entry(name)} for name in source_chain}
    for name in released:
        repositories[name] = {'release': {
            'tags': {'release': 'release/test/{package}/{version}'},
            'url': 'https://github.com/example-release/%s.git' % name,
            'version': '1.0.0-1'}}
    cache = DistributionCache('srcext', data={
        'type': 'cache',
        'version': 2,
        'name': 'srcext',
        'distribution_file': {
            'type': 'distribution',
            'version': 2,
            'release_platforms': {'ubuntu': ['resolute']},
            'repositories': repositories},
        'release_package_xmls': {
            name: _package_xml(name, deps) for name, deps in released.items()},
        'source_repo_package_xmls': {
            name: {'_ref': '0' * 40, name: ['.', _package_xml(name, deps)]}
            for name, deps in source_chain.items()},
    })
    return get_cached_distribution(None, 'srcext', cache=cache)


def test_walk_through_source_only_packages():
    data = get_repositories_data(
        _distribution(SOURCE_CHAIN), [], ['downstream_src_a'], True)
    assert data == {name: _source_entry(name) for name in SOURCE_CHAIN}


def test_without_dependencies_only_the_named_package():
    data = get_repositories_data(
        _distribution(SOURCE_CHAIN), [], ['upstream_b'], False)
    assert data == {'upstream_b': _source_entry('upstream_b')}


def test_released_package_keeps_its_release_checkout():
    dist = _distribution(
        {'consumer': ['released_dep']}, released={'released_dep': []})
    data = get_repositories_data(dist, [], ['consumer'], True)
    assert data == {
        'consumer': _source_entry('consumer'),
        'released_dep': {
            'type': 'git',
            'url': 'https://github.com/example-release/released_dep.git',
            'version': 'release/test/released_dep/1.0.0-1'},
    }


def test_unknown_package_raises():
    dist = _distribution(SOURCE_CHAIN)
    with pytest.raises(KeyError):
        get_repositories_data(dist, [], ['no_such_package'], True)
    with pytest.raises(KeyError):
        get_repositories_data(dist, [], ['no_such_package'], False)


def test_repository_names_read_the_source_entry():
    data = get_repositories_data(
        _distribution(SOURCE_CHAIN), ['upstream_a'], [], False)
    assert data == {'upstream_a': _source_entry('upstream_a')}
