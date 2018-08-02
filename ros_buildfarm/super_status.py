import collections
import os
import requests
import re
import time
import yaml
from .aggregate_status import get_aggregate_status
from .config import get_index as get_config_index, get_release_build_files
from .status_page import additional_resources
from .templates import expand_template

YAML_FOLDER = 'http://repositories.ros.org/status_page/yaml/'
YAML_PATTERN = re.compile('<a href="(ros_(\w+)_(\w+).yaml)">')

# Patterns for extracting the organization and repo name
GITHUB_PATTERN = re.compile('https?://github.com/(?P<org>[^/]+)/(?P<repo>.+)\.git')
GITHUB_BRANCH_PATTERN = re.compile('https://github.com/(?P<org>[^/]+)/(?P<repo>[^/]+)/tree/(?P<branch>.*)')
BB_PATTERN = re.compile('https://bitbucket.org/(?P<org>.*)/(?P<repo>.*)')
GITLAB_PATTERN = re.compile('https?://gitlab.(?P<server>[^/]+)/(?P<org>[^/]+)/(?P<repo>.+).git')

# Organization Templates
GITHUB_ORG_TEMPLATE = 'http://github.com/{org}'
BB_ORG_TEMPLATE = 'https://bitbucket.org/{org}'
GITLAB_ORG_TEMPLATE = 'https://gitlab.{server}/{org}'

# Map url patterns to their matching organization template
URL_PATTERNS = {
    GITHUB_PATTERN: GITHUB_ORG_TEMPLATE,
    GITHUB_BRANCH_PATTERN: GITHUB_ORG_TEMPLATE,
    BB_PATTERN: BB_ORG_TEMPLATE,
    GITLAB_PATTERN: GITLAB_ORG_TEMPLATE
}

"""
  Naming Conventions
   * distro refers to ROS Distro (e.g. indigo)
   * machine refers to different release builds (e.g. default, uxhf, dsv8)
   * os_name refers to the name of the Operating System (e.g. ubuntu, debian)
   * os_flavor refers to specific distros of the os (e.g. xenial, jessie)
   * cpu refers to the cpu architecture (or source), (e.g. i386, amd64, source)
   * candidate refers to different candidate builds, (e.g. build, test, main)
   * combo refers to the os_flavor + the cpu
"""


def get_yaml_filenames():
    filenames = {}
    r = requests.get(YAML_FOLDER)
    for filename, distro, machine in YAML_PATTERN.findall(r.text):
        filenames[distro, machine] = filename
    return filenames


def dict_merge(dct, merge_dct):
    for k, v in merge_dct.iteritems():
        if (k in dct and isinstance(dct[k], dict) and isinstance(merge_dct[k], collections.Mapping)):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]


def merge_status_yaml(data, new_data, new_distro):
    for pkg, D in new_data.items():
        D2 = {new_distro: {}, 'maintainers': {}}
        for k, v in D.iteritems():
            if k == 'maintainers':
                for d in v:
                    D2['maintainers'][d['email']] = d['name']
            else:
                D2[new_distro][k] = v

        if pkg in data:
            dict_merge(data[pkg], D2)
        else:
            data[pkg] = D2


def get_multi_distro_status(distros):
    status = {}
    for (distro, machine), filename in sorted(get_yaml_filenames().items()):
        if distro not in distros:
            continue
        print('Loading {}/{}'.format(distro, machine))
        r = requests.get(YAML_FOLDER + filename)
        distro_status = yaml.load(r.text)
        merge_status_yaml(status, distro_status, distro)
    return status


def get_url_fields(s):
    for pattern in URL_PATTERNS:
        m = pattern.match(s)
        if m:
            fields = m.groupdict()
            fields['repo_url'] = s
            fields['org_url'] = URL_PATTERNS[pattern].format(**fields)
            fields['repo'] = fields['repo'].replace('.git', '').replace('-release', '')
            return fields


def get_repo_info(entry):
    """
       Iterates through the different distributions and parses the organization and repo for the most recent distro
    """
    url = None
    for key, distro_dict in sorted(entry.items(), reverse=True):
        if 'url' not in distro_dict:
            continue
        url = distro_dict['url']
        fields = get_url_fields(url)
        if fields is not None:
            return fields
    # If nothing found, return organization=None and repo=full url
    return {'repo': url, 'repo_url': url}


def get_blacklist(build_file_dict):
    blacklist = collections.defaultdict(lambda: collections.defaultdict(set))

    for distro in sorted(build_file_dict):
        for machine in build_file_dict[distro]:
            build_file = build_file_dict[distro][machine]
            if len(build_file.package_blacklist) == 0:
                continue
            for pkg in build_file.package_blacklist:
                for os_name, os_d in build_file.targets.items():
                    for os_flavor, fl_d in os_d.items():
                        for cpu in fl_d:
                            blacklist[pkg][distro].add((os_name, os_flavor, cpu))
    return dict(blacklist)


