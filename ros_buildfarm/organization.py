import re

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

def get_url_fields(url):
    for pattern in URL_PATTERNS:
        m = pattern.match(url)
        if not m:
            continue
        fields = m.groupdict()
        fields['repo_url'] = url
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
