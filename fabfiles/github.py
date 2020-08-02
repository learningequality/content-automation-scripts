from github import Github
import json
import re

from fabric.api import task
from fabric.colors import red, green, blue, yellow
from fabric.utils import puts


# GITHUB CREDS
################################################################################
GITHUB_API_TOKEN_FILE = 'credentials/github_api.json'
GITHUB_API_TOKEN_NAME = 'cloud-chef-token'
GITHUB_SUSHI_CHEFS_TEAM_ID = 2590528  # "Sushi Chefs" team = all sushi chef devs


# TODO: support git:// URLs
# TODO: support .git suffix in HTTTPs urls
# TODO: handle all special cases https://github.com/tj/node-github-url-from-git
GITHUB_REPO_NAME_PAT = re.compile(r'https://github.com/(?P<repo_account>\w*?)/(?P<repo_name>[A-Za-z0-9_-]*)')


def get_github_client(token=None):
    """
    Returns a token-authenticated github client (to avoid code duplication).
    """
    if token is None:
        with open(GITHUB_API_TOKEN_FILE, 'r') as tokenf:
            token = json.load(tokenf)[GITHUB_API_TOKEN_NAME]
    return Github(token)


@task
def create_github_repo(nickname, source_url=None, init=True, private=False):
    """
    Create a github repo for chef given its `nickname` and `source_url`.
    """
    init = False if init=='False' or init=='false' else True
    private = True if private=='True' or private=='true' else False
    description = 'Sushi Chef script for importing {} content'.format(nickname)
    if source_url:
        description += ' from ' + str(source_url)
    repo_name = 'sushi-chef-' + nickname

    github = get_github_client()
    le_org = github.get_organization('learningequality')

    # 1. create repo
    create_repo_kwargs = dict(
        description=description,
        private=private,
        has_issues=True,
        has_wiki=False,
        auto_init=init
    )
    if init:
        create_repo_kwargs['license_template'] = 'mit'
        create_repo_kwargs['gitignore_template'] = 'Python'
    repo = le_org.create_repo(repo_name, **create_repo_kwargs)

    # 3. Give "Sushi Chefs" team read/write persmissions
    team = le_org.get_team(GITHUB_SUSHI_CHEFS_TEAM_ID)
    team.add_to_repos(repo)
    team.set_repo_permission(repo, 'admin')
    puts(green('Chef repo succesfully created: {}'.format(repo.html_url)))



@task
def list_chef_repos(organization='learningequality'):
    """
    List of all learningequality github repos that match the `sushi-chef-*`.
    """
    CHEF_REPO_PATTERN = re.compile('.*sushi-chef-.*')
    github = get_github_client() 
    le_org = github.get_organization(organization)
    repos = le_org.get_repos()
    chef_repos = []
    for repo in repos:
        if CHEF_REPO_PATTERN.search(repo.name):
            chef_repos.append(repo)
    for repo in chef_repos:
        pulls = list(repo.get_pulls())
        issues = list(repo.get_issues())
        print(repo.name,
              '\t', repo.html_url,
              '\t', len(pulls), 'PRs',
              '\t', len(issues), 'Issues')
    return chef_repos


@task
def list_repo_issues(reponame, organization='learningequality'):
    """
    List github issues associated with a given suchi chef repository.
    """
    if reponame is None:
        return
    github = get_github_client() 
    repo = github.get_repo("{}/{}".format(organization, reponame))
    open_issues = repo.get_issues(state='open')
    for issue in open_issues:
        print(issue.number, issue.state, issue.title, issue.comments, 'comments', issue.labels)
    return open_issues




def github_repo_to_chefdir(github_url):
    """
    Extracts the `chefdir` (repo name) from a github URL.
    """
    if github_url.endswith('/'):
        github_url = github_url[0:-1]
    match = GITHUB_REPO_NAME_PAT.search(github_url)
    if match:
        return match.groupdict()['repo_name']
    else:
        raise ValueError('chefdir cannot be inferred from github repo name...')
