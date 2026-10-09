# generated from @template_name

@{task_os_code_name = 'focal'}@
FROM ubuntu:@task_os_code_name

VOLUME ["/var/cache/apt/archives"]

ENV DEBIAN_FRONTEND noninteractive

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
    os_name='ubuntu',
    os_code_name=task_os_code_name,
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
    os_name='ubuntu',
    os_code_name=task_os_code_name,
))@

RUN python3 -u /tmp/wrapper_scripts/apt.py update-install-clean -q -y python3-rosdistro-modules python3-yaml

# REP-159 test: shadow the apt rosdistro module with KmoM88's REP-2015 fork,
# which parses distribution file version 3. pip installs under /usr/local,
# which precedes /usr/lib/python3/dist-packages on sys.path. This task image
# is focal: its pip 20 neither knows --break-system-packages nor can check out
# a commit that is on no branch, so it installs the same commit (full SHA)
# from GitHub's archive.
RUN python3 -u /tmp/wrapper_scripts/apt.py update-install-clean -q -y --no-install-recommends python3-pip
RUN pip3 install --no-deps https://github.com/KmoM88/rosdistro/archive/436f5429fc1e1a70144de9c809823321df4a3ec2.tar.gz

USER buildfarm
ENTRYPOINT ["sh", "-c"]
@{
cmd = \
    'PYTHONPATH=/tmp/ros_buildfarm:$PYTHONPATH python3 -u' + \
    ' /tmp/ros_buildfarm/scripts/release/check_sync_criteria.py' + \
    ' ' + config_url + \
    ' ' + rosdistro_name + \
    ' ' + release_build_name + \
    ' ' + os_name + \
    ' ' + os_code_name + \
    ' ' + arch + \
    ' --cache-dir ' + cache_dir + \
    (' --return-zero' if return_zero else '')
}@
CMD ["@cmd"]
