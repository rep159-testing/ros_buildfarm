# Copyright 2019 Open Source Robotics Foundation, Inc.
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

import argparse
import os
import sys
from urllib.request import urlretrieve

from ros_buildfarm.argument import add_argument_package_dependencies
from ros_buildfarm.argument import add_argument_package_names
from ros_buildfarm.argument import add_argument_repos_file_urls
from ros_buildfarm.argument import add_argument_repository_names
from ros_buildfarm.argument import add_argument_rosdistro_name
from ros_buildfarm.argument import add_argument_test_branch
from ros_buildfarm.common import Scope
from ros_buildfarm.vcs import export_repositories, import_repositories
from ros_buildfarm.workspace import ensure_workspace_exists
from rosdistro import get_cached_distribution
from rosdistro import get_index
from rosdistro import get_index_url
from rosdistro.dependency_walker import DependencyWalker
from rosdistro.dependency_walker import SourceDependencyWalker
import yaml


DEPENDENCY_TYPES = [
    'buildtool', 'buildtool_export', 'build', 'build_export', 'run', 'test']


# Walks released and source-only packages of one distribution alike. A
# package with a release entry is read from its released package.xml, as
# DependencyWalker does; one with only a source entry (which REP 159
# source_rebuild allows, in the child and in its parents) is read from the
# source part of the distribution cache. Packages of a binary_import parent
# are left out, as system dependencies are: they come as the parent's
# binaries, and checking them out would override them in the child.
class ReleaseAndSourceDependencyWalker(DependencyWalker):

    def __init__(self, distribution_instance):  # noqa: D107
        super().__init__(distribution_instance)
        self._source_walker = SourceDependencyWalker(distribution_instance)

    def _get_package_names(self):
        dist = self._distribution_instance
        names = set(dist.release_packages.keys()) | \
            set(dist.source_packages.keys())
        return {
            name for name in names
            if not _is_binary_import(dist, _repository_name(dist, name))}

    def _get_package(self, pkg_name):
        if pkg_name in self._distribution_instance.release_packages:
            return super()._get_package(pkg_name)
        return self._source_walker._get_package(pkg_name)


def _repository_name(dist, pkg_name):
    if pkg_name in dist.release_packages:
        return dist.release_packages[pkg_name].repository_name
    return dist.source_packages[pkg_name].repository_name


def _is_binary_import(dist, repo_name):
    repo = dist.repositories[repo_name]
    return getattr(repo, 'extension_method', None) == 'binary_import' and \
        getattr(repo, 'origin_distro', dist.name) != dist.name


def _source_repository_data(source_repository):
    repo_data = {
        'type': source_repository.type,
        'url': source_repository.url,
    }
    if source_repository.version is not None:
        repo_data['version'] = source_repository.version
    return repo_data


def get_repositories_data(
    dist, repository_names, package_names, package_dependencies
):
    """
    Return the repositories to check out for a CI workspace.

    Repositories named directly, and source-only packages, use the source
    entry and are keyed by repository name. Released packages use the
    release repository at the release tag and are keyed by package name.
    """
    data = {}
    for repo_name in repository_names or ():
        data[repo_name] = _source_repository_data(
            dist.repositories[repo_name].source_repository)

    package_names = list(package_names or ())
    if package_dependencies and package_names:
        walker = ReleaseAndSourceDependencyWalker(dist)
        additional_package_names = set()
        for pkg_name in package_names:
            additional_package_names |= walker.get_recursive_depends(
                pkg_name, DEPENDENCY_TYPES, ros_packages_only=True)
        additional_package_names.difference_update(package_names)
        package_names.extend(sorted(additional_package_names))

    for pkg_name in package_names:
        if pkg_name in dist.release_packages:
            pkg = dist.release_packages[pkg_name]
            rel_repo = dist.repositories[pkg.repository_name].release_repository
            data[pkg_name] = {
                'type': 'git',
                'url': rel_repo.url,
                'version': rel_repo.tags['release'].format_map({
                    'package': pkg_name,
                    'version': rel_repo.version,
                }),
            }
        elif pkg_name in dist.source_packages:
            repo_name = dist.source_packages[pkg_name].repository_name
            data[repo_name] = _source_repository_data(
                dist.repositories[repo_name].source_repository)
        else:
            raise KeyError(
                "Package '%s' has neither a release nor a source entry" %
                pkg_name)
    return data


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(
        description='Create a workspace from vcs repos files.')
    add_argument_rosdistro_name(parser)
    add_argument_repos_file_urls(parser)
    add_argument_repository_names(parser, optional=True)
    add_argument_package_names(parser, optional=True)
    add_argument_package_dependencies(parser)
    add_argument_test_branch(parser)
    parser.add_argument(
        '--workspace-root',
        help='The path of the desired workspace',
        required=True)
    args = parser.parse_args(argv)

    assert args.repos_file_urls or args.repository_names or args.package_names

    ensure_workspace_exists(args.workspace_root)

    repos_files = []
    if args.repository_names or args.package_names:
        with Scope('SUBSECTION', 'get repository information from rosdistro'):
            index = get_index(get_index_url())
            dist = get_cached_distribution(index, args.rosdistro_name)
            data = get_repositories_data(
                dist, args.repository_names, args.package_names,
                args.package_dependencies)
            repos_file = os.path.join(args.workspace_root, 'repositories-from-rosdistro.repos')
            with open(repos_file, 'w') as h:
                h.write(yaml.safe_dump({'repositories': data}, default_flow_style=False))
            repos_files.append(repos_file)

    with Scope('SUBSECTION', 'fetch repos files(s)'):
        for index, repos_file_url in enumerate(args.repos_file_urls):
            repos_file = os.path.join(args.workspace_root, '%d.repos' % index)
            print('Fetching \'%s\' to \'%s\'' % (repos_file_url, repos_file))
            urlretrieve(repos_file_url, repos_file)
            repos_files += [repos_file]

    with Scope('SUBSECTION', 'import repositories'):
        source_space = os.path.join(args.workspace_root, 'src')
        for repos_file in repos_files:
            print('Importing repositories from \'%s\'' % (repos_file))
            import_repositories(source_space, repos_file, args.test_branch)

    with Scope('SUBSECTION', 'vcs export --exact'):
        # if a repo has been rebased against the default branch vcs can't detect the remote
        export_repositories(source_space, check=not args.test_branch)


if __name__ == '__main__':
    sys.exit(main())