def collect_expected_values(build_file_dict):
    C = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(set)))
    for distro in build_file_dict:
        for machine in build_file_dict[distro]:
            build_file = build_file_dict[distro][machine]
            for os_name, os_d in build_file.targets.items():
                for os_flavor, fl_d in os_d.items():
                    C[distro][os_name][os_flavor].add('source')
                    for cpu in fl_d:
                        C[distro][os_name][os_flavor].add(cpu)
    return C

def get_super_status(config, rosdistro_names):
    build_file_dict = {distro: get_release_build_files(config, distro) for distro in rosdistro_names}
    blacklist = get_blacklist(build_file_dict)
    expected = collect_expected_values(build_file_dict)
    multi_distro_status = get_multi_distro_status(rosdistro_names)

    return {pkg: get_aggregate_status(entry, expected, pkg, blacklist) for pkg, entry in multi_distro_status.items()}

def merge_statuses(statuses):
    if len(statuses) == 1:
        return list(statuses)[0]
    all_waiting = True
    all_broken = True
    for status in statuses:
        if 'waiting' not in status:
            all_waiting = False
        if 'build' not in status:
            all_broken = False
    if all_waiting:
        return 'waiting for new/re-release'
    elif all_broken:
        return 'does not build on some platforms'
    else:
        return 'mixed'


def build_super_status_page(config_url, rosdistro_names=[], output_dir='.', copy_resources=False):
    start_time = time.time()

    config = get_config_index(config_url)

    if len(rosdistro_names) == 0:
        rosdistro_names = list(sorted(config.distributions.keys()))

    build_file_dict = {}
    for distro in rosdistro_names:
        build_file_dict[distro] = get_release_build_files(config, distro)

    multi_distro_status = get_multi_distro_status(rosdistro_names)
    print('Write yaml file')
    yaml_filename = os.path.join(output_dir, 'multi_distro_status.yaml')
    yaml.safe_dump(multi_distro_status, open(yaml_filename, 'w'), allow_unicode=True)

    print('Examining each package')
    super_status = {}
    blacklist = get_blacklist(build_file_dict)
    expected = collect_expected_values(build_file_dict)
    for pkg, entry in sorted(multi_distro_status.items()):
        repo_info = get_repo_info(entry)
        org = repo_info.get('org')
        repo = repo_info.get('repo')
        if org not in super_status:
            super_status[org] = {'repos': {}}
            if 'org_url' in repo_info:
                super_status[org]['url'] = repo_info['org_url']
        org_dict = super_status[org]['repos']
        if repo not in org_dict:
            org_dict[repo] = {'pkgs': {}, 'url': repo_info['repo_url']}
        repo_dict = org_dict[repo]['pkgs']
        status = get_aggregate_status(entry, expected, pkg, blacklist)
        d = {'status': status}
        if 'maintainers' in entry:
            d['maintainers'] = entry['maintainers']
        versions = dict([(distro, entry[distro]['version']) for distro in status])
        if versions:
            d['versions'] = versions
        repo_dict[pkg] = d

    print('Getting status for each org/repo')
    for org, org_dict in super_status.items():
        org_set = collections.defaultdict(set)
        for repo, repo_dict in org_dict['repos'].items():
            repo_set = collections.defaultdict(set)
            for pkg, pkg_dict in repo_dict['pkgs'].items():
                for distro, status in pkg_dict['status'].iteritems():
                    org_set[distro].add(status)
                    repo_set[distro].add(status)
            repo_dict['status'] = {}
            for distro, statuses in repo_set.items():
                repo_dict['status'][distro] = merge_statuses(statuses)
        org_dict['status'] = {}
        for distro, statuses in org_set.items():
            org_dict['status'][distro] = merge_statuses(statuses)

    print('Write parsed yaml file')
    yaml_filename = os.path.join(output_dir, 'super_status.yaml')
    yaml.safe_dump(super_status, open(yaml_filename, 'w'), allow_unicode=True)

    output_filename = os.path.join(output_dir, 'super_status.html')
    print("Generating super status page '%s':" % output_filename)
    template_name = 'status/super_status_page.html.em'
    data = {
        'title': 'ROS Buildfarm Super Status',
        'start_time': start_time,
        'start_time_local_str': time.strftime('%Y-%m-%d %H:%M:%S %z', time.localtime(start_time)),
        'super_status': super_status,
        'rosdistro_names': rosdistro_names
    }
    html = expand_template(template_name, data)
    with open(output_filename, 'w') as h:
        h.write(html)

    additional_resources(output_dir, copy_resources=copy_resources)
