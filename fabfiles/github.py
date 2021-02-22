from github import Github
import json
import os
import re
import subprocess

from fabric.api import task
from fabric.colors import red, green, blue, yellow
from fabric.utils import puts


# GITHUB CREDS
################################################################################
GITHUB_API_TOKEN_FILE = 'credentials/github_api.json'
GITHUB_API_TOKEN_NAME = 'cloud-chef-token'
GITHUB_SUSHI_CHEFS_TEAM_ID = 2590528  # "Sushi Chefs" team = all sushi chef devs

def get_github_client(token=None):
    """
    Returns a token-authenticated github client (to avoid code duplication).
    """
    if token is None:
        with open(GITHUB_API_TOKEN_FILE, 'r') as tokenf:
            token = json.load(tokenf)[GITHUB_API_TOKEN_NAME]
    return Github(token)



# GITHUB ACTIONS
################################################################################

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



# REPORTS
################################################################################

@task
def list_chef_repos(fast=False):
    """
    Print report about all sushi chef repos (forks, branches, PRs, issues).
    """
    chef_repos = get_chef_repos()
    print_report_for_github_repos(chef_repos, fast=fast)


@task
def list_pipeline_repos(fast=False):
    """
    Print report about all the github repos related to the Content Pipeline.
    """
    pipeline_repos = get_pipeline_repos()
    print_report_for_github_repos(pipeline_repos, fast=fast)


@task
def clone_chef_repos(root_dir):
    assert os.path.exists(root_dir), "Directory to clone into does not exist: {}".format(root_dir)
    pipeline_repos = get_chef_repos()
    os.chdir(root_dir)
    for repo in pipeline_repos:
        subprocess.call(['git', 'clone', repo.html_url])


# GITHUB REPOS INFO
################################################################################

# Repos that are no longer in active use
DEPRECATED_REPOS = [
    'learningequality/sushi-chef-khan-academy-legacy',      # old KA chef
    'learningequality/sushi-chef-pradigi',                  # old PraDigi chef
    'learningequality/cloud-kolibri-demo',  # --301-> content-automation-scripts
    'learningequality/cloud-chef',          # --301-> content-automation-scripts
    'learningequality/sushibar',            # no more sushibar
    'learningequality/KhanTsvExports',      # POC paesing of TSV exports
    'learningequality/pipeline-panic',      # game engine on using notion as UI
]

CONTENT_PIPELINE_REPOS = [
    'learningequality/le-utils',                        # shared contstants
    'learningequality/ricecooker',                      # main actor
    'learningequality/pressurecooker',                  # supporting actor 1
    'learningequality/pycaption',                       # supporting actor 2
    'learningequality/sample-channels',                 # mo sushichefs examples
    'learningequality/content-automation-scripts',      # fab all the things
    'learningequality/imscp',                           # IMSCP/SCORM parser
    'learningequality/microwave',                       # docx -> pdf convertion
    'learningequality/treediffer',                      # JSON diff all things
    'learningequality/BasicCrawler',                    # automated crawler 2018
    'learningequality/webmixer',                        # automated crawler 2019
    'learningequality/cookiecutter-chef',               # chef repo template
    'learningequality/html-app-starter',                # default style for HTML
    # 'fle-internal/handy-scripts',
    # 'fle-internal/content-provenance',
]

# Other chef repos that don't fit the `learningequality/sushi-chef-*` pattern
EXTERNAL_CHEF_REPOS = [
    'prathamopenschool1/pratham-content-integration-script',  # new PraDigi chef
]


def get_pipeline_repos():
    """
    Return a list of all non-chef repos related to the Content Pipeline.
    """
    github = get_github_client()
    pipeline_repos = []
    for full_name in CONTENT_PIPELINE_REPOS:
        repo = github.get_repo(full_name)
        pipeline_repos.append(repo)
    return pipeline_repos


def get_chef_repos(organization='learningequality'):
    """
    Return a list of all learningequality github repos matching `sushi-chef-*`.
    """
    github = get_github_client() 
    le_org = github.get_organization(organization)
    all_repos = le_org.get_repos()
    # select only sushi-chef-* repos
    CHEF_REPO_PATTERN = re.compile('.*sushi-chef-.*')
    chef_repos = []
    for repo in all_repos:
        if CHEF_REPO_PATTERN.search(repo.name) and repo.full_name not in DEPRECATED_REPOS:
            chef_repos.append(repo)
    # append other repos
    if EXTERNAL_CHEF_REPOS:
        for full_name in EXTERNAL_CHEF_REPOS:
            repo = github.get_repo(full_name)
            chef_repos.append(repo)
    return chef_repos


def print_report_for_github_repos(github_repos, fast=False):
    """
    Report detailed info about the github repos in `github_repos`.
    """
    fast = (fast and fast.lower() == 'true')
    for repo in github_repos:
        forks = list(repo.get_forks())
        branches = list(repo.get_branches())
        pulls = list(repo.get_pulls())
        issues = list(repo.get_issues(state='open'))
        if not fast:
            print()  # extra newline between repos when printing detailed report
        print('-', blue(repo.html_url),
            '\t', len(forks), 'forks',
            '\t', len(branches), 'branches',
            '\t', len(pulls), 'PRs',
            '\t', len(issues), 'Issues')
        if not fast:
            for fork in forks:
                fork_branches = list(fork.get_branches())
                branch_names = [yellow(fb.name) for fb in fork_branches if fb.name != 'master']
                fork_branches_str = 'branches: ' + ', '.join(branch_names) if branch_names else ''
                print(blue('   - fork: ' + fork.html_url), fork_branches_str)
            for branch in branches:
                commit_msg_lines = branch.commit.commit.message.split('\n')
                commit_msg_str = commit_msg_lines[0]
                print(yellow('   - branch: ' + branch.name),
                        '('+ branch.commit.sha[0:7]+')',
                        'by', branch.commit.author.login if branch.commit.author else '?',
                        commit_msg_str, '\t', branch.commit.commit.last_modified)
            for pr in pulls:
                print(green('   - PR' + str(pr.number) + ': ' + pr.title),
                        pr.state,
                        'by', pr.user.login,
                        '\t', pr.last_modified,
                        pr.commits, 'commits',
                        pr.comments, 'comments',
                        pr.labels if pr.labels else '')
            for issue in issues:
                print(red('   - I' + str(issue.number) + ': ' + issue.title),
                        issue.state, issue.comments, 'comments',
                        issue.labels if issue.labels else '')