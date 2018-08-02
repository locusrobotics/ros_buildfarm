# Copyright 2014-2016 Open Source Robotics Foundation, Inc.
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

from __future__ import print_function

from distutils.version import LooseVersion
import os
import time
import itertools
from .config import get_index as get_config_index
from .status_page import additional_resources
from .status_page import get_resource_hashes
from .super_status import get_super_status
from .templates import expand_template


def build_release_compare_page(
        config_url, rosdistro_names,
        output_dir, copy_resources=False):
    from rosdistro import get_cached_distribution
    from rosdistro import get_index

    start_time = time.time()

    config = get_config_index(config_url)

    index = get_index(config.rosdistro_index_url)

    # get all input data
    distros = [get_cached_distribution(index, d) for d in rosdistro_names]

    # get cached yaml data
    super_status = get_super_status(config, rosdistro_names)

    pkg_names = [d.release_packages.keys() for d in distros]
    pkg_names = [x for y in pkg_names for x in y]

    pkgs_data = {}
    for pkg_name in pkg_names:
        pkg_data = _compare_package_version(distros, pkg_name)
        if pkg_data:
            pkgs_data[pkg_name] = pkg_data
            pkg_data.status = super_status.get(pkg_name, {})

    template_name = 'status/release_compare_page.html.em'
    data = {
        'title': 'ROS packages in %s' % ' '.join([x.capitalize() for x in rosdistro_names]),

        'start_time': start_time,
        'start_time_local_str': time.strftime('%Y-%m-%d %H:%M:%S %z', time.localtime(start_time)),

        'resource_hashes': get_resource_hashes(),

        'rosdistro_names': rosdistro_names,

        'pkgs_data': pkgs_data,
    }
    html = expand_template(template_name, data)
    output_filename = os.path.join(
        output_dir, 'compare_%s.html' % '_'.join(rosdistro_names))
    print("Generating compare page: '%s'" % output_filename)
    with open(output_filename, 'w') as h:
        h.write(html)

    additional_resources(output_dir, copy_resources=copy_resources)

class CompareRow(object):

    def __init__(self, pkg_name):
        self.pkg_name = pkg_name
        self.repo_name = ''
        self.repo_urls = []
        self.maintainers = {}
        self.versions = {}
        self.branches = []
        self.status = {}

    def get_repo_name_with_link(self):
        valid_urls = [u for u in self.repo_urls if u]
        if len(set(valid_urls)) == 1:
            return '<a href="%s">%s</a>' % (valid_urls[0], self.repo_name)

        unique_urls = []
        [unique_urls.append(u) for u in valid_urls if u not in unique_urls]
        parts = [self.repo_name]
        for i, repo_url in enumerate(unique_urls):
            parts.append(' [<a href="%s">%d</a>]' % (repo_url, i + 1))
        return ' '.join(parts)

    def get_maintainers(self):
        return ' '.join([self.maintainers[k] for k in sorted(self.maintainers.keys())])

    def get_labels(self, distros):
        all_versions = [LooseVersion(v) if v else v for v in self.versions.values()]
        valid_versions = [v for v in all_versions if v]
        labels = []
        if any([
            _is_only_patch_is_different(p[0], p[1])
            for p in itertools.combinations(valid_versions, 2)]
        ):
            labels.append('DIFF_PATCH')
        if any([_is_greater(p[0], p[1]) for p in itertools.combinations(valid_versions, 2)]):
            labels.append('DOWNGRADE_VERSION')

        versions_and_branches = zip(
            itertools.combinations(all_versions, 2), itertools.combinations(self.branches, 2))
        if any([
            _is_same_version_but_different_branch(vb[0][0], vb[0][1], vb[1][0], vb[1][1])
            for vb in versions_and_branches
        ]):
            labels.append('DIFF_BRANCH_SAME_VERSION')
        return labels


def _is_only_patch_is_different(a, b):
    return a.version[0] == b.version[0] and \
        a.version[1] == b.version[1] and a.version[2] != b.version[2]


def _is_greater(a, b):
    return a.version[0] > b.version[0] or \
        (a.version[0] == b.version[0] and a.version[1] > b.version[1])


def _is_same_version_but_different_branch(version_a, version_b, branch_a, branch_b):
    # skip when any version is unknown
    if not version_a or not version_b:
        return False
    # skip when any branch is unknown or they are equal
    if not branch_a or not branch_b or branch_a == branch_b:
        return False
    return version_a.version[0] == version_b.version[0] and \
        version_a.version[1] == version_b.version[1]


def _compare_package_version(distros, pkg_name):
    from catkin_pkg.package import InvalidPackage, parse_package_string
    row = CompareRow(pkg_name)
    for distro in distros:
        repo_url = None
        version = None
        branch = None
        if pkg_name in distro.release_packages:
            pkg = distro.release_packages[pkg_name]
            row.repo_name = pkg.repository_name
            repo = distro.repositories[pkg.repository_name]

            rel_repo = repo.release_repository
            if rel_repo:
                version = rel_repo.version
                pkg_xml = distro.get_release_package_xml(pkg_name)
                if pkg_xml is not None:
                    try:
                        pkg = parse_package_string(pkg_xml)
                        for m in pkg.maintainers:
                            row.maintainers[m.name] = '<a href="mailto:%s">%s</a>' % \
                                (m.email, m.name)
                    except InvalidPackage:
                        row.maintainers['zzz'] = '<b>invalid package.xml in %s</b>' % \
                            distro.name

                if repo.source_repository:
                    repo_url = repo.source_repository.url
                elif repo.doc_repository:
                    repo_url = repo.doc_repository.url

            source_repo = repo.source_repository
            if source_repo:
                branch = source_repo.version
            else:
                doc_repo = repo.source_repository
                if doc_repo:
                    branch = doc_repo.version

        row.repo_urls.append(repo_url)
        if version:
            row.versions[distro.name] = version
        row.branches.append(branch)

    # skip if no versions available
    if row.versions:
        return row
