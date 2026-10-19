# generated from @template_name

FROM @os_name:@os_code_name

VOLUME ["/var/cache/apt/archives"]

ENV DEBIAN_FRONTEND noninteractive

@(TEMPLATE(
    'snippet/old_release_set.Dockerfile.em',
    os_name=os_name,
    os_code_name=os_code_name,
))@

@(TEMPLATE(
    'snippet/setup_locale.Dockerfile.em',
    timezone=timezone,
))@

@(TEMPLATE(
    'snippet/add_buildfarm_user.Dockerfile.em',
    uid=uid,
))@

@(TEMPLATE(
    'snippet/add_distribution_repositories.Dockerfile.em',
    distribution_repository_keys=distribution_repository_keys,
    distribution_repository_urls=distribution_repository_urls,
    os_name=os_name,
    os_code_name=os_code_name,
    add_source=False,
))@

@(TEMPLATE(
    'snippet/add_wrapper_scripts.Dockerfile.em',
    wrapper_scripts=wrapper_scripts,
))@

# automatic invalidation once every day
RUN echo "@today_str"

@(TEMPLATE(
    'snippet/install_python3.Dockerfile.em',
    os_name=os_name,
    os_code_name=os_code_name,
))@

@(TEMPLATE(
    'snippet/install_dh-python.Dockerfile.em',
    os_name=os_name,
    os_code_name=os_code_name,
))@

RUN python3 -u /tmp/wrapper_scripts/apt.py update-install-clean -q -y debhelper dh-cargo dpkg dpkg-dev git git-buildpackage python3-catkin-pkg-modules python3-rosdistro-modules python3-yaml
@[if os_name == 'ubuntu' and os_code_name == 'yakkety']@
@# git-buildpackage in Yakkety has a bug resulting in using the current time for
@# the to be archived files resulting in non-deterministic checksums for the tarball
@# https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=851645;msg=43
RUN sed -i '/    main_tree = repo.tree_drop_dirs(upstream_tree, options.subtarballs)/c\    main_tree = repo.tree_drop_dirs(upstream_tree, options.subtarballs) if options.subtarballs else upstream_tree' /usr/lib/python2.7/dist-packages/gbp/scripts/buildpackage.py
@[end if]@

# REP-159 test: install rosdistro fork with format version 3 and binary_rule support
RUN python3 -u /tmp/wrapper_scripts/apt.py update-install-clean -q -y --no-install-recommends python3-pip
RUN pip3 install --break-system-packages --no-deps \
    git+https://github.com/rep159-testing/rosdistro@feature/rep159-binary-naming-regex \
    git+https://github.com/rep159-testing/rosdep@3d52dadcbe13

USER buildfarm
ENTRYPOINT ["sh", "-c"]
@{
cmds = [
    'PYTHONPATH=/tmp/ros_buildfarm:$PYTHONPATH python3 -u' +
    ' /tmp/ros_buildfarm/scripts/release/get_sources.py' +
    ' --rosdistro-index-url ' + rosdistro_index_url +
    ' ' + rosdistro_name +
    ' ' + package_name +
    ' ' + os_name +
    ' ' + os_code_name +
    ' ' + ' '.join(distribution_repository_urls) +
    ' --source-dir ' + source_dir,

    'PYTHONPATH=/tmp/ros_buildfarm:$PYTHONPATH python3 -u' +
    ' /tmp/ros_buildfarm/scripts/release/build_sourcedeb.py' +
    ' ' + os_name +
    ' ' + os_code_name +
    ' --source-dir ' + source_dir,
]
}@
CMD ["@(' && '.join(cmds))"]
