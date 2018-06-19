import os
import re
import time
import yaml
import requests
import shutil
from .templates import expand_template, get_template_path
from github import Github, GithubException

GITHUB_TOKEN_PATTERN = re.compile('https://([^@]*)@?github.com/([^/]+)/.*git')
GITLAB_TOKEN_PATTERN = re.compile('http://gitlab-ci-token:([^@]+)@(.*)\.git')


def _download_yaml(url, headers={}):
    r = requests.get(url, headers=headers)
    try:
        return yaml.load(r.text)
    except:
        print('Error', url)
        return {}


def _get_distro_info(distros=None):
    info = {}
    main_url = os.environ['ROSDISTRO_INDEX_URL']
    folder = os.path.split(main_url)[0]
    D = _download_yaml(main_url)
    for distro_name, distro_info in D['distributions'].items():
        if distros is not None and distro_name not in distros:
            continue
        url_part = distro_info['distribution'][0]
        new_url = os.path.join(folder, url_part)
        info[distro_name] = _download_yaml(new_url)
    if distros is not None:
        remaining = set(distros) - set(info.keys())
        for distro in remaining:
            print('Warning! Distro "{}" not found.'.format(distro))
    return info


def _extract_token(distro_info):
    for distro, distro_data in distro_info.items():
        for name, d in distro_data['repositories'].items():
            if 'source' not in d:
                continue
            m = GITHUB_TOKEN_PATTERN.match(d['source'].get('url', ''))
            if m:
                if len(m.group(1)):
                    return m.group(1)


def _get_package_info(g, distro_info, filter_packages=None):
    packages = {}
    cached_tracks = {}

    for distro, distro_data in distro_info.items():
        for name, d in distro_data['repositories'].items():
            if filter_packages and name not in filter_packages:
                continue
            if name not in packages:
                pkg = {}
                packages[name] = pkg
            else:
                pkg = packages[name]
            pkg[distro] = {}
            distro_d = pkg[distro]

            url = d.get('release', {}).get('url')
            if url and url[-4:] == '.git':
                if url in cached_tracks:
                    tracks = cached_tracks[url]
                else:
                    m = GITLAB_TOKEN_PATTERN.match(url)
                    if m:
                        headers = {'PRIVATE-TOKEN': m.group(1)}
                        tracks_url = 'http://' + m.group(2) + '/raw/master/tracks.yaml'
                    else:
                        tracks_url = url[:-4] + '/raw/master/tracks.yaml'
                        headers = {}
                    tracks = _download_yaml(tracks_url, headers).get('tracks', {})
                    cached_tracks[url] = tracks
                dtracks = tracks.get(distro, {})
                m = GITHUB_TOKEN_PATTERN.match(dtracks.get('vcs_uri', ''))
                if m:
                    distro_d['org'] = m.group(2)
                upstream = dtracks.get('devel_branch')
                if upstream:
                    distro_d['upstream'] = upstream
                release_tag = dtracks.get('release_tag')
                if release_tag == ':{ask}' and 'last_release' in dtracks:
                    distro_d['last_release'] = dtracks['last_release']

            if 'source' in d:
                upstream = d['source'].get('version')
                if upstream:
                    if 'upstream' in distro_d:
                        if upstream != distro_d['upstream']:
                            print('Package {} does not have matching upstream branches for {}. ({} vs. {})'
                                    .format(name, distro, upstream, distro_d['upstream']))
                    else:
                        distro_d['upstream'] = upstream

                if 'org' not in distro_d:
                    m = GITHUB_TOKEN_PATTERN.match(d['source'].get('url', ''))
                    if m:
                        pkg[distro]['org'] = m.group(2)

            release = d.get('release', {}).get('version')
            if release:
                if '-' in release:
                    release = release.partition('-')[0]
                distro_d['release'] = release
    return packages


def _get_package_status(g, name, branch_info):
    if 'org' not in branch_info:
        return ''
    elif 'upstream' not in branch_info:
        return 'NO SOURCE'
    elif 'release' not in branch_info:
        return 'NO RELEASE'
    repo = g.get_repo(branch_info['org'] + '/' + name)
    branch = branch_info.get('last_release', branch_info['release'])
    try:
        the_diff = repo.compare(branch, branch_info['upstream'])
        if len(the_diff.commits) > 0:
            return 'CHANGED'
        else:
            return 'BLOOMED'
    except GithubException as e:
        print('Error getting diff with repo {} between {}, {}'.format(name, branch, branch_info['upstream']))
        return 'BROKEN'


def _query_package_statuses(g, package_info):
    for pkg_name, info in package_info.items():
        for distro, d_info in info.items():
            status = _get_package_status(g, pkg_name, d_info)
            d_info['status'] = status


def build_bloom_status_page(packages=None, distros=None, output_dir='.'):
    start_time = time.time()
    print('Retrieving list of distros from ROSDISTRO_INDEX_URL')
    distro_info = _get_distro_info(distros)
    token = _extract_token(distro_info)
    if token:
        g = Github(token)
    else:
        g = Github()
    print('Retrieving package info')
    package_info = _get_package_info(g, distro_info, packages)
    print('Retrieving package statuses')
    _query_package_statuses(g, package_info)

    data = {
        'start_time': start_time,
        'start_time_local_str': time.strftime('%Y-%m-%d %H:%M:%S %z', time.localtime(start_time)),
        'packages': package_info,
        'distros': list(distro_info.keys())
    }

    output_filename = os.path.join(output_dir, 'bloom_status.html')
    print("Generating bloom status page '%s':" % output_filename)
    template_name = 'status/bloom_status_page.html.em'
    html = expand_template(template_name, data)
    with open(output_filename, 'w') as h:
        h.write(html)
    for subfolder in ['css', 'js']:
        dst = os.path.join(output_dir, subfolder)
        if not os.path.exists(dst):
            src = get_template_path(os.path.join('status', subfolder))
            shutil.copytree(src, dst)
